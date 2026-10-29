"""Crop Disease Detection: Flask web application for a student project.

The app requires a model trained with train_model.py before predictions can run.
Uploaded leaf images are processed in memory and are not stored on disk.
"""
from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from flask import Flask, flash, redirect, render_template, request, url_for
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.utils import secure_filename

from disease_guide import get_disease_guide, readable_label
from database import get_recent_predictions, init_db, save_prediction

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model"
MODEL_PATH = MODEL_DIR / "crop_disease_model.keras"
CLASS_NAMES_PATH = MODEL_DIR / "class_names.json"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
IMAGE_SIZE = 160

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-student-project-change-me")
app.config["MAX_CONTENT_LENGTH"] = 42 * 1024 * 1024  # Five 8 MB photos plus multipart overhead

_MODEL = None
_CLASS_NAMES: list[str] | None = None


def model_is_ready() -> bool:
    return MODEL_PATH.is_file() and CLASS_NAMES_PATH.is_file()


def load_predictor():
    """Load the trained model only when the first prediction is requested."""
    global _MODEL, _CLASS_NAMES
    if not model_is_ready():
        raise RuntimeError(
            "The disease model has not been trained yet. Follow the Training section in README.md."
        )
    if _MODEL is None or _CLASS_NAMES is None:
        try:
            import tensorflow as tf
        except ImportError as exc:
            raise RuntimeError(
                "TensorFlow is not installed in this Python environment. Activate .venv and run "
                "python -m pip install -r requirements.txt."
            ) from exc
        try:
            _MODEL = tf.keras.models.load_model(MODEL_PATH)
            with CLASS_NAMES_PATH.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            # The training script writes a JSON list. The dict form is accepted for compatibility.
            _CLASS_NAMES = payload if isinstance(payload, list) else payload.get("class_names", [])
            if not _CLASS_NAMES:
                raise ValueError("No class names were found in model/class_names.json.")
        except Exception as exc:
            _MODEL = None
            _CLASS_NAMES = None
            raise RuntimeError(
                f"Could not load the trained model: {exc}. Please rerun train_model.py."
            ) from exc
    return _MODEL, _CLASS_NAMES


def image_to_preview_data(image: Image.Image) -> str:
    """Return a downsized image preview as a data URI; don't keep uploaded files."""
    preview = ImageOps.contain(image.copy(), (900, 900))
    buffer = io.BytesIO()
    preview.save(buffer, format="JPEG", quality=86, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def predict_image(image: Image.Image) -> tuple[list[dict[str, Any]], list[str]]:
    model, class_names = load_predictor()
    resized = image.convert("RGB").resize((IMAGE_SIZE, IMAGE_SIZE))
    batch = np.expand_dims(np.asarray(resized, dtype=np.float32), axis=0)
    probabilities = np.asarray(model.predict(batch, verbose=0))[0]
    if len(probabilities) != len(class_names):
        raise RuntimeError(
            "The model output does not match class_names.json. Please retrain the model."
        )
    top_indices = np.argsort(probabilities)[::-1][: min(3, len(probabilities))]
    results: list[dict[str, Any]] = []
    for index in top_indices:
        raw_label = class_names[int(index)]
        crop, disease = readable_label(raw_label)
        results.append({
            "raw_label": raw_label,
            "crop": crop,
            "disease": disease,
            "confidence": float(probabilities[int(index)]) * 100,
            "guide": get_disease_guide(raw_label),
        })
    return results, class_names


@app.context_processor
def inject_common_values():
    return {"model_ready": model_is_ready()}


def analyze_upload(upload) -> dict[str, Any]:
    """Validate and analyse one uploaded image without storing the original photo."""
    original_name = upload.filename or "crop-photo"
    safe_name = secure_filename(original_name)
    extension = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"{original_name}: use a JPG, JPEG, PNG, or WEBP image.")

    image_bytes = upload.read(8 * 1024 * 1024 + 1)
    if not image_bytes:
        raise ValueError(f"{original_name}: the selected file is empty.")
    if len(image_bytes) > 8 * 1024 * 1024:
        raise ValueError(f"{original_name}: the image is larger than 8 MB.")

    try:
        with Image.open(io.BytesIO(image_bytes)) as opened:
            opened.verify()
        with Image.open(io.BytesIO(image_bytes)) as opened:
            crop_image = ImageOps.exif_transpose(opened).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"{original_name}: this file could not be read as an image.") from exc

    if crop_image.width < 40 or crop_image.height < 40:
        raise ValueError(f"{original_name}: the image is too small. Choose a clearer photo.")

    preview_data = image_to_preview_data(crop_image)
    results, _ = predict_image(crop_image)
    best = results[0]
    save_prediction(best["crop"], best["disease"], best["confidence"])
    return {
        "file_name": safe_name or "crop-photo",
        "result": best,
        "alternatives": results[1:],
        "preview_data": preview_data,
        "low_confidence": best["confidence"] < 45,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        mode = request.form.get("upload_mode", "single")
        if mode == "multiple":
            uploads = [item for item in request.files.getlist("crop_images") if item and item.filename]
            if not uploads:
                flash("Choose at least one crop or leaf photo before starting detection.", "error")
                return redirect(url_for("index"))
            if len(uploads) > 5:
                flash("You can analyse up to 5 photos at a time.", "error")
                return redirect(url_for("index"))
        else:
            uploaded = request.files.get("leaf_image")
            if uploaded is None or not uploaded.filename:
                flash("Choose a leaf image before starting detection.", "error")
                return redirect(url_for("index"))
            uploads = [uploaded]
            mode = "single"

        if not model_is_ready():
            flash("The model is not trained yet. Follow README.md → Train the model, then try again.", "warning")
            return redirect(url_for("index"))

        try:
            analysed = [analyze_upload(upload) for upload in uploads]
            if mode == "multiple":
                return render_template(
                    "index.html",
                    multi_results=analysed,
                    recent=get_recent_predictions(5),
                )
            one = analysed[0]
            return render_template(
                "index.html",
                result=one["result"],
                alternatives=one["alternatives"],
                preview_data=one["preview_data"],
                low_confidence=one["low_confidence"],
                recent=get_recent_predictions(5),
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))
        except RuntimeError as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))
        except Exception as exc:  # Fail gracefully for a student demo.
            app.logger.exception("Prediction failed")
            flash(f"Prediction failed ({type(exc).__name__}). Check the terminal for details.", "error")
            return redirect(url_for("index"))

    return render_template("index.html", recent=get_recent_predictions(5))

@app.route("/history")
def history():
    return render_template("history.html", predictions=get_recent_predictions(100))


@app.route("/about")
def about():
    return render_template("about.html")


@app.errorhandler(413)
def file_too_large(_error):
    flash("The upload is too large. Each photo must be 8 MB or less, with up to 5 photos per batch.", "error")
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    # Local-only development server. Do not expose this debug server to the internet.
    app.run(host="127.0.0.1", port=5000, debug=True)
