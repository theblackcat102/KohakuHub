"""S3 storage browser endpoints for admin API."""

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
        s3 = get_s3_client()

        # Log the actual request URL that will be constructed
        logger.info(f"S3 client endpoint: {s3.meta.endpoint_url}")
        logger.info(f"S3 client region: {s3.meta.region_name}")
        logger.info(f"S3 client config: {s3.meta.config}")

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

                # Log the exact parameters
                params = {"Bucket": test_bucket, "Prefix": prefix, "MaxKeys": limit}
                logger.info(f"list_objects_v2 params: {params}")

                response = s3.list_objects_v2(**params)

                # Log EVERYTHING in response
                logger.info(f"Response type: {type(response)}")
                logger.info(f"Response keys: {list(response.keys())}")

                for key in response.keys():
                    if key != "ResponseMetadata":
                        logger.info(f"Response['{key}']: {response[key]}")

                # Check if response has expected fields
                expected_fields = [
                    "Name",
                    "Prefix",
                    "KeyCount",
                    "MaxKeys",
                    "IsTruncated",
                ]
                for field in expected_fields:
                    logger.info(
                        f"Has '{field}': {field in response}, Value: {response.get(field, 'N/A')}"
                    )

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
