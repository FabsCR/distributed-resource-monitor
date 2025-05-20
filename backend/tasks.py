# tasks.py
import os
import time
import socket
import getpass
import tempfile

import psutil
import requests
import boto3
import psycopg2
from PIL import Image, ImageFilter
from celery import Celery
from celery.signals import task_prerun, task_postrun
from dotenv import load_dotenv
from kombu import Queue

# Load environment variables
load_dotenv()

# Configure Celery
app = Celery("distributed_blur", broker=os.getenv("BROKER_URL"))

app.conf.task_queues = [
    Queue("images", routing_key="images", queue_arguments={"x-max-priority": 10})
]
app.conf.task_default_queue = "images"
app.conf.task_default_routing_key = "images"

# Map each task to its queue
app.conf.task_routes = {
    "tasks.send_metrics": {"queue": "metrics"},
    "tasks.heavy_image_pipeline_s3": {"queue": "images"},
    "tasks.blur_image_s3": {"queue": "images"},
}

# Schedule send_metrics via Beat
app.conf.beat_schedule = {
    "send-metrics": {
        "task": "tasks.send_metrics",
        "schedule": int(os.getenv("MONITOR_INTERVAL", 5)),
        "options": {"queue": "metrics"},
    },
}

# S3 client (MinIO)
s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("MINIO_ENDPOINT"),
    aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
    aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD"),
)
BUCKET = os.getenv("MINIO_BUCKET")

# Logging heavy task status

def log_task_event(task_name: str, delivered: bool):
    """
    Insert a record into task_status_log:
      - hostname: user@host
      - task_name: name of the task (e.g. "blur image1.jpg")
      - delivered: False at start, True at finish
    """
    dsn = os.getenv("DATABASE_URL")
    hostname = f"{getpass.getuser()}@{socket.gethostname()}"
    conn = cur = None
    try:
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO task_status_log (hostname, task_name, delivered, created_at)
            VALUES (%s, %s, %s, NOW())
            """,
            (hostname, task_name, delivered)
        )
        conn.commit()
    except Exception as e:
        print(f"[log][ERROR] Could not insert into DB: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@task_prerun.connect
def before_task_run(sender=None, task_id=None, args=None, kwargs=None, **extras):
    # Only log for heavy image tasks
    if sender.name in ("tasks.blur_image_s3", "tasks.heavy_image_pipeline_s3"):
        key_in = args[0] if args else None
        filename = os.path.basename(key_in) if key_in else sender.name
        action = "blur" if sender.name == "tasks.blur_image_s3" else "heavy"
        log_task_event(f"{action} {filename}", False)


@task_postrun.connect
def after_task_run(sender=None, task_id=None, args=None, kwargs=None, retval=None, state=None, **extras):
    # Only log for heavy image tasks
    if sender.name in ("tasks.blur_image_s3", "tasks.heavy_image_pipeline_s3"):
        key_in = args[0] if args else None
        filename = os.path.basename(key_in) if key_in else sender.name
        action = "blur" if sender.name == "tasks.blur_image_s3" else "heavy"
        log_task_event(f"{action} {filename}", True)


@app.task
def blur_image_s3(key_in: str, key_out: str, radius: int = 5) -> str:
    """Download from S3, apply Gaussian blur, upload back to S3."""
    print(f"[blur] start {key_in}")
    fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(key_in)[1])
    os.close(fd)
    out_path = tmp_path + "_out" + os.path.splitext(key_in)[1]

    try:
        print(f"[blur] download {key_in} → {tmp_path}")
        s3.download_file(BUCKET, key_in, tmp_path)

        print(f"[blur] processing (r={radius})")
        img = Image.open(tmp_path).filter(ImageFilter.GaussianBlur(radius))

        img.save(out_path)
        print(f"[blur] upload {out_path} → {key_out}")
        s3.upload_file(out_path, BUCKET, key_out)

    except Exception as e:
        print(f"[blur][ERROR] {e}")
        raise

    finally:
        for p in (tmp_path, out_path):
            try:
                os.remove(p)
            except OSError:
                pass

    print(f"[blur] done {key_in}")
    return key_out


@app.task
def heavy_image_pipeline_s3(
    key_in: str,
    key_out: str,
    scale_factor: float = 2.0,
    filters: list[dict] = None
) -> str:
    """Download from S3, run filter pipeline, upload back to S3."""
    print(f"[heavy] start {key_in}")
    fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(key_in)[1])
    os.close(fd)
    out_path = tmp_path + "_out" + os.path.splitext(key_in)[1]

    try:
        print(f"[heavy] download {key_in} → {tmp_path}")
        s3.download_file(BUCKET, key_in, tmp_path)

        img = Image.open(tmp_path)
        w, h = img.size
        print(f"[heavy] resize x{scale_factor}")
        img = img.resize((int(w * scale_factor), int(h * scale_factor)), Image.LANCZOS)

        for f in filters or []:
            t = f.get("type")
            print(f"[heavy] filter '{t}'")
            if t == "gaussian":
                img = img.filter(ImageFilter.GaussianBlur(f.get("radius", 5)))
            elif t == "box":
                img = img.filter(ImageFilter.BoxBlur(f.get("radius", 5)))
            elif t == "detail":
                img = img.filter(ImageFilter.DETAIL)
            elif t == "edge_enhance_more":
                img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
            elif t == "sharpen":
                img = img.filter(ImageFilter.UnsharpMask(
                    radius=f.get("radius", 2),
                    percent=f.get("percent", 150),
                    threshold=f.get("threshold", 3)
                ))

        img.save(out_path)
        print(f"[heavy] upload {out_path} → {key_out}")
        s3.upload_file(out_path, BUCKET, key_out)

    except Exception as e:
        print(f"[heavy][ERROR] {e}")
        raise

    finally:
        for p in (tmp_path, out_path):
            try:
                os.remove(p)
            except OSError:
                pass

    print(f"[heavy] done {key_in}")
    return key_out


@app.task
def send_metrics():
    """
    Collect CPU %, RAM total/used in MB (+%),
    temperature (if available), print and send via POST.
    """
    hostname = f"{getpass.getuser()}@{socket.gethostname()}"
    ts = time.time()

    cpu_pct = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    total_mb = mem.total / (1024 * 1024)
    used_mb = mem.used / (1024 * 1024)
    used_pct = (used_mb / total_mb * 100) if total_mb else 0

    temp = None
    try:
        df_temps = getattr(psutil, "sensors_temperatures", None)
        if df_temps:
            for entries in psutil.sensors_temperatures().values():
                for entry in entries:
                    if entry.current is not None:
                        temp = round(entry.current, 1)
                        break
                if temp is not None:
                    break
    except Exception:
        temp = None

    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Host: {hostname}")
    print(f"  CPU Usage:     {cpu_pct:6.2f}%")
    print(f"  RAM Total:     {total_mb:8.2f} MB")
    print(f"  RAM Used:      {used_mb:8.2f} MB ({used_pct:6.2f}%)")
    print(f"  Temperature:   {f'{temp}°C' if temp is not None else 'N/A'}")

    payload = {
        "hostname":     hostname,
        "cpu_percent":  cpu_pct,
        "ram_total_mb": round(total_mb, 2),
        "ram_used_mb":  round(used_mb, 2),
        "ram_percent":  round(used_pct, 2),
        "temperature":  temp,
        "timestamp":    ts,
    }

    try:
        resp = requests.post(os.getenv("MONITOR_SERVER"), json=payload, timeout=3)
        resp.raise_for_status()
    except Exception as e:
        print("Metrics send error:", e)

    return "ok"
