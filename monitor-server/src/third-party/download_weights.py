"""Download AI model weights into the third-party/ directory.

Run once before first deployment:
    python src/third-party/download_weights.py

In production the third-party/ directory is mounted from the host so weights
persist across container restarts.
"""
import os
from pathlib import Path

THIRD_PARTY = Path(__file__).resolve().parent


def download_yolo(model: str = "yolo11n.pt") -> Path | None:
    """Download YOLO11 weights to third-party/yolo/.  ~5.4 MB for nano."""
    dest = THIRD_PARTY / "yolo"
    dest.mkdir(exist_ok=True)
    target = dest / model
    if target.exists():
        print(f"  SKIP  {target}  (already present)")
        return target

    # YOLO() downloads to CWD — chdir into dest so it lands there
    cwd = os.getcwd()
    os.chdir(str(dest))
    try:
        from ultralytics import YOLO
        _ = YOLO(model)
        downloaded = dest / model
        if downloaded.exists():
            print(f"  OK    {downloaded}")
        else:
            print(f"  WARN  {model} not found — may be cached by ultralytics")
    finally:
        os.chdir(cwd)
    return target


def download_slowfast() -> Path | None:
    """Download SlowFast R-50 Kinetics-400 classification weights.  ~140 MB."""
    dest = THIRD_PARTY / "slowfast"
    dest.mkdir(exist_ok=True)
    target = dest / "SLOWFAST_8x8_R50.pkl"
    if target.exists():
        print(f"  SKIP  {target}  (already present)")
        return target

    import torch
    try:
        from pytorchvideo.models.hub import slowfast_r50
        model = slowfast_r50(pretrained=True)
        torch.save(model.state_dict(), target)
        mb = target.stat().st_size // 1024 // 1024
        print(f"  OK    {target}  [{mb} MB]")
    except Exception as e:
        print(f"  WARN  SlowFast download failed: {e}")
        print(f"  HINT  Download manually and place in {dest}")
        return None
    return target


def download_slowfast_ava() -> Path | None:
    """Download SlowFast R-50 AVA detection weights.  ~258 MB.

    Trained on Kinetics-400, fine-tuned on AVA 2.2 (60 action classes
    including smoking, drinking, talking on phone).
    """
    import urllib.request

    dest = THIRD_PARTY / "slowfast"
    dest.mkdir(exist_ok=True)
    target = dest / "SLOWFAST_8x8_R50_DETECTION.pyth"
    if target.exists():
        print(f"  SKIP  {target}  (already present)")
        return target

    url = (
        "https://dl.fbaipublicfiles.com/pytorchvideo/model_zoo/ava/"
        "SLOWFAST_8x8_R50_DETECTION.pyth"
    )
    print(f"  Downloading {url} ...")
    try:
        urllib.request.urlretrieve(url, str(target))
        mb = target.stat().st_size // 1024 // 1024
        print(f"  OK    {target}  [{mb} MB]")
    except Exception as e:
        print(f"  WARN  SlowFast AVA download failed: {e}")
        print(f"  HINT  Download manually from {url} and place in {dest}")
        return None
    return target


def download_yamnet() -> Path | None:
    """Download YAMNet via tensorflow-hub.  AudioSet 521-class model."""
    dest = THIRD_PARTY / "yamnet"
    dest.mkdir(exist_ok=True)
    target = dest / "yamnet_tfhub"
    if target.exists():
        print(f"  SKIP  {target}  (already present)")
        return target

    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    try:
        import tensorflow_hub as hub
        model = hub.load("https://tfhub.dev/google/yamnet/1")
        tf.saved_model.save(model, str(target))
        print(f"  OK    {target}")
    except Exception as e:
        print(f"  WARN  YAMNet tfhub download failed: {e}")
        print(f"  HINT  YAMNet auto-downloads on first hub.load() call")
        return None
    return target


def verify_face_recognition() -> None:
    """face_recognition models are shipped with the pip package (small)."""
    import face_recognition
    print(f"  OK    face_recognition  (bundled with package, no download needed)")


def main() -> None:
    print("Monitor Server — AI model weight download\n")
    download_yolo("yolo11n.pt")
    download_slowfast()
    download_slowfast_ava()
    download_yamnet()
    verify_face_recognition()
    print(f"\nAll weights ready in {THIRD_PARTY}")


if __name__ == "__main__":
    main()
