import os
from celery import Celery
from PIL import Image, ImageFilter
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

BROKER_URL = os.getenv("BROKER_URL")
app = Celery("distributed_blur", broker=BROKER_URL)

@app.task
def blur_image(input_path: str, output_path: str, radius: int = None) -> str:
    """Apply a Gaussian blur and save the result."""
    r = radius or int(os.getenv("BLUR_RADIUS", 5))
    img = Image.open(input_path)
    blurred = img.filter(ImageFilter.GaussianBlur(r))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    blurred.save(output_path)
    return output_path

@app.task
def heavy_image_pipeline(
    input_path: str,
    output_path: str,
    scale_factor: float = 2.0,
    filters: list[dict] = None
) -> str:
    # Load and scale
    img = Image.open(input_path)
    w, h = img.size
    img = img.resize(
        (int(w * scale_factor), int(h * scale_factor)),
        Image.LANCZOS
    )

    # Apply filter pipeline
    for f in filters or []:
        t = f.get("type")
        if t == "gaussian":
            img = img.filter(
                ImageFilter.GaussianBlur(f.get("radius", 5))
            )
        elif t == "box":
            img = img.filter(
                ImageFilter.BoxBlur(f.get("radius", 5))
            )
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

    # Save the final image
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    return output_path
