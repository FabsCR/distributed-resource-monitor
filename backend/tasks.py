# tasks.py
import os
import tempfile
from dotenv import load_dotenv
from celery import Celery
from PIL import Image, ImageFilter
import boto3

# 1) Load env vars
load_dotenv()

# 2) Configure Celery
app = Celery("distributed_blur", broker=os.getenv("BROKER_URL"))

# 3) Initialize S3 client
s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("MINIO_ENDPOINT"),
    aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
    aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD"),
)
BUCKET = os.getenv("MINIO_BUCKET")


@app.task
def blur_image_s3(key_in: str, key_out: str, radius: int = 5) -> str:
    print(f"[blur] start {key_in}")
    # mkstemp para Windows
    fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(key_in)[1])
    os.close(fd)

    try:
        print(f"[blur] download {key_in} → {tmp_path}")
        s3.download_file(BUCKET, key_in, tmp_path)
    except Exception as e:
        print(f"[blur][ERROR] download failed: {e}")
        raise

    try:
        print(f"[blur] processing (r={radius})")
        img = Image.open(tmp_path).filter(ImageFilter.GaussianBlur(radius))
    except Exception as e:
        print(f"[blur][ERROR] processing failed: {e}")
        raise

    base, ext = os.path.splitext(tmp_path)
    out_path = f"{base}_out{ext}"
    try:
        img.save(out_path)
        print(f"[blur] upload {out_path} → {key_out}")
        s3.upload_file(out_path, BUCKET, key_out)
    except Exception as e:
        print(f"[blur][ERROR] save/upload failed: {e}")
        raise

    # cleanup
    for p in (tmp_path, out_path):
        try: os.remove(p)
        except: pass

    print(f"[blur] done {key_in}")
    return key_out


@app.task
def heavy_image_pipeline_s3(key_in: str, key_out: str,
                            scale_factor: float = 2.0,
                            filters: list[dict] = None) -> str:
    print(f"[heavy] start {key_in}")
    fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(key_in)[1])
    os.close(fd)

    try:
        print(f"[heavy] download {key_in} → {tmp_path}")
        s3.download_file(BUCKET, key_in, tmp_path)
    except Exception as e:
        print(f"[heavy][ERROR] download failed: {e}")
        raise

    try:
        img = Image.open(tmp_path)
        print(f"[heavy] resize x{scale_factor}")
        w, h = img.size
        img = img.resize((int(w*scale_factor), int(h*scale_factor)), Image.LANCZOS)
    except Exception as e:
        print(f"[heavy][ERROR] resize failed: {e}")
        raise

    for f in filters or []:
        t = f.get("type")
        try:
            print(f"[heavy] filter '{t}'")
            if t == "gaussian":
                img = img.filter(ImageFilter.GaussianBlur(f.get("radius", 5)))
            elif t == "box":
                img = img.filter(ImageFilter.BoxBlur(f.get("radius", 5)))
            elif t == "detail":
                img = img.filter(ImageFilter.DETAIL)
            elif t == "sharpen":
                img = img.filter(ImageFilter.UnsharpMask(
                    radius=f.get("radius", 2),
                    percent=f.get("percent", 150),
                    threshold=f.get("threshold", 3)
                ))
            elif t == "edge_enhance":
                img = img.filter(ImageFilter.EDGE_ENHANCE)
            elif t == "edge_enhance_more":
                img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
        except Exception as e:
            print(f"[heavy][ERROR] filter '{t}' failed: {e}")
            raise

    base, ext = os.path.splitext(tmp_path)
    out_path = f"{base}_out{ext}"
    try:
        img.save(out_path)
        print(f"[heavy] upload {out_path} → {key_out}")
        s3.upload_file(out_path, BUCKET, key_out)
    except Exception as e:
        print(f"[heavy][ERROR] save/upload failed: {e}")
        raise

    for p in (tmp_path, out_path):
        try: os.remove(p)
        except: pass

    print(f"[heavy] done {key_in}")
    return key_out
