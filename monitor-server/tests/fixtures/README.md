# Test Fixtures

AI 推理管线的单元测试数据。

## Files

| Fixture | Source | License | Purpose |
|---------|--------|---------|---------|
| `coco8/` | [Ultralytics COCO8](https://ultralytics.com/assets/coco8.zip) | Academic free | YOLO unit test — 8 images + labels |
| `lfw_subset/` | [Labeled Faces in the Wild](http://vis-www.cs.umass.edu/lfw/) | Academic free | Face recognition unit test — 5 known + 5 unknown |
| `urbansound_subset/` | [UrbanSound8K](https://github.com/anubhav6864/UrbanSound8k-Classification) | CC | YAMNet unit test — 5 WAV clips |

## Usage

```python
# YOLO unit test
img = cv2.imread("tests/fixtures/coco8/images/val/000000000139.jpg")
detections = yolo_detector.detect(img)
assert any(d.entity_type_id is not None for d in detections)
```
