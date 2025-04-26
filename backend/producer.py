import os
from dotenv import load_dotenv
import boto3
from tasks import blur_image_s3, heavy_image_pipeline_s3

# 1) Load environment variables from .env
load_dotenv()

# 2) Retrieve configuration parameters from environment
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_USER     = os.getenv("MINIO_ROOT_USER")
MINIO_PASS     = os.getenv("MINIO_ROOT_PASSWORD")
BUCKET         = os.getenv("MINIO_BUCKET")

# Processing settings (can also be set via .env)
RADIUS          = int(os.getenv("BLUR_RADIUS", 5))
SCALE           = float(os.getenv("SCALE_FACTOR", 2.0))
FILTERS_PIPELINE = [
    {"type": "gaussian",        "radius": 15},
    {"type": "box",             "radius": 10},
    {"type": "detail"},
    {"type": "edge_enhance_more"},
    {"type": "sharpen",         "radius": 2, "percent": 200, "threshold": 3},
]

# 3) Initialize S3-compatible client for MinIO
s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_USER,
    aws_secret_access_key=MINIO_PASS,
)

# 4) List all images under the 'samples/' prefix in the bucket
paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=BUCKET, Prefix="samples/"):
    for obj in page.get("Contents", []):
        key_in = obj["Key"]
        # Skip directory placeholders
        if key_in.endswith("/"):
            continue

        filename = os.path.basename(key_in)
        key_blur_out    = f"outputs/blur_{filename}"
        key_filters_out = f"outputs/filters_{filename}"

        # 5) Enqueue Celery tasks for processing
        blur_image_s3.delay(key_in, key_blur_out, RADIUS)
        heavy_image_pipeline_s3.delay(
            key_in,
            key_filters_out,
            scale_factor=SCALE,
            filters=FILTERS_PIPELINE
        )

        print(f"Enqueued blur:   {key_in} → {key_blur_out}")
        print(f"Enqueued filter: {key_in} → {key_filters_out}")
