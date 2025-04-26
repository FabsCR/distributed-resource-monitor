# upload_samples.py
import os
from dotenv import load_dotenv
import boto3

load_dotenv()  

s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("MINIO_ENDPOINT"),
    aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
    aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD"),
)
bucket = os.getenv("MINIO_BUCKET")

local_dir = "samples"
for fname in os.listdir(local_dir):
    local_path = os.path.join(local_dir, fname)
    if os.path.isfile(local_path):
        key = f"samples/{fname}"
        print(f"Uploading {local_path} → {bucket}/{key}")
        s3.upload_file(local_path, bucket, key)
