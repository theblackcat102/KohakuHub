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

            objects = []
            for obj in contents:
                objects.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                        "storage_class": obj.get("StorageClass", "STANDARD"),
                    }
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
