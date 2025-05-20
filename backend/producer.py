# producer.py
import os
from dotenv import load_dotenv
import boto3
from tasks import blur_image_s3, heavy_image_pipeline_s3

# 1) Load env
load_dotenv()

# 2) Config
MINIO_ENDPOINT   = os.getenv("MINIO_ENDPOINT")
MINIO_USER       = os.getenv("MINIO_ROOT_USER")
MINIO_PASS       = os.getenv("MINIO_ROOT_PASSWORD")
BUCKET           = os.getenv("MINIO_BUCKET")
RADIUS           = int(os.getenv("BLUR_RADIUS",5))
SCALE            = float(os.getenv("SCALE_FACTOR",2.0))
FILTERS_PIPELINE = [
    {"type":"gaussian","radius":15},
    {"type":"box",     "radius":10},
    {"type":"detail"},
    {"type":"edge_enhance_more"},
    {"type":"sharpen","radius":2,"percent":200,"threshold":3},
]

# 3) S3 client for listing
s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_USER,
    aws_secret_access_key=MINIO_PASS,
)

print("[producer] Listing 'samples/'…")
paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=BUCKET, Prefix="samples/"):
    for obj in page.get("Contents", []):
        key = obj["Key"]
        if key.endswith("/"):
            continue

        print(f"[producer] Enqueuing {key}")
        blur_image_s3.apply_async(
            args=[key, f"outputs/blur_{os.path.basename(key)}", RADIUS],
            priority=1
        )
        heavy_image_pipeline_s3.apply_async(
            args=[key, f"outputs/filters_{os.path.basename(key)}"],
            kwargs={"scale_factor": SCALE, "filters": FILTERS_PIPELINE},
            priority=10
        )

print("[producer] All tasks enqueued.")
