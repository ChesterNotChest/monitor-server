"""YAMNet 音频分类运行器 —— FFmpeg 拉 PCM → 模型推理 → EventBus SOUND。

AudioSet 521 类 → SoundType 15 类映射（ai-model-capability spec）。
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum

import numpy as np

from src.network.rtmp.puller import build_pull_url

logger = logging.getLogger(__name__)

# ── AudioSet class_id → SoundType 映射 ─────────────────
SOUND_TYPE_MAP: dict[int, int] = {
    0: 430,   # GUNSHOT
    1: 2,     # SCREAM
    2: 417,   # SIREN
    3: 457,   # EXPLOSION
    4: 441,   # GLASS_BREAKING
    5: 74,    # DOG_BARKING
    6: 424,   # CAR_HORN
    7: 491,   # ENGINE
    8: 25,    # BABY_CRYING
    9: 460,   # ALARM
    10: 484,  # THUNDER
    11: 497,  # WIND
    12: 488,  # RAIN
    13: 38,   # FOOTSTEPS
    14: 499,  # SILENCE
}

YAMNET_THRESHOLD = 0.5
YAMNET_SAMPLE_RATE = 16000


class YamnetState(Enum):
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"


class YamnetRunner:
    """YAMNet 音频分类器。

    从 RTMP audio 流拉 PCM，每 0.96s 窗口推理一次，
    输出 521 类 AudioSet scores → 映射为 SoundType → EventBus SOUND。
    """

    def __init__(self, view_id: int, audio_id: int, audio_name: str,
                 threshold: float = YAMNET_THRESHOLD) -> None:
        self._view_id = view_id
        self._audio_id = audio_id
        self._audio_name = audio_name
        self._threshold = threshold
        self._state = YamnetState.IDLE
        self._proc: asyncio.subprocess.Process | None = None
        self._model = None
        self._task: asyncio.Task | None = None
        self._retry_delay = 1.0
        self._max_retry_delay = 60.0

    @property
    def state(self) -> YamnetState:
        return self._state

    async def _load_model(self):
        """加载 YAMNet 模型（tensorflow-hub 优先，首次自动缓存）。"""
        if self._model is not None:
            return
        try:
            import tensorflow_hub as hub
            self._model = hub.load("https://tfhub.dev/google/yamnet/1")
            logger.info("YAMNet TF model loaded for view %d", self._view_id)
        except Exception:
            logger.info("tensorflow_hub load failed, trying torchaudio fallback")
            try:
                from torchaudio.prototype.models import YAMNET
                self._model = YAMNET.get_model()
                self._model.eval()
                logger.info("YAMNet torch model loaded for view %d", self._view_id)
            except ImportError:
                raise RuntimeError(
                    "YAMNet: neither tensorflow_hub nor torchaudio available"
                )

    async def _start_ffmpeg(self) -> asyncio.subprocess.Process:
        cmd = [
            "ffmpeg",
            "-i", build_pull_url(self._audio_name, "audio", self._audio_id),
            "-f", "f32le", "-ac", "1", "-ar", str(YAMNET_SAMPLE_RATE),
            "-loglevel", "error",
            "pipe:1",
        ]
        return await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )

    async def run(self) -> None:
        """主循环：拉流 → 累积样本 → 推理 → 发布事件。断流重连（指数退避 1s→60s）。"""
        self._state = YamnetState.ACTIVE
        self._task = asyncio.current_task()
        await self._load_model()

        while self._state == YamnetState.ACTIVE:
            try:
                self._proc = await self._start_ffmpeg()
                await self._inference_loop()
            except Exception:
                logger.exception("YAMNet error view=%d, retry %.1fs", self._view_id, self._retry_delay)
                self._state = YamnetState.ERROR
                await self._cleanup_proc()
                await asyncio.sleep(self._retry_delay)
                self._retry_delay = min(self._retry_delay * 2, self._max_retry_delay)
                self._state = YamnetState.ACTIVE
            else:
                self._retry_delay = 1.0

    async def _inference_loop(self) -> None:
        samples_per_window = YAMNET_SAMPLE_RATE
        buffer = bytearray()

        while self._state == YamnetState.ACTIVE and self._proc is not None:
            chunk = await self._proc.stdout.read(samples_per_window * 4)
            if not chunk:
                logger.warning("YAMNet audio stream ended view=%d", self._view_id)
                break
            buffer.extend(chunk)
            while len(buffer) >= samples_per_window * 4:
                window = buffer[:samples_per_window * 4]
                buffer = buffer[samples_per_window * 4:]
                waveform = np.frombuffer(window, dtype=np.float32)
                await self._classify(waveform)

    async def _classify(self, waveform) -> None:
        if self._model is None:
            return
        try:
            scores, _, _ = self._model(waveform)
            scores_np = scores.numpy()[0]
        except Exception:
            import torch
            with torch.no_grad():
                batch = torch.from_numpy(waveform).unsqueeze(0)
                result = self._model(batch)
                scores_np = result[0].numpy() if isinstance(result, tuple) else result.numpy()

        try:
            from src.service.vision_module.vision_event_bus import event_bus, SOUND
        except ImportError:
            return  # EventBus unavailable (e.g. cv2 not installed)
        for sound_type_val, class_id in SOUND_TYPE_MAP.items():
            if class_id < len(scores_np) and scores_np[class_id] > self._threshold:
                await event_bus.publish(SOUND, {
                    "view_id": self._view_id,
                    "sound_type": sound_type_val,
                    "score": float(scores_np[class_id]),
                })

    async def stop(self) -> None:
        self._state = YamnetState.IDLE
        await self._cleanup_proc()
        if self._task is not None:
            self._task.cancel()

    async def _cleanup_proc(self) -> None:
        if self._proc is not None:
            try:
                self._proc.kill()
                await self._proc.wait()
            except Exception:
                pass
            self._proc = None
