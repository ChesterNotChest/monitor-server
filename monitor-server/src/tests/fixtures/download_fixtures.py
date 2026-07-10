"""下载测试数据集到 tests/fixtures/。

Run once before first test run:
    cd monitor-server
    python src/tests/fixtures/download_fixtures.py

脚本自动下载并跳过已存在的文件，可重复运行。
"""

import os
import shutil
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

FIXTURES_DIR = Path(__file__).resolve().parent

_COCO8_URL = "https://ultralytics.com/assets/coco8.zip"
_COCO8_SIZE = 1  # MB
_LFW_SIZE = 0.5  # MB (subset)
_US8K_SIZE = 5   # MB (subset)


def download_coco8() -> None:
    dest = FIXTURES_DIR / "coco8"
    if dest.exists() and list(dest.glob("images/val/*.jpg")):
        print(f"  SKIP  {dest}  (already present)")
        return

    zip_path = FIXTURES_DIR / "coco8.zip"
    print(f"  Downloading COCO8 ({_COCO8_SIZE} MB) ...")
    urlretrieve(_COCO8_URL, str(zip_path))
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(FIXTURES_DIR)
    zip_path.unlink()
    # ultralytics zip extracts to coco8/
    actual = FIXTURES_DIR / "coco8"
    if actual.exists():
        print(f"  OK    {actual}")
    else:
        print(f"  WARN  extraction failed — expected {actual}")


def download_lfw_subset() -> None:
    """LFW 数据集太大（~200 MB），fixture 目录提供占位说明。

    Face 单元测试在 Part B 实现时选择具体人脸。
    """
    dest = FIXTURES_DIR / "lfw_subset"
    dest.mkdir(exist_ok=True)
    note = dest / "README.md"
    if note.exists():
        print(f"  SKIP  lfw_subset/  (placeholder present)")
        return
    note.write_text(
        "# LFW Subset\n\n"
        "来源: [Labeled Faces in the Wild](http://vis-www.cs.umass.edu/lfw/)\n\n"
        "Part B 开发时从此数据集中选取 10 张人脸（5 known + 5 unknown），\n"
        "用 face_recognition 提取 128D 特征向量后对比。\n"
    )
    print(f"  OK    {dest}/README.md")


def download_urbansound_subset() -> None:
    """UrbanSound8K 数据集太大（~6 GB），fixture 目录提供占位说明。

    YAMNet 单元测试在 Part C 实现时选择具体音频。
    """
    dest = FIXTURES_DIR / "urbansound_subset"
    dest.mkdir(exist_ok=True)
    note = dest / "README.md"
    if note.exists():
        print(f"  SKIP  urbansound_subset/  (placeholder present)")
        return
    note.write_text(
        "# UrbanSound8K Subset\n\n"
        "来源: [UrbanSound8K](https://github.com/anubhav6864/UrbanSound8k-Classification)\n\n"
        "Part C 开发时从此数据集中选取 5 个 WAV：\n"
        "- gun_shot  (GUNSHOT)\n"
        "- siren     (SIREN)\n"
        "- dog_bark  (DOG_BARKING)\n"
        "- car_horn  (CAR_HORN)\n"
        "- street_music (SILENCE if no match)\n\n"
        "放入本目录即可，YAMNet 单元测试自动读取。\n"
    )
    print(f"  OK    {dest}/README.md")


def main() -> None:
    print("Monitor Server — test fixture download\n")
    download_coco8()
    download_lfw_subset()
    download_urbansound_subset()
    print(f"\nFixtures ready in {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
