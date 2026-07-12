"""SlowFast queueing and action event publishing."""

from __future__ import annotations

import logging
import os
import re
from collections import defaultdict, deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from src.constants import SlowFastActionType
from src.service.vision_module.vision_event_bus import ACTION, event_bus

logger = logging.getLogger(__name__)

_CLIP_LENGTH = 32
_KINETICS_CROP_SIZE = 224
_KINETICS_ALPHA = 4
_KINETICS_MEAN = np.array([0.45, 0.45, 0.45], dtype=np.float32)
_KINETICS_STD = np.array([0.225, 0.225, 0.225], dtype=np.float32)
_AVA_CROP_SIZE = 224
_AVA_DEFAULT_THRESHOLD = 0.75
_AVA_MAX_RESULTS = 3

_ACTION_KEYWORDS: tuple[tuple[SlowFastActionType, tuple[str, ...]], ...] = (
    (SlowFastActionType.WALKING, ("walking", "walk")),
    (SlowFastActionType.RUNNING, ("running", "jogging", "sprinting", "run")),
    (SlowFastActionType.FALLING, ("falling", "tripping", "fall")),
    (SlowFastActionType.FIGHTING, ("fighting", "boxing", "punching", "wrestling", "kicking")),
    (SlowFastActionType.CLIMBING, ("climbing", "climb")),
    (SlowFastActionType.THROWING, ("throwing", "throw")),
    (SlowFastActionType.POINTING, ("pointing", "point")),
    (SlowFastActionType.WAVING, ("waving", "wave")),
    (SlowFastActionType.HUGGING, ("hugging", "hug")),
    (SlowFastActionType.PUSHING, ("pushing", "shoving", "push")),
    (SlowFastActionType.SITTING, ("sitting", "sit")),
    (SlowFastActionType.STANDING, ("standing", "stand")),
    (SlowFastActionType.LYING_DOWN, ("lying", "lie", "sleeping", "sleep", "lay")),
    (SlowFastActionType.LOITERING, ("loitering", "loiter", "linger", "idle")),
    (SlowFastActionType.CROWDING, ("crowding", "crowd", "gather", "group")),
)

_AVA_ACTION_KEYWORDS: tuple[tuple[SlowFastActionType, tuple[str, ...]], ...] = (
    (SlowFastActionType.SMOKING, ("smoke", "smoking")),
    (SlowFastActionType.FALLING, ("fall down", "lie/sleep", "trip")),
    (SlowFastActionType.FIGHTING, ("fight/hit", "martial art", "grab", "kick")),
    (SlowFastActionType.RUNNING, ("run/jog",)),
    (SlowFastActionType.WALKING, ("walk",)),
    (SlowFastActionType.STANDING, ("stand",)),
    (SlowFastActionType.SITTING, ("sit",)),
    (SlowFastActionType.WAVING, ("wave",)),
    (SlowFastActionType.THROWING, ("throw",)),
    (SlowFastActionType.CLIMBING, ("climb", "crawl", "crouch")),
    (SlowFastActionType.LYING_DOWN, ("lie/sleep", "fall down")),
    (SlowFastActionType.LOITERING, ("linger", "idle")),
    (SlowFastActionType.CLIMBING, ("climb",)),
    (SlowFastActionType.THROWING, ("throw",)),
    (SlowFastActionType.POINTING, ("point to",)),
    (SlowFastActionType.WAVING, ("hand wave",)),
    (SlowFastActionType.HUGGING, ("hug",)),
    (SlowFastActionType.PUSHING, ("push",)),
    (SlowFastActionType.SITTING, ("sit",)),
    (SlowFastActionType.STANDING, ("stand",)),
    (SlowFastActionType.WALKING, ("walk",)),
)

_AVA_EXCLUSIVE_ACTIONS = {
    SlowFastActionType.FALLING,
    SlowFastActionType.RUNNING,
    SlowFastActionType.CLIMBING,
    SlowFastActionType.SITTING,
    SlowFastActionType.STANDING,
    SlowFastActionType.WALKING,
}


class SlowFastState(Enum):
    IDLE = auto()
    ACTIVE = auto()
    ERROR = auto()


@dataclass
class ActionResult:
    track_id: int
    action_type_id: int
    label: str
    confidence: float
    source: str


InferenceFn = Callable[[list[np.ndarray]], ActionResult | None]


class SlowFastRunner:
    """Maintain per-track clip queues and publish ActionType events."""

    def __init__(
        self,
        *,
        clip_length: int = _CLIP_LENGTH,
        kinetics_infer: InferenceFn | None = None,
        ava_infer: InferenceFn | None = None,
        enable_real_kinetics: bool = False,
        enable_real_ava: bool = False,
        kinetics_labels_path: str | Path | None = None,
        kinetics_weights_path: str | Path | None = None,
        ava_labels_path: str | Path | None = None,
        ava_weights_path: str | Path | None = None,
        kinetics_confidence_threshold: float = 0.05,
        ava_confidence_threshold: float = _AVA_DEFAULT_THRESHOLD,
        ava_max_results: int = _AVA_MAX_RESULTS,
        device: str | None = None,
    ) -> None:
        self.clip_length = clip_length
        self._queues: defaultdict[int, deque[np.ndarray]] = defaultdict(
            lambda: deque(maxlen=self.clip_length),
        )
        self._state = SlowFastState.IDLE
        self._kinetics_infer = kinetics_infer
        self._ava_infer = ava_infer
        self._models_loaded = False
        self._enable_real_kinetics = enable_real_kinetics
        self._enable_real_ava = enable_real_ava
        self._kinetics_model = None
        self._ava_model = None
        self._kinetics_labels = self._load_kinetics_labels(kinetics_labels_path)
        self._ava_labels = self._load_ava_labels(ava_labels_path)
        self._kinetics_weights_path = self._resolve_kinetics_weights_path(kinetics_weights_path)
        self._ava_weights_path = self._resolve_ava_weights_path(ava_weights_path)
        self._kinetics_confidence_threshold = kinetics_confidence_threshold
        self._ava_confidence_threshold = ava_confidence_threshold
        self._ava_max_results = ava_max_results
        self._device = device
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="slowfast")
        self._pending: dict[int, Future] = {}  # track_id → inference future

    @property
    def state(self) -> SlowFastState:
        return self._state

    def load(self) -> bool:
        """Load optional SlowFast models once."""

        if self._models_loaded:
            return True
        if not self._enable_real_kinetics and not self._enable_real_ava:
            self._models_loaded = True
            return True

        try:
            import torch
            from pytorchvideo.models.hub import slowfast_r50, slowfast_r50_detection

            self._device = self._device or ("cuda" if torch.cuda.is_available() else "cpu")
            if self._enable_real_kinetics:
                if self._kinetics_weights_path.exists():
                    self._kinetics_model = slowfast_r50(pretrained=False)
                    state_dict = _load_checkpoint_state(torch, self._kinetics_weights_path)
                    self._kinetics_model.load_state_dict(state_dict)
                else:
                    self._kinetics_model = slowfast_r50(pretrained=True)
                self._kinetics_model.eval()
                self._kinetics_model.to(self._device)

            if self._enable_real_ava:
                if self._ava_weights_path.exists():
                    self._ava_model = slowfast_r50_detection(pretrained=False)
                    state_dict = _load_checkpoint_state(torch, self._ava_weights_path)
                    self._ava_model.load_state_dict(state_dict)
                else:
                    self._ava_model = slowfast_r50_detection(pretrained=True)
                self._ava_model.eval()
                self._ava_model.to(self._device)
        except Exception:
            logger.exception("Failed to load real SlowFast model")
            self._state = SlowFastState.ERROR
            return False
        self._models_loaded = True
        return True

    def enqueue(self, track_id: int, frame_crop: np.ndarray) -> list[ActionResult]:
        """Enqueue frame; submit inference to thread pool when clip is ready.

        Returns [] — actual results arrive asynchronously via collect_results().
        """
        queue = self._queues[track_id]
        queue.append(frame_crop.copy())
        self._state = SlowFastState.ACTIVE

        if len(queue) < self.clip_length:
            if len(queue) == 1:
                logger.info("[SlowFast] track %d: started collecting (need %d frames)",
                             track_id, self.clip_length)
            elif len(queue) % 8 == 0:
                logger.info("[SlowFast] track %d: %d/%d frames collected",
                             track_id, len(queue), self.clip_length)
            return []

        logger.info("[SlowFast] track %d: clip ready, submitting to thread pool", track_id)
        clip = list(queue)
        queue.clear()
        # 推理扔到线程池，不阻塞主循环
        self._pending[track_id] = self._executor.submit(self._infer, track_id, clip)
        return []

    def collect_results(self) -> list[ActionResult]:
        """Harvest completed inference futures. Call from main loop each frame."""
        results: list[ActionResult] = []
        for track_id, fut in list(self._pending.items()):
            if not fut.done():
                continue
            del self._pending[track_id]
            try:
                result = fut.result()
            except Exception:
                logger.exception("[SlowFast] inference failed for track %d", track_id)
                continue
            if result:
                logger.info("[SlowFast] track %d: result=%s", track_id,
                             [(r.action_type_id, r.confidence) for r in result])
            else:
                logger.info("[SlowFast] track %d: no action detected in clip", track_id)
            results.extend(result)
        return results

    async def enqueue_and_publish(
        self,
        track_id: int,
        frame_crop: np.ndarray,
        view_id: int,
    ) -> list[ActionResult]:
        results = self.enqueue(track_id, frame_crop)
        if results:
            await event_bus.publish(
                ACTION,
                {
                    "view_id": view_id,
                    "actions": [
                        {
                            "track_id": result.track_id,
                            "action_type_id": result.action_type_id,
                            "label": result.label,
                            "confidence": result.confidence,
                            "source": result.source,
                        }
                        for result in results
                    ],
                },
            )
        return results

    def clear_track(self, track_id: int) -> None:
        self._queues.pop(track_id, None)
        if not self._queues:
            self._state = SlowFastState.IDLE

    def _infer(self, track_id: int, clip: list[np.ndarray]) -> list[ActionResult]:
        results: list[ActionResult] = []
        if self._kinetics_infer is not None:
            result = self._kinetics_infer(clip)
            if result is not None:
                result.track_id = track_id
                results.append(result)
        else:
            result = self.infer_kinetics(track_id, clip)
            if result is not None:
                results.append(result)

        if self._ava_infer is not None:
            result = self._ava_infer(clip)
            if result is not None:
                result.track_id = track_id
                results.append(result)
        else:
            results.extend(self.infer_ava(track_id, clip))
        return results

    def infer_kinetics(
        self,
        track_id: int,
        clip_32frames: list[np.ndarray],
    ) -> ActionResult | None:
        """Run opt-in Kinetics inference."""

        if not self._enable_real_kinetics:
            return None
        if not self.load() or self._kinetics_model is None:
            return None

        try:
            import torch

            inputs = self._preprocess_kinetics_clip(clip_32frames)
            inputs = [pathway.to(self._device) for pathway in inputs]
            with torch.no_grad():
                logits = self._kinetics_model(inputs)
                scores = torch.softmax(logits, dim=1)[0]
                confidences, indices = torch.topk(scores, k=min(5, scores.numel()))

            for confidence, index in zip(confidences.tolist(), indices.tolist()):
                if confidence < self._kinetics_confidence_threshold:
                    continue
                label = self._label_for_index(index)
                action = map_kinetics_label_to_action(label)
                if action is not None:
                    return ActionResult(
                        track_id=track_id,
                        action_type_id=int(action),
                        label=action.name,
                        confidence=float(confidence),
                        source=f"slowfast_kinetics:{label}",
                    )
        except Exception:
            logger.exception("SlowFast Kinetics inference failed")
            self._state = SlowFastState.ERROR
        return None

    def infer_ava(
        self,
        track_id: int,
        clip_32frames: list[np.ndarray],
    ) -> list[ActionResult]:
        """Run AVA per-box action inference."""

        if not self._enable_real_ava:
            return []
        if not self.load() or self._ava_model is None:
            return []

        try:
            import torch

            inputs = self._preprocess_ava_clip(clip_32frames)
            inputs = [pathway.to(self._device) for pathway in inputs]
            boxes = self._make_ava_full_crop_box().to(self._device)
            with torch.no_grad():
                logits = self._ava_model(inputs, boxes)
                scores = torch.sigmoid(logits)[0]

            # 诊断：打印 top-5 预测（不管阈值）
            top_indices = torch.topk(scores, k=min(5, scores.numel())).indices.tolist()
            top_scores = [float(scores[i]) for i in top_indices]
            top_labels = [(self._ava_label_for_index(i), top_scores[j])
                           for j, i in enumerate(top_indices)]
            logger.info("[SlowFast AVA] track %d: top5=%s", track_id, top_labels)

            candidates: list[ActionResult] = []
            for index, confidence in enumerate(scores.tolist()):
                if confidence < self._ava_confidence_threshold:
                    continue
                label = self._ava_label_for_index(index)
                action = map_ava_label_to_action(label)
                if action is not None:
                    candidates.append(ActionResult(
                        track_id=track_id,
                        action_type_id=int(action),
                        label=action.name,
                        confidence=float(confidence),
                        source=f"slowfast_ava:{label}",
                    ))
            if not candidates:
                # 低于阈值但最高分也打印出来，便于调阈值
                max_conf = max(scores.tolist()) if scores.numel() > 0 else 0.0
                logger.info("[SlowFast AVA] track %d: all below threshold (max=%.3f, thresh=%.2f)",
                             track_id, max_conf, self._ava_confidence_threshold)
            return _select_ava_results(candidates, max_results=self._ava_max_results)
        except Exception:
            logger.exception("SlowFast AVA inference failed")
            self._state = SlowFastState.ERROR
            return []

    def _preprocess_ava_clip(self, clip_32frames: list[np.ndarray]):
        return self._preprocess_kinetics_clip(clip_32frames)

    def _make_ava_full_crop_box(self):
        try:
            import torch
        except Exception as exc:
            raise RuntimeError("torch is required for real SlowFast AVA inference") from exc

        return torch.tensor(
            [[0.0, 0.0, 0.0, float(_AVA_CROP_SIZE - 1), float(_AVA_CROP_SIZE - 1)]],
            dtype=torch.float32,
        )

    def _resolve_ava_weights_path(self, weights_path: str | Path | None) -> Path:
        if weights_path:
            return Path(weights_path)
        env_path = os.getenv("SLOWFAST_AVA_WEIGHTS")
        if env_path:
            return Path(env_path)
        return (
            Path(__file__).resolve().parents[3]
            / "third-party"
            / "slowfast"
            / "SLOWFAST_8x8_R50_DETECTION.pyth"
        )

    def _resolve_kinetics_weights_path(self, weights_path: str | Path | None) -> Path:
        if weights_path:
            return Path(weights_path)
        env_path = os.getenv("SLOWFAST_KINETICS_WEIGHTS")
        if env_path:
            return Path(env_path)
        return (
            Path(__file__).resolve().parents[3]
            / "third-party"
            / "slowfast"
            / "SLOWFAST_8x8_R50.pkl"
        )

    def _preprocess_kinetics_clip(self, clip_32frames: list[np.ndarray]):
        try:
            import torch
        except Exception as exc:
            raise RuntimeError("torch is required for real SlowFast inference") from exc

        if not clip_32frames:
            raise ValueError("SlowFast clip is empty")

        frames = [
            _preprocess_frame_for_kinetics(frame, _KINETICS_CROP_SIZE)
            for frame in clip_32frames
        ]
        fast_pathway = torch.from_numpy(np.stack(frames)).permute(3, 0, 1, 2).unsqueeze(0)
        fast_pathway = fast_pathway.float()

        fast_t = fast_pathway.shape[2]
        slow_t = max(1, fast_t // _KINETICS_ALPHA)
        slow_indices = torch.linspace(0, fast_t - 1, slow_t).long()
        slow_pathway = torch.index_select(fast_pathway, 2, slow_indices)
        return [slow_pathway, fast_pathway]

    def _label_for_index(self, index: int) -> str:
        if 0 <= index < len(self._kinetics_labels):
            return self._kinetics_labels[index]
        return f"kinetics_{index}"

    def _load_kinetics_labels(self, labels_path: str | Path | None) -> list[str]:
        candidates: list[Path] = []
        if labels_path:
            candidates.append(Path(labels_path))
        env_path = os.getenv("KINETICS_LABELS_PATH")
        if env_path:
            candidates.append(Path(env_path))
        candidates.append(
            Path(__file__).resolve().parents[3]
            / "third-party"
            / "slowfast"
            / "kinetics_classnames.txt",
        )

        for candidate in candidates:
            if not candidate.exists():
                continue
            labels = [_parse_label_line(line) for line in candidate.read_text(encoding="utf-8").splitlines()]
            labels = [label for label in labels if label]
            if labels:
                return labels
        return []

    def _ava_label_for_index(self, index: int) -> str:
        if 0 <= index < len(self._ava_labels):
            return self._ava_labels[index]
        return f"ava_{index}"

    def _load_ava_labels(self, labels_path: str | Path | None) -> list[str]:
        candidates: list[Path] = []
        if labels_path:
            candidates.append(Path(labels_path))
        env_path = os.getenv("AVA_LABELS_PATH")
        if env_path:
            candidates.append(Path(env_path))
        candidates.append(
            Path(__file__).resolve().parents[3]
            / "third-party"
            / "slowfast"
            / "ava_action_list_v2.1_for_activitynet_2018.pbtxt",
        )

        for candidate in candidates:
            if not candidate.exists():
                continue
            labels = _parse_ava_pbtxt(candidate.read_text(encoding="utf-8"))
            if labels:
                return labels
        return _default_ava_labels()


def _preprocess_frame_for_kinetics(frame: np.ndarray, crop_size: int) -> np.ndarray:
    if frame.size == 0:
        raise ValueError("SlowFast frame crop is empty")

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width = rgb.shape[:2]
    scale = crop_size / min(height, width)
    resized = cv2.resize(
        rgb,
        (max(crop_size, int(round(width * scale))), max(crop_size, int(round(height * scale)))),
        interpolation=cv2.INTER_LINEAR,
    )
    resized_height, resized_width = resized.shape[:2]
    x1 = (resized_width - crop_size) // 2
    y1 = (resized_height - crop_size) // 2
    cropped = resized[y1 : y1 + crop_size, x1 : x1 + crop_size]
    normalized = cropped.astype(np.float32) / 255.0
    return (normalized - _KINETICS_MEAN) / _KINETICS_STD


def map_kinetics_label_to_action(label: str) -> SlowFastActionType | None:
    normalized = label.lower().replace("_", " ")
    for action, keywords in _ACTION_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return action
    return None


def map_ava_label_to_action(label: str) -> SlowFastActionType | None:
    normalized = label.lower().replace("_", " ")
    for action, keywords in _AVA_ACTION_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return action
    return None


def _select_ava_results(
    candidates: list[ActionResult],
    *,
    max_results: int,
) -> list[ActionResult]:
    best_by_action: dict[int, ActionResult] = {}
    for candidate in candidates:
        existing = best_by_action.get(candidate.action_type_id)
        if existing is None or candidate.confidence > existing.confidence:
            best_by_action[candidate.action_type_id] = candidate

    unique = sorted(best_by_action.values(), key=lambda result: result.confidence, reverse=True)
    exclusive = [
        result
        for result in unique
        if SlowFastActionType(result.action_type_id) in _AVA_EXCLUSIVE_ACTIONS
    ]
    non_exclusive = [
        result
        for result in unique
        if SlowFastActionType(result.action_type_id) not in _AVA_EXCLUSIVE_ACTIONS
    ]

    selected = non_exclusive[: max(0, max_results - 1)]
    if exclusive and len(selected) < max_results:
        selected.append(exclusive[0])
    if not selected:
        selected = unique[:max_results]
    return sorted(selected, key=lambda result: result.confidence, reverse=True)


def _parse_ava_pbtxt(text: str) -> list[str]:
    entries: list[tuple[int, str]] = []
    for block in re.findall(r"item\s*\{(.*?)\}", text, flags=re.DOTALL):
        name_match = re.search(r'name:\s*"([^"]+)"', block)
        id_match = re.search(r"id:\s*(\d+)", block)
        if not name_match or not id_match:
            continue
        entries.append((int(id_match.group(1)), name_match.group(1)))
    if not entries:
        return []

    labels = [""] * max(action_id for action_id, _ in entries)
    for action_id, name in entries:
        labels[action_id - 1] = name
    return labels


def _default_ava_labels() -> list[str]:
    labels = [""] * 80
    defaults = {
        5: "fall down",
        8: "lie/sleep",
        9: "martial art",
        10: "run/jog",
        11: "sit",
        12: "stand",
        14: "walk",
        20: "climb (e.g., a mountain)",
        43: "point to (an object)",
        46: "push (an object)",
        54: "smoke",
        58: "throw",
        64: "fight/hit (a person)",
        66: "grab (a person)",
        69: "hand wave",
        70: "hug (a person)",
        76: "push (another person)",
    }
    for action_id, name in defaults.items():
        labels[action_id - 1] = name
    return labels


def _load_checkpoint_state(torch_module, checkpoint_path: Path):
    checkpoint = torch_module.load(checkpoint_path, map_location="cpu")
    if isinstance(checkpoint, dict) and "model_state" in checkpoint:
        return checkpoint["model_state"]
    return checkpoint


def _parse_label_line(line: str) -> str:
    value = line.strip().strip('"').strip("'")
    if not value:
        return ""
    first, _, rest = value.partition(" ")
    if first.isdigit() and rest:
        return rest.strip().strip('"').strip("'")
    return value


def make_action_result(
    track_id: int,
    action: SlowFastActionType,
    confidence: float,
    source: str = "mock",
) -> ActionResult:
    return ActionResult(
        track_id=track_id,
        action_type_id=int(action),
        label=action.name,
        confidence=confidence,
        source=source,
    )
