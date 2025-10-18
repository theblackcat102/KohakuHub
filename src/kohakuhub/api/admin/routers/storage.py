"""S3 storage browser endpoints for admin API."""

from fastapi import APIRouter, Depends, HTTPException

from kohakuhub.async_utils import run_in_s3_executor
from kohakuhub.config import cfg
from kohakuhub.logger import get_logger
from kohakuhub.api.admin.utils import verify_admin_token
from kohakuhub.utils.s3 import get_s3_client

logger = get_logger("ADMIN")
router = APIRouter()


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
        s3 = get_s3_client()

        # Try two strategies for R2/path-style compatibility
        strategies = [
            {"bucket": bucket_name, "name": "with bucket name"},
            {"bucket": "", "name": "with empty bucket (endpoint has path)"},
        ]

        last_exception = None
        for strategy in strategies:
            try:
                test_bucket = strategy["bucket"]
                logger.info(
                    f"Trying strategy '{strategy['name']}': Bucket='{test_bucket}', Prefix='{prefix}'"
                )

                response = s3.list_objects_v2(
                    Bucket=test_bucket,
                    Prefix=prefix,
                    MaxKeys=limit,
                )

                # Log full response structure
                logger.info(f"Response keys: {list(response.keys())}")
                logger.info(f"Full response (excluding metadata): {dict((k, v) for k, v in response.items() if k != 'ResponseMetadata')}")

                contents = response.get("Contents", [])
                common_prefixes = response.get("CommonPrefixes", [])
                logger.info(f"Contents count: {len(contents)}")
                logger.info(f"CommonPrefixes count: {len(common_prefixes)}")

                if common_prefixes:
                    logger.info(f"CommonPrefixes: {common_prefixes}")

                # Log first few object keys if any exist
                if contents:
                    sample_keys = [obj["Key"] for obj in contents[:3]]
                    logger.success(
                        f"✓ Strategy '{strategy['name']}' worked! Found {len(contents)} objects"
                    )
                    logger.info(f"Sample keys: {sample_keys}")

                    # Build result and return
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
                else:
                    logger.warning(
                        f"✗ Strategy '{strategy['name']}' returned 0 objects"
                    )

            except Exception as e:
                logger.error(f"✗ Strategy '{strategy['name']}' failed: {e}")
                last_exception = e

        # If we get here, all strategies failed or returned empty
        if last_exception:
            logger.error(f"All strategies failed. Last error: {last_exception}")
            raise HTTPException(500, detail={"error": str(last_exception)})
        else:
            logger.warning("All strategies returned 0 objects - storage might be empty")
            return {
                "objects": [],
                "bucket": bucket_name,
                "is_truncated": False,
                "key_count": 0,
            }

    result = await run_in_s3_executor(_list_objects)

    logger.info(f"Returning {result['key_count']} objects to client")
    return result
