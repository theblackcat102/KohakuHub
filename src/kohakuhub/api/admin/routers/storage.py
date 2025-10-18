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

    def _list_objects():
        s3 = get_s3_client()

        try:
            logger.debug(
                f"Calling list_objects_v2 with Bucket={bucket_name}, Prefix={prefix}"
            )
            response = s3.list_objects_v2(
                Bucket=bucket_name, Prefix=prefix, MaxKeys=limit
            )

            logger.info(f"S3 response keys: {response.keys()}")
            logger.info(f"S3 response has Contents: {'Contents' in response}")
            logger.info(
                f"S3 response Contents count: {len(response.get('Contents', []))}"
            )

            contents = response.get("Contents", [])
            if contents:
                logger.info(f"First object: {contents[0]}")

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

            logger.success(
                f"Successfully listed {len(objects)} objects from {bucket_name}"
            )

            return {
                "objects": objects,
                "bucket": bucket_name,
                "is_truncated": response.get("IsTruncated", False),
                "key_count": len(objects),
            }
        except Exception as e:
            logger.error(f"Failed to list objects in bucket {bucket_name}: {e}")
            logger.exception("Full exception details:", e)
            raise HTTPException(500, detail={"error": str(e)})

    result = await run_in_s3_executor(_list_objects)

    logger.info(f"Returning {result['key_count']} objects to client")
    return result
