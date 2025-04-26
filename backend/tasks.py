import os
import tempfile
from dotenv import load_dotenv
from celery import Celery
from PIL import Image, ImageFilter
import boto3

# 1) Load environment variables
load_dotenv()

# 2) Configure Celery with Redis broker
app = Celery("distributed_blur", broker=os.getenv("BROKER_URL"))

# 3) Initialize S3-compatible client pointing to MinIO
s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("MINIO_ENDPOINT"),
    aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
    aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD"),
)
BUCKET = os.getenv("MINIO_BUCKET")

@app.task
def blur_image_s3(key_in: str, key_out: str, radius: int = 5) -> str:
    # Download the image from MinIO
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(key_in)[1]) as tmp:
        s3.download_file(BUCKET, key_in, tmp.name)
        # Apply Gaussian blur filter
        img = Image.open(tmp.name).filter(ImageFilter.GaussianBlur(radius))
        # Construct output filename preserving extension
        base, ext = os.path.splitext(tmp.name)
        out_tmp = f"{base}_out{ext}"
        img.save(out_tmp)
        # Upload processed image back to MinIO
        s3.upload_file(out_tmp, BUCKET, key_out)
    return key_out

@app.task
def heavy_image_pipeline_s3(
    key_in: str,
    key_out: str,
    scale_factor: float = 2.0,
    filters: list[dict] = None
) -> str:
    # Download the original image
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(key_in)[1]) as tmp:
        s3.download_file(BUCKET, key_in, tmp.name)
        img = Image.open(tmp.name)
        # Resize image by scale factor
        w, h = img.size
        img = img.resize((int(w * scale_factor), int(h * scale_factor)), Image.LANCZOS)
        # Apply filter pipeline
        for f in filters or []:
            t = f.get("type")
            if t == "gaussian":
                img = img.filter(ImageFilter.GaussianBlur(f.get("radius", 5)))
            elif t == "box":
                img = img.filter(ImageFilter.BoxBlur(f.get("radius", 5)))
            elif t == "detail":
                img = img.filter(ImageFilter.DETAIL)
            elif t == "sharpen":
                img = img.filter(
                    ImageFilter.UnsharpMask(
                        radius=f.get("radius", 2),
                        percent=f.get("percent", 150),
                        threshold=f.get("threshold", 3)
                    )
                )
            elif t == "edge_enhance":
                img = img.filter(ImageFilter.EDGE_ENHANCE)
            elif t == "edge_enhance_more":
                img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
        # Construct output filename preserving extension
        base, ext = os.path.splitext(tmp.name)
        out_tmp = f"{base}_out{ext}"
        img.save(out_tmp)
        # Upload processed image back to MinIO
        s3.upload_file(out_tmp, BUCKET, key_out)
    return key_out
