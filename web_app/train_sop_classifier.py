"""
Train YOLOv8n-cls on the HATREC assembly dataset.
=================================================
Extracts frames from each cycle/task video, organizes into
classification format, and trains a YOLOv8n-cls model.

Dataset structure expected:
  archive/VideoDataset/Cycles/Cycle_X/Cycle_X_task_Y.mp4

Output:
  weights/sop_classifier.pt — fine-tuned YOLOv8n-cls

Usage:
  python train_sop_classifier.py
"""

import os
import sys
import random
import shutil
import cv2
import glob
from pathlib import Path

# ── Config ────────────────────────────────────────────
DATASET_ROOT = os.path.join("archive", "VideoDataset", "Cycles")
OUTPUT_DATASET = os.path.join("dataset_sop_cls")
WEIGHTS_DIR = "weights"
MODEL_OUTPUT = os.path.join(WEIGHTS_DIR, "sop_classifier.pt")

NUM_TASKS = 7
FRAMES_PER_VIDEO = 8          # extract N frames per task video
TRAIN_SPLIT = 0.85            # 85% train, 15% val
IMG_SIZE = 224                # YOLOv8-cls default
EPOCHS = 30                   # training epochs
BATCH_SIZE = 32

TASK_NAMES = [
    "task_0_assembling_spring",
    "task_1_placing_white_part",
    "task_2_screwing_1",
    "task_3_inflating_valve",
    "task_4_placing_black_part",
    "task_5_screwing_2",
    "task_6_fixing_cable",
]


def extract_frames_from_video(video_path: str, n_frames: int = 8) -> list:
    """Extract evenly spaced frames from a video."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  [WARN] Cannot open: {video_path}")
        return []

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        cap.release()
        return []

    # Evenly spaced indices, skip first and last 10% to avoid transitions
    start = max(0, int(total * 0.1))
    end = min(total - 1, int(total * 0.9))
    if end <= start:
        start, end = 0, total - 1

    indices = [int(start + i * (end - start) / max(n_frames - 1, 1)) for i in range(n_frames)]
    indices = sorted(set(indices))

    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            # Resize for consistency
            frame = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
            frames.append(frame)

    cap.release()
    return frames


def build_dataset():
    """Extract frames from all cycles and create classification dataset."""
    print("=" * 60)
    print("  SOP Classifier — Dataset Builder")
    print("=" * 60)

    if not os.path.isdir(DATASET_ROOT):
        print(f"ERROR: Dataset not found at {DATASET_ROOT}")
        sys.exit(1)

    # Clean output
    if os.path.exists(OUTPUT_DATASET):
        shutil.rmtree(OUTPUT_DATASET)

    # Create directories
    for split in ["train", "val"]:
        for task_name in TASK_NAMES:
            os.makedirs(os.path.join(OUTPUT_DATASET, split, task_name), exist_ok=True)

    # Find all cycle directories
    cycle_dirs = sorted(glob.glob(os.path.join(DATASET_ROOT, "Cycle_*")))
    print(f"\nFound {len(cycle_dirs)} cycles")

    # Split cycles into train/val
    random.seed(42)
    random.shuffle(cycle_dirs)
    split_idx = int(len(cycle_dirs) * TRAIN_SPLIT)
    train_cycles = cycle_dirs[:split_idx]
    val_cycles = cycle_dirs[split_idx:]

    print(f"  Train: {len(train_cycles)} cycles")
    print(f"  Val:   {len(val_cycles)} cycles")

    total_images = 0

    for split_name, cycles in [("train", train_cycles), ("val", val_cycles)]:
        for cycle_dir in cycles:
            cycle_name = os.path.basename(cycle_dir)
            for task_id in range(NUM_TASKS):
                # Find the video file
                pattern = os.path.join(cycle_dir, f"*task_{task_id}.mp4")
                matches = glob.glob(pattern)
                if not matches:
                    # Try alternate naming
                    pattern2 = os.path.join(cycle_dir, f"*task_{task_id}*.mp4")
                    matches = glob.glob(pattern2)

                if not matches:
                    continue

                video_path = matches[0]
                frames = extract_frames_from_video(video_path, FRAMES_PER_VIDEO)

                task_name = TASK_NAMES[task_id]
                for fi, frame in enumerate(frames):
                    fname = f"{cycle_name}_task{task_id}_f{fi}.jpg"
                    out_path = os.path.join(OUTPUT_DATASET, split_name, task_name, fname)
                    cv2.imwrite(out_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    total_images += 1

        # Count per class
        for task_name in TASK_NAMES:
            folder = os.path.join(OUTPUT_DATASET, split_name, task_name)
            count = len(os.listdir(folder)) if os.path.isdir(folder) else 0
            print(f"  {split_name}/{task_name}: {count} images")

    print(f"\nTotal images: {total_images}")
    return total_images


def train_model():
    """Train YOLOv8n-cls on the prepared dataset."""
    print("\n" + "=" * 60)
    print("  SOP Classifier — Training YOLOv8n-cls")
    print("=" * 60)

    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    os.makedirs(WEIGHTS_DIR, exist_ok=True)

    # Load pretrained YOLOv8n-cls
    model = YOLO("yolov8n-cls.pt")

    print(f"\nDataset: {OUTPUT_DATASET}")
    print(f"Classes: {NUM_TASKS} ({', '.join(TASK_NAMES)})")
    print(f"Epochs:  {EPOCHS}")
    print(f"ImgSize: {IMG_SIZE}")
    print(f"Batch:   {BATCH_SIZE}")
    print()

    # Train
    results = model.train(
        data=OUTPUT_DATASET,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        project=WEIGHTS_DIR,
        name="sop_cls",
        exist_ok=True,
        verbose=True,
        patience=10,
        lr0=0.001,
        # Data augmentation for robustness
        hsv_h=0.015,
        hsv_s=0.3,
        hsv_v=0.2,
        flipud=0.0,        # don't flip up-down (assembly orientation matters)
        fliplr=0.3,         # slight horizontal flip
        degrees=5.0,        # slight rotation
    )

    # Copy best weights
    best_path = os.path.join(WEIGHTS_DIR, "sop_cls", "weights", "best.pt")
    if os.path.exists(best_path):
        shutil.copy2(best_path, MODEL_OUTPUT)
        print(f"\n✅ Best model saved to: {MODEL_OUTPUT}")
    else:
        # Try to find any weights
        last_path = os.path.join(WEIGHTS_DIR, "sop_cls", "weights", "last.pt")
        if os.path.exists(last_path):
            shutil.copy2(last_path, MODEL_OUTPUT)
            print(f"\n✅ Last model saved to: {MODEL_OUTPUT}")
        else:
            print("\n❌ No model weights found after training!")

    return results


def test_model():
    """Quick test of the trained model."""
    if not os.path.exists(MODEL_OUTPUT):
        print("No trained model found. Run training first.")
        return

    from ultralytics import YOLO
    model = YOLO(MODEL_OUTPUT)

    # Test on a few validation images
    val_dir = os.path.join(OUTPUT_DATASET, "val")
    for task_name in TASK_NAMES:
        task_dir = os.path.join(val_dir, task_name)
        if not os.path.isdir(task_dir):
            continue
        images = os.listdir(task_dir)[:2]
        for img_name in images:
            img_path = os.path.join(task_dir, img_name)
            results = model(img_path, verbose=False)
            if results:
                top1 = results[0].probs.top1
                top1_conf = float(results[0].probs.top1conf)
                predicted = model.names[top1]
                correct = "✅" if predicted == task_name else "❌"
                print(f"  {correct} {img_name}: predicted={predicted} ({top1_conf:.2f}), actual={task_name}")


if __name__ == "__main__":
    # Step 1: Build dataset
    n = build_dataset()

    if n == 0:
        print("No images extracted. Check dataset path.")
        sys.exit(1)

    # Step 2: Train
    train_model()

    # Step 3: Quick test
    print("\n" + "=" * 60)
    print("  Quick Validation Test")
    print("=" * 60)
    test_model()

    print("\n✅ Training complete! Model saved to:", MODEL_OUTPUT)
    print("   Restart the server to use the trained classifier for SOP validation.")
