"""S3 storage browser endpoints for admin API."""

from urllib.parse import urlparse

import boto3
from botocore.config import Config as BotoConfig
from fastapi import APIRouter, Depends, HTTPException

from kohakuhub.async_utils import run_in_s3_executor
from kohakuhub.config import cfg
from kohakuhub.logger import get_logger
from kohakuhub.api.admin.utils import verify_admin_token
from kohakuhub.utils.s3 import get_s3_client

logger = get_logger("ADMIN")
router = APIRouter()


@router.get("/storage/debug")
async def debug_s3_config(
    _admin: bool = Depends(verify_admin_token),
):
    """Debug S3 configuration and test connectivity.

    Returns diagnostic information about S3 setup.
    """

    def _debug():
        s3 = get_s3_client()

        info = {
            "endpoint": cfg.s3.endpoint,
            "bucket": cfg.s3.bucket,
            "region": cfg.s3.region,
            "force_path_style": cfg.s3.force_path_style,
        }

        # Test 1: Can we access the bucket?
        try:
            head_response = s3.head_bucket(Bucket=cfg.s3.bucket)
            info["bucket_accessible"] = True
            info["head_bucket_response"] = str(
                head_response.get("ResponseMetadata", {})
            )
        except Exception as e:
            info["bucket_accessible"] = False
            info["head_bucket_error"] = str(e)

        # Test 2: Try list with different parameters
        for test_name, params in [
            ("Standard", {"Bucket": cfg.s3.bucket, "MaxKeys": 10}),
            (
                "With Delimiter",
                {"Bucket": cfg.s3.bucket, "Delimiter": "/", "MaxKeys": 10},
            ),
            ("No MaxKeys", {"Bucket": cfg.s3.bucket}),
        ]:
            try:
                response = s3.list_objects_v2(**params)
                result = {
                    "success": True,
                    "response_keys": list(response.keys()),
                    "key_count": response.get("KeyCount", "N/A"),
                    "contents_count": len(response.get("Contents", [])),
                    "common_prefixes_count": len(response.get("CommonPrefixes", [])),
                }
                if response.get("Contents"):
                    result["sample_keys"] = [
                        obj["Key"] for obj in response.get("Contents", [])[:3]
                    ]
                info[f"test_{test_name}"] = result
            except Exception as e:
                info[f"test_{test_name}"] = {"success": False, "error": str(e)}

        return info

    result = await run_in_s3_executor(_debug)
    logger.info(f"S3 Debug Info: {result}")

    return result


@router.get("/storage/buckets")
async def list_s3_buckets(
    _admin: bool = Depends(verify_admin_token),
):
    """List S3 buckets and their sizes.

    Args:
        _admin: Admin authentication (dependency)

    Returns:
        List of buckets with sizes
    """

    def _list_buckets():
        s3 = get_s3_client()

        try:
            buckets = s3.list_buckets()
            logger.info(f"list_buckets() response: {buckets}")
        except Exception as e:
            logger.error(f"Failed to list buckets: {e}")
            # For R2/path-style, list_buckets might not work
            # Return configured bucket as fallback
            return [
                {
                    "name": cfg.s3.bucket,
                    "creation_date": "N/A",
                    "total_size": 0,
                    "object_count": 0,
                    "note": "Using configured bucket (list_buckets not supported)",
                }
            ]

        bucket_list = buckets.get("Buckets", [])
        logger.info(f"Found {len(bucket_list)} buckets")

        # If no buckets returned (R2 path-style issue), use configured bucket
        if not bucket_list:
            logger.warning("list_buckets returned empty, using configured bucket")
            return [
                {
                    "name": cfg.s3.bucket,
                    "creation_date": "N/A",
                    "total_size": 0,
                    "object_count": 0,
                    "note": "Using configured bucket",
                }
            ]

        bucket_info = []
        for bucket in bucket_list:
            bucket_name = bucket["Name"]

            # Get bucket size (sum of all objects)
            try:
                total_size = 0
                paginator = s3.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket_name):
                    for obj in page.get("Contents", []):
                        total_size += obj.get("Size", 0)

                object_count = sum(
                    len(page.get("Contents", []))
                    for page in paginator.paginate(Bucket=bucket_name)
                )

                bucket_info.append(
                    {
                        "name": bucket_name,
                        "creation_date": bucket["CreationDate"].isoformat(),
                        "total_size": total_size,
                        "object_count": object_count,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to get size for bucket {bucket_name}: {e}")
                bucket_info.append(
                    {
                        "name": bucket_name,
                        "creation_date": bucket["CreationDate"].isoformat(),
                        "total_size": 0,
                        "object_count": 0,
                        "error": str(e),
                    }
                )

        return bucket_info

    buckets = await run_in_s3_executor(_list_buckets)

    return {"buckets": buckets}


@router.get("/storage/objects")
@router.get("/storage/objects/{bucket}")
async def list_s3_objects(
    bucket: str = "",
    prefix: str = "",
    limit: int = 1000,
    _admin: bool = Depends(verify_admin_token),
):
    """List S3 objects in configured bucket or specified bucket.

    Args:
        bucket: Bucket name (empty = use configured bucket)
        prefix: Key prefix filter
        limit: Maximum objects to return
        _admin: Admin authentication (dependency)

    Returns:
        List of S3 objects
    """

    # Use configured bucket if not specified
    bucket_name = bucket if bucket else cfg.s3.bucket

    logger.info(
        f"Listing S3 objects: bucket={bucket_name}, prefix={prefix}, limit={limit}"
    )
    logger.info(f"S3 endpoint: {cfg.s3.endpoint}")
    logger.info(f"S3 bucket config: {cfg.s3.bucket}")

    def _list_objects():
        # Parse endpoint URL to extract path (for R2 with path-in-endpoint)
        parsed = urlparse(cfg.s3.endpoint)
        endpoint_path = parsed.path.strip("/")  # e.g., "sizigi-deepghs-grant"

        # Determine actual bucket, endpoint, and prefix
        if endpoint_path:
            # Endpoint has path - first component is bucket, rest is base prefix
            path_parts = endpoint_path.split("/")
            root_endpoint = f"{parsed.scheme}://{parsed.netloc}"
            actual_bucket = path_parts[0]  # "sizigi-deepghs-grant"

            # Combine remaining path parts + configured bucket + user prefix
            base_prefix_parts = path_parts[1:] + [bucket_name]  # ["hub-storage"]
            base_prefix = "/".join(base_prefix_parts)

            # Add user-requested prefix
            if prefix:
                actual_prefix = f"{base_prefix}/{prefix}"
            else:
                actual_prefix = f"{base_prefix}/" if base_prefix else ""

            logger.info(f"Endpoint path detected: '{endpoint_path}'")
            logger.info(f"Root endpoint: {root_endpoint}")
            logger.info(f"Actual bucket: {actual_bucket}")
            logger.info(f"Base prefix: {base_prefix}")
            logger.info(f"Final prefix: {actual_prefix}")

            # Create client with root endpoint
            s3_config = {}
            if cfg.s3.force_path_style:
                s3_config["addressing_style"] = "path"

            boto_config = BotoConfig(signature_version="s3v4", s3=s3_config)

            s3 = boto3.client(
                "s3",
                endpoint_url=root_endpoint,
                aws_access_key_id=cfg.s3.access_key,
                aws_secret_access_key=cfg.s3.secret_key,
                region_name=cfg.s3.region,
                config=boto_config,
            )
        else:
            # Standard S3/MinIO - use configured client as-is
            actual_bucket = bucket_name
            actual_prefix = prefix
            s3 = get_s3_client()
            logger.info(
                f"Standard S3 endpoint - bucket: {actual_bucket}, prefix: {actual_prefix}"
            )

        try:
            logger.info(
                f"Calling list_objects_v2(Bucket='{actual_bucket}', Prefix='{actual_prefix}', MaxKeys={limit})"
            )

            response = s3.list_objects_v2(
                Bucket=actual_bucket,
                Prefix=actual_prefix,
                MaxKeys=limit,
            )

            # Log ResponseMetadata
            metadata = response.get("ResponseMetadata", {})
            logger.info(
                f"ResponseMetadata HTTPStatusCode: {metadata.get('HTTPStatusCode')}"
            )
            logger.info(f"ResponseMetadata RequestId: {metadata.get('RequestId')}")

            # Log all response fields
            logger.info(f"Response keys: {list(response.keys())}")
            for key in ["Name", "Prefix", "KeyCount", "MaxKeys", "IsTruncated"]:
                if key in response:
                    logger.info(f"{key}: {response[key]}")

            contents = response.get("Contents", [])
            logger.info(f"Contents count: {len(contents)}")

            if contents:
                logger.success(f"Found {len(contents)} objects!")
                logger.info(f"First 3 keys: {[obj['Key'] for obj in contents[:3]]}")

            # Strip base prefix from keys for frontend display
            # So frontend sees relative paths from their perspective
            strip_prefix = f"{base_prefix}/" if endpoint_path and base_prefix else ""
            logger.info(
                f"Stripping prefix '{strip_prefix}' from object keys for frontend"
            )

            objects = []
            for obj in contents:
                original_key = obj["Key"]
                # Remove base prefix to show relative path
                display_key = (
                    original_key[len(strip_prefix) :]
                    if strip_prefix and original_key.startswith(strip_prefix)
                    else original_key
                )

                objects.append(
                    {
                        "key": display_key,  # Relative path for frontend
                        "full_key": original_key,  # Full S3 key
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                        "storage_class": obj.get("StorageClass", "STANDARD"),
                    }
                )

            if objects:
                logger.info(
                    f"Sample display keys: {[obj['key'] for obj in objects[:3]]}"
                )

            return {
                "objects": objects,
                "bucket": bucket_name,
                "is_truncated": response.get("IsTruncated", False),
                "key_count": len(objects),
            }
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            logger.exception("Full exception:", e)
            raise HTTPException(500, detail={"error": str(e)})

    result = await run_in_s3_executor(_list_objects)

    logger.info(f"Returning {result['key_count']} objects to client")
    return result


# ========== S3 Storage Management Operations (Admin Only) ==========

# In-memory store for delete confirmations (TTL: 60 seconds)
_delete_confirmations = {}


@router.delete("/storage/objects/{key:path}")
async def delete_s3_object(
    key: str,
    _admin: bool = Depends(verify_admin_token),
):
    """Delete a single S3 object.

    Args:
        key: Full S3 object key (path parameter, auto URL-decoded)
        _admin: Admin authentication

    Returns:
        Success message
    """

    def _delete():
        s3 = get_s3_client()
        s3.delete_object(Bucket=cfg.s3.bucket, Key=key)
        return {"deleted": 1}

    result = await run_in_s3_executor(_delete)
    logger.warning(f"Admin deleted S3 object: {key}")

    return {"success": True, "message": f"Object deleted: {key}"}


@router.post("/storage/prefix/prepare-delete")
async def prepare_delete_prefix(
    prefix: str,
    _admin: bool = Depends(verify_admin_token),
):
    """Step 1: Prepare prefix deletion (generate confirmation token).

    Returns estimated object count and confirmation token.
    Token expires in 60 seconds.

    Args:
        prefix: S3 prefix to delete
        _admin: Admin authentication

    Returns:
        Confirmation token, prefix, estimated count, expiration
    """
    import time
    import uuid

    # Count objects with prefix
    def _count():
        s3 = get_s3_client()
        paginator = s3.get_paginator("list_objects_v2")
        count = 0
        for page in paginator.paginate(Bucket=cfg.s3.bucket, Prefix=prefix):
            count += len(page.get("Contents", []))
        return count

    estimated = await run_in_s3_executor(_count)

    # Generate confirmation token
    token = str(uuid.uuid4())
    _delete_confirmations[token] = {
        "prefix": prefix,
        "timestamp": time.time(),
        "estimated_count": estimated,
    }

    # Cleanup old tokens (>60 seconds)
    current_time = time.time()
    expired = [
        t
        for t, data in _delete_confirmations.items()
        if current_time - data["timestamp"] > 60
    ]
    for t in expired:
        del _delete_confirmations[t]

    logger.warning(f"Admin prepared delete for prefix: {prefix} ({estimated} objects)")

    return {
        "confirm_token": token,
        "prefix": prefix,
        "estimated_objects": estimated,
        "expires_in": 60,
    }


@router.delete("/storage/prefix")
async def delete_s3_prefix(
    prefix: str,
    confirm_token: str,
    _admin: bool = Depends(verify_admin_token),
):
    """Step 2: Delete all objects under prefix (requires confirmation token).

    Args:
        prefix: S3 prefix to delete
        confirm_token: Token from /prepare-delete
        _admin: Admin authentication

    Returns:
        Success message with deleted count
    """
    import time
    from kohakuhub.utils.s3 import delete_objects_with_prefix

    # Validate confirmation token
    if confirm_token not in _delete_confirmations:
        raise HTTPException(400, detail="Invalid or expired confirmation token")

    confirmation = _delete_confirmations[confirm_token]

    # Check token not expired
    if time.time() - confirmation["timestamp"] > 60:
        del _delete_confirmations[confirm_token]
        raise HTTPException(400, detail="Confirmation token expired (60 seconds)")

    # Check prefix matches
    if confirmation["prefix"] != prefix:
        raise HTTPException(400, detail="Prefix mismatch with confirmation token")

    # Delete objects
    deleted_count = await delete_objects_with_prefix(cfg.s3.bucket, prefix)

    # Cleanup confirmation token
    del _delete_confirmations[confirm_token]

    logger.warning(f"Admin deleted S3 prefix: {prefix} ({deleted_count} objects)")

    return {"success": True, "deleted_count": deleted_count, "prefix": prefix}
