"""Train an image classifier from a PlantVillage-style folder dataset.

Example:
  python train_model.py --data-dir data/PlantVillage --epochs 8

The script searches common nested archive layouts and chooses the directory whose
immediate subfolders contain image files (the class-folder directory).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
BASE_DIR = Path(__file__).resolve().parent


def has_direct_images(folder: Path) -> bool:
    try:
        return any(child.is_file() and child.suffix.lower() in IMAGE_EXTENSIONS for child in folder.iterdir())
    except OSError:
        return False


def discover_class_directory(data_dir: Path) -> Path:
    """Find a directory whose direct child folders each represent a class."""
    if not data_dir.exists():
        raise FileNotFoundError(f"Dataset folder was not found: {data_dir}")
    if not data_dir.is_dir():
        raise NotADirectoryError(f"Dataset path is not a folder: {data_dir}")

    candidates = [data_dir]
    try:
        candidates.extend(path for path in data_dir.rglob("*") if path.is_dir())
    except OSError:
        pass

    ranked: list[tuple[int, int, Path]] = []
    for folder in candidates:
        try:
            class_folders = [child for child in folder.iterdir() if child.is_dir() and has_direct_images(child)]
        except OSError:
            continue
        if len(class_folders) >= 2:
            # Prefer many classes, then the shallower directory to avoid nested false matches.
            ranked.append((len(class_folders), -len(folder.parts), folder))
    if not ranked:
        raise ValueError(
            "Could not find class folders containing images. Expected a layout like "
            "PlantVillage/Tomato___Early_blight/image.jpg. Extract the dataset ZIP and retry."
        )
    return max(ranked, key=lambda item: (item[0], item[1]))[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the crop disease image-classification model.")
    parser.add_argument("--data-dir", default="data/PlantVillage", help="Extracted dataset directory (default: data/PlantVillage)")
    parser.add_argument("--epochs", type=int, default=8, help="Training epochs (default: 8)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size (default: 32)")
    parser.add_argument("--image-size", type=int, default=160, help="Square input image size (default: 160)")
    args = parser.parse_args()

    if args.epochs < 1 or args.batch_size < 1 or args.image_size < 96:
        parser.error("epochs and batch-size must be positive; image-size must be at least 96.")

    try:
        import tensorflow as tf
    except ImportError:
        print("ERROR: TensorFlow is not installed. Activate your .venv, then run: python -m pip install -r requirements.txt")
        return 2

    data_dir = Path(args.data_dir).expanduser()
    if not data_dir.is_absolute():
        data_dir = (BASE_DIR / data_dir).resolve()

    try:
        class_dir = discover_class_directory(data_dir)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print(f"Dataset class directory: {class_dir}")
    print("Loading images and making an 80/20 training/validation split...")
    try:
        train_ds = tf.keras.utils.image_dataset_from_directory(
            class_dir, validation_split=0.2, subset="training", seed=123,
            image_size=(args.image_size, args.image_size), batch_size=args.batch_size, label_mode="int",
        )
        val_ds = tf.keras.utils.image_dataset_from_directory(
            class_dir, validation_split=0.2, subset="validation", seed=123,
            image_size=(args.image_size, args.image_size), batch_size=args.batch_size,
            label_mode="int", shuffle=False,
        )
    except Exception as exc:
        print(f"ERROR while reading dataset: {exc}")
        return 2

    class_names = list(train_ds.class_names)
    if len(class_names) < 2:
        print("ERROR: At least two class folders are required.")
        return 2
    print(f"Found {len(class_names)} classes: {', '.join(class_names[:6])}" + (" ..." if len(class_names) > 6 else ""))

    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.prefetch(buffer_size=autotune)
    val_ds = val_ds.prefetch(buffer_size=autotune)

    augmentation = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.05),
            tf.keras.layers.RandomZoom(0.10),
        ],
        name="data_augmentation",
    )
    try:
        backbone = tf.keras.applications.MobileNetV2(
            input_shape=(args.image_size, args.image_size, 3), include_top=False, weights="imagenet",
        )
    except Exception as exc:
        print("ERROR: Could not load MobileNetV2 ImageNet weights. Check your internet connection and retry.")
        print(f"Details: {exc}")
        return 2
    backbone.trainable = False

    inputs = tf.keras.Input(shape=(args.image_size, args.image_size, 3), name="leaf_image")
    x = augmentation(inputs)
    x = tf.keras.layers.Rescaling(1.0 / 127.5, offset=-1, name="mobilenet_normalization")(x)
    x = backbone(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.25)(x)
    outputs = tf.keras.layers.Dense(len(class_names), activation="softmax", name="disease_probabilities")(x)
    model = tf.keras.Model(inputs, outputs, name="crop_disease_classifier")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True),
    ]
    print(f"Training for up to {args.epochs} epochs. First run downloads pretrained weights from Keras.")
    try:
        history = model.fit(train_ds, validation_data=val_ds, epochs=args.epochs, callbacks=callbacks)
    except Exception as exc:
        print(f"ERROR during training: {exc}")
        return 2

    model_dir = BASE_DIR / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "crop_disease_model.keras"
    labels_path = model_dir / "class_names.json"
    try:
        model.save(model_path)
        with labels_path.open("w", encoding="utf-8") as f:
            json.dump(class_names, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"ERROR saving model files: {exc}")
        return 2

    final_train_acc = history.history.get("accuracy", [0])[-1] * 100
    final_val_acc = history.history.get("val_accuracy", [0])[-1] * 100
    print("\nTraining complete.")
    print(f"Model saved: {model_path}")
    print(f"Class names saved: {labels_path}")
    print(f"Last epoch training accuracy: {final_train_acc:.1f}%")
    print(f"Last epoch validation accuracy: {final_val_acc:.1f}%")
    print("These scores are dataset-specific and do not guarantee accuracy on real farm photos.")
    print("Now start the website with: python app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
