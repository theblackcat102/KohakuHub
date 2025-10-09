"""S3 client utilities and helper functions."""

from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config as BotoConfig

from kohakuhub.async_utils import run_in_s3_executor
from kohakuhub.config import cfg
from kohakuhub.logger import get_logger

logger = get_logger("S3")


def get_s3_client():
    """Create configured S3 client.

    Returns:
        Configured boto3 S3 client.
    """
    boto_config = BotoConfig(
        s3={"addressing_style": "path"} if cfg.s3.force_path_style else {}
    )
    return boto3.client(
        "s3",
        endpoint_url=cfg.s3.endpoint,
        aws_access_key_id=cfg.s3.access_key,
        aws_secret_access_key=cfg.s3.secret_key,
        region_name=cfg.s3.region,
        config=boto_config,
    )


def init_storage():
    """Check and create the configured S3 bucket if it doesn't exist."""
    s3 = get_s3_client()
    bucket_name = cfg.s3.bucket
    region = cfg.s3.region

    try:
        s3.head_bucket(Bucket=bucket_name)
        logger.success(f"S3 Bucket '{bucket_name}' already exists.")
    except Exception as e:
        # If a 404 error is received, the bucket does not exist
        error_code = e.response["Error"]["Code"]
        if error_code == "404":
            logger.info(f"S3 Bucket '{bucket_name}' not found. Creating it...")
            try:
                # MinIO doesn't care about the region for local setup, but S3 requires it
                if region and region != "us-east-1":
                    s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": region},
                    )
                else:
                    s3.create_bucket(Bucket=bucket_name)

                logger.success(f"S3 Bucket '{bucket_name}' created successfully.")
            except Exception as e:
                logger.exception(f"Failed to create S3 bucket '{bucket_name}'", e)
                # You might want to raise this error to halt startup
                raise
        else:
            # Other error (e.g., 403 Forbidden)
            logger.exception(f"Error checking S3 bucket '{bucket_name}'", e)
            raise


def _generate_download_presigned_url_sync(
    bucket: str, key: str, expires_in: int = 3600, filename: str = None
) -> str:
    """Synchronous implementation of generate_download_presigned_url."""
    s3 = get_s3_client()
    params = {"Bucket": bucket, "Key": key}

    if filename:
        params["ResponseContentDisposition"] = f'attachment; filename="{filename}";'

    url = s3.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=expires_in,
    )

    return url.replace(cfg.s3.endpoint, cfg.s3.public_endpoint)


async def generate_download_presigned_url(
    bucket: str, key: str, expires_in: int = 3600, filename: str = None
) -> str:
    """Generate presigned URL for downloading from S3.

    Args:
        bucket: S3 bucket name
        key: Object key in S3
        expires_in: URL expiration time in seconds (default: 1 hour)
        filename: Optional filename for Content-Disposition header

    Returns:
        Presigned download URL
    """
    return await run_in_s3_executor(
        _generate_download_presigned_url_sync, bucket, key, expires_in, filename
    )


def _generate_upload_presigned_url_sync(
    bucket: str,
    key: str,
    expires_in: int = 3600,
    content_type: str = "application/octet-stream",
    checksum_sha256: str = None,
) -> dict:
    """Synchronous implementation of generate_upload_presigned_url."""
    s3 = get_s3_client()

    params = {
        "Bucket": bucket,
        "Key": key,
    }

    url = s3.generate_presigned_url(
        "put_object",
        Params=params,
        ExpiresIn=expires_in,
        HttpMethod="PUT",
    )

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )

    headers = {
        "Content-Type": content_type,
    }

    return {
        "url": url.replace(cfg.s3.endpoint, cfg.s3.public_endpoint),
        "expires_at": expires_at,
        "method": "PUT",
        "headers": headers,
    }


async def generate_upload_presigned_url(
    bucket: str,
    key: str,
    expires_in: int = 3600,
    content_type: str = "application/octet-stream",
    checksum_sha256: str = None,
) -> dict:
    """Generate presigned URL for uploading to S3.

    Args:
        bucket: S3 bucket name
        key: Object key in S3
        expires_in: URL expiration time in seconds (default: 1 hour)
        content_type: Content type of the object
        checksum_sha256: Base64-encoded SHA256 checksum for S3 to verify (optional)

    Returns:
        Dict with 'url', 'fields', and 'expires_at'
    """
    return await run_in_s3_executor(
        _generate_upload_presigned_url_sync,
        bucket,
        key,
        expires_in,
        content_type,
        checksum_sha256,
    )


def _generate_multipart_upload_urls_sync(
    bucket: str,
    key: str,
    part_count: int,
    upload_id: str = None,
    expires_in: int = 3600,
) -> dict:
    """Synchronous implementation of generate_multipart_upload_urls."""
    s3 = get_s3_client()

    if not upload_id:
        response = s3.create_multipart_upload(
            Bucket=bucket,
            Key=key,
            ContentType="application/octet-stream",
        )
        upload_id = response["UploadId"]

    part_urls = []
    for part_number in range(1, part_count + 1):
        url = s3.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": bucket,
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=expires_in,
        )
        part_urls.append(
            {
                "part_number": part_number,
                "url": url.replace(cfg.s3.endpoint, cfg.s3.public_endpoint),
            }
        )

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )

    return {
        "upload_id": upload_id,
        "part_urls": part_urls,
        "expires_at": expires_at,
    }


async def generate_multipart_upload_urls(
    bucket: str,
    key: str,
    part_count: int,
    upload_id: str = None,
    expires_in: int = 3600,
) -> dict:
    """Generate presigned URLs for multipart upload.

    For files larger than 5GB, S3 requires multipart upload.

    Args:
        bucket: S3 bucket name
        key: Object key in S3
        part_count: Number of parts to upload
        upload_id: Existing upload ID (if resuming)
        expires_in: URL expiration time in seconds

    Returns:
        Dict with 'upload_id', 'part_urls', and 'expires_at'
    """
    return await run_in_s3_executor(
        _generate_multipart_upload_urls_sync,
        bucket,
        key,
        part_count,
        upload_id,
        expires_in,
    )


def _complete_multipart_upload_sync(
    bucket: str, key: str, upload_id: str, parts: list
) -> dict:
    """Synchronous implementation of complete_multipart_upload."""
    s3 = get_s3_client()

    response = s3.complete_multipart_upload(
        Bucket=bucket,
        Key=key,
        UploadId=upload_id,
        MultipartUpload={"Parts": parts},
    )

    return response


async def complete_multipart_upload(
    bucket: str, key: str, upload_id: str, parts: list
) -> dict:
    """Complete a multipart upload.

    Args:
        bucket: S3 bucket name
        key: Object key in S3
        upload_id: Upload ID from create_multipart_upload
        parts: List of dicts with 'PartNumber' and 'ETag'

    Returns:
        S3 completion response
    """
    return await run_in_s3_executor(
        _complete_multipart_upload_sync, bucket, key, upload_id, parts
    )


def _abort_multipart_upload_sync(bucket: str, key: str, upload_id: str):
    """Synchronous implementation of abort_multipart_upload."""
    s3 = get_s3_client()
    s3.abort_multipart_upload(
        Bucket=bucket,
        Key=key,
        UploadId=upload_id,
    )


async def abort_multipart_upload(bucket: str, key: str, upload_id: str):
    """Abort a multipart upload.

    Args:
        bucket: S3 bucket name
        key: Object key in S3
        upload_id: Upload ID to abort
    """
    await run_in_s3_executor(_abort_multipart_upload_sync, bucket, key, upload_id)


def _get_object_metadata_sync(bucket: str, key: str) -> dict:
    """Synchronous implementation of get_object_metadata."""
    s3 = get_s3_client()
    response = s3.head_object(Bucket=bucket, Key=key)

    return {
        "size": response.get("ContentLength"),
        "etag": response.get("ETag", "").strip('"'),
        "last_modified": response.get("LastModified"),
        "content_type": response.get("ContentType"),
    }


async def get_object_metadata(bucket: str, key: str) -> dict:
    """Get metadata for an S3 object.

    Args:
        bucket: S3 bucket name
        key: Object key in S3

    Returns:
        Dict with 'size', 'etag', 'last_modified', 'content_type'

    Raises:
        ClientError: If object not found
    """
    return await run_in_s3_executor(_get_object_metadata_sync, bucket, key)


def _object_exists_sync(bucket: str, key: str) -> bool:
    """Synchronous implementation of object_exists."""
    s3 = get_s3_client()

    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


async def object_exists(bucket: str, key: str) -> bool:
    """Check if an object exists in S3.

    Args:
        bucket: S3 bucket name
        key: Object key in S3

    Returns:
        True if object exists, False otherwise
    """
    return await run_in_s3_executor(_object_exists_sync, bucket, key)


def parse_s3_uri(uri: str) -> tuple:
    """Parse S3 URI into bucket and key.

    Args:
        uri: S3 URI (e.g., "s3://bucket/path/to/file")

    Returns:
        Tuple of (bucket, key)

    Raises:
        ValueError: If URI is invalid
    """
    if not uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {uri}")

    parts = uri[5:].split("/", 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ""

    return bucket, key
