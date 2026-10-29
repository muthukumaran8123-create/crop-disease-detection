"""Human-readable labels and general educational guidance for predicted classes."""
from __future__ import annotations

import re


def _pretty(text: str) -> str:
    text = text.replace("_", " ").replace(",", " ").replace("(", " (").strip()
    return re.sub(r"\s+", " ", text).title()


def readable_label(raw_label: str) -> tuple[str, str]:
    """Convert common PlantVillage class names into (crop, disease) display labels."""
    parts = raw_label.split("___", 1)
    crop_raw = parts[0] if parts else "Crop"
    disease_raw = parts[1] if len(parts) > 1 else "Unknown condition"
    crop = _pretty(crop_raw)
    disease_raw = disease_raw.replace("_", " ").strip()
    # Avoid repeating the crop prefix in labels such as Tomato___Tomato_mosaic_virus.
    if disease_raw.lower().startswith(crop_raw.replace(",", "").replace("_", " ").strip().lower() + " "):
        disease_raw = disease_raw[len(crop_raw.replace(",", "").replace("_", " ").strip()):].strip()
    if disease_raw.lower() == "healthy":
        disease = "Appears Healthy"
    else:
        disease = _pretty(disease_raw) or "Unknown Condition"
    return crop, disease


def get_disease_guide(raw_label: str) -> dict[str, str]:
    """Return cautious, general prevention information based on label keywords.

    This is educational guidance, not a definitive diagnosis or pesticide prescription.
    """
    _, disease = readable_label(raw_label)
    key = raw_label.lower().replace("_", " ")

    if "healthy" in key:
        return {
            "category": "Healthy leaf pattern",
            "symptoms": "The model found the image most similar to the dataset's healthy-leaf examples.",
            "prevention": "Continue checking the crop regularly, keep tools clean, follow balanced irrigation and nutrition, and monitor new growth. A healthy result does not rule out nutrient problems, pests, or diseases that are not represented in the dataset.",
        }
    if any(word in key for word in ("virus", "mosaic", "yellow leaf curl", "curl virus")):
        return {
            "category": "Possible viral disease",
            "symptoms": "Viral diseases can cause mottled or mosaic colouring, curling, yellowing, stunted growth, or distorted new leaves. Symptoms vary by crop and virus.",
            "prevention": "Use healthy planting material and resistant varieties where available. Clean tools, monitor insect vectors, and ask a local agricultural extension officer how to manage confirmed infected plants. Do not rely on this image result alone to decide removal or treatment.",
        }
    if any(word in key for word in ("bacterial", "bacteriosis")):
        return {
            "category": "Possible bacterial disease",
            "symptoms": "Some bacterial leaf diseases cause water-soaked or dark spots, angular lesions, yellow halos, or leaf blight.",
            "prevention": "Avoid handling wet plants, reduce leaf wetness where practical, clean tools between plants, and remove badly affected debris according to local guidance. Confirm the cause before applying any treatment.",
        }
    if any(word in key for word in ("mildew", "mold", "mould", "rust", "scab", "anthracnose", "esca", "black rot", "septoria", "target spot", "leaf spot", "early blight", "late blight", "blight", "rot")):
        return {
            "category": "Possible fungal or fungus-like disease",
            "symptoms": "Depending on the disease, signs may include expanding brown or black patches, yellowing, rings, powdery growth, or drying leaves. Similar symptoms can also have non-infectious causes.",
            "prevention": "Remove heavily affected fallen leaves when practical, improve airflow, avoid prolonged leaf wetness, rotate crops when appropriate, and use healthy seed or transplants. Seek local crop-specific advice before choosing a fungicide.",
        }
    if any(word in key for word in ("mite", "spider")):
        return {
            "category": "Possible pest-related damage",
            "symptoms": "Pest damage can look like stippling, speckling, bronzing, curling, or fine webbing, depending on the pest.",
            "prevention": "Inspect both sides of leaves and nearby plants for pests. Preserve beneficial insects and ask a local agricultural adviser to confirm the pest before using a control method.",
        }
    if any(word in key for word in ("nutrient", "deficiency", "chlorosis")):
        return {
            "category": "Possible nutrient or growing-condition issue",
            "symptoms": "Yellowing, pale leaves, or uneven growth may be related to nutrition, soil pH, watering, root stress, or several other causes.",
            "prevention": "Check irrigation, drainage, and recent fertiliser use. A soil test and local agricultural advice are more reliable than guessing from a leaf image.",
        }
    return {
        "category": "Possible leaf disease or stress",
        "symptoms": "Leaf spots, colour changes, curling, or drying can result from diseases, insects, nutrient imbalance, weather, or watering stress.",
        "prevention": "Take clear photos of both leaf sides, inspect other plants for similar symptoms, keep tools clean, and remove fallen debris when practical. Ask a local agricultural extension officer to confirm the cause before treating the crop.",
    }
