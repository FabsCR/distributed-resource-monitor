import os
from tasks import blur_image, heavy_image_pipeline
from dotenv import load_dotenv

load_dotenv()

in_dir   = os.getenv("INPUT_DIR", "samples")
out_dir  = os.getenv("OUTPUT_DIR", "outputs")
radius   = int(os.getenv("BLUR_RADIUS", 5))
scale    = float(os.getenv("SCALE_FACTOR", 2.0))

# Filters pipeline
filters_pipeline = [
    {"type": "gaussian",        "radius": 15},
    {"type": "box",             "radius": 10},
    {"type": "detail"},
    {"type": "edge_enhance_more"},
    {"type": "sharpen",         "radius": 2, "percent": 200, "threshold": 3},
]

for fname in os.listdir(in_dir):
    in_path      = os.path.join(in_dir, fname)
    blur_out     = os.path.join(out_dir, f"blur_{fname}")
    filters_out  = os.path.join(out_dir, f"filters_{fname}")

    # Enqueue blur task
    blur_image.delay(in_path, blur_out, radius)
    print(f"Enqueued blur task:   {in_path} → {blur_out}")

    # Enqueue filters pipeline task
    heavy_image_pipeline.delay(
        in_path,
        filters_out,
        scale_factor=scale,
        filters=filters_pipeline
    )
    print(f"Enqueued filters task: {in_path} → {filters_out}")
