"""S3 storage browser endpoints for admin API."""

from fastapi import APIRouter, Depends, HTTPException

from kohakuhub.async_utils import run_in_s3_executor
from kohakuhub.logger import get_logger
from kohakuhub.utils.s3 import get_s3_client
from kohakuhub.api.admin.utils import verify_admin_token

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
        buckets = s3.list_buckets()

        bucket_info = []
        for bucket in buckets.get("Buckets", []):
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


@router.get("/storage/objects/{bucket}")
async def list_s3_objects(
    bucket: str,
    prefix: str = "",
    limit: int = 100,
    _admin: bool = Depends(verify_admin_token),
):
    """List S3 objects in a bucket.

    Args:
        bucket: Bucket name
        prefix: Key prefix filter
        limit: Maximum objects to return
        _admin: Admin authentication (dependency)

    Returns:
        List of S3 objects
    """

    def _list_objects():
        s3 = get_s3_client()

        try:
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=limit)

            objects = []
            for obj in response.get("Contents", []):
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
                "is_truncated": response.get("IsTruncated", False),
                "key_count": len(objects),
            }
        except Exception as e:
            logger.error(f"Failed to list objects in bucket {bucket}: {e}")
            raise HTTPException(500, detail={"error": str(e)})

    result = await run_in_s3_executor(_list_objects)

    return result
