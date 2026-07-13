"""YAMNet 音频分类运行器 —— FFmpeg 拉 PCM → 模型推理 → EventBus SOUND。

AudioSet 521 类 → SoundType 15 类映射（ai-model-capability spec）。
"""

from __future__ import annotations

import asyncio
import csv
import logging
from enum import Enum
from pathlib import Path

import numpy as np

from src.network.rtmp.puller import build_pull_url

logger = logging.getLogger(__name__)

# ── AudioSet 521 类名缓存 ──────────────────────────
_ALL_CLASS_NAMES: dict[int, str] = {}


def _load_class_names() -> dict[int, str]:
    """从 YAMNet 模型的 class_map CSV 加载全部 521 类名称。"""
    global _ALL_CLASS_NAMES
    if _ALL_CLASS_NAMES:
        return _ALL_CLASS_NAMES
    try:
        import tensorflow_hub as hub
        model = hub.load("https://tfhub.dev/google/yamnet/1")
        csv_path = model.class_map_path().numpy().decode()
    except Exception:
        logger.warning("YAMNet class_map_path failed, trying cached CSV")
        csv_path = None
        for p in Path.home().glob("AppData/Local/Temp/tfhub_modules/*/assets/yamnet_class_map.csv"):
            csv_path = str(p)
            break
    if csv_path:
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    _ALL_CLASS_NAMES[int(row["index"])] = row["display_name"]
            logger.info("YAMNet class names loaded: %d classes", len(_ALL_CLASS_NAMES))
        except Exception:
            logger.exception("Failed to load YAMNet class map CSV")
    return _ALL_CLASS_NAMES


# ── AudioSet class_id → SoundType 映射 ─────────────────
# 2026-07-12 修正：原映射全部指向错误 AudioSet class_id
# （如 SCREAM→class 2 实际是 Conversation，GUNSHOT→430 实际是 Boom）。
# 对照 yamnet_class_map.csv 逐条校正。
SOUND_TYPE_MAP: dict[int, int] = {
    0: 421,   # GUNSHOT       → "Gunshot, gunfire"
    1: 11,    # SCREAM        → "Screaming"
    2: 390,   # SIREN         → "Siren"
    3: 420,   # EXPLOSION     → "Explosion"
    4: 464,   # GLASS_BREAKING → "Breaking"
    5: 70,    # DOG_BARKING   → "Bark"
    6: 302,   # CAR_HORN      → "Vehicle horn, car horn, honking"
    7: 320,   # ENGINE        → "Motorcycle" (closest engine class)
    8: 20,    # BABY_CRYING   → "Baby cry, infant cry"
    9: 394,   # ALARM         → "Fire alarm"
    10: 281,  # THUNDER       → "Thunder"
    11: 277,  # WIND          → "Wind"
    12: 283,  # RAIN          → "Rain"
    13: 48,   # FOOTSTEPS     → "Walk, footsteps"
    14: 494,  # SILENCE       → "Silence"
}

YAMNET_THRESHOLD = 0.5
DANGER_THRESHOLD = 0.3
YAMNET_SAMPLE_RATE = 16000

# ── 危险声音检测（全 521 类）─────────────────────
# 独立危险：任一类 score > DANGER_THRESHOLD 直接触发
_DANGER_STANDALONE: dict[int, str] = {
    11: "Screaming", 19: "Crying", 20: "Baby_cry", 22: "Wail",
    317: "Police_siren", 318: "Ambulance", 319: "Fire_truck",
    382: "Alarm", 391: "Civil_siren", 393: "Smoke_alarm", 394: "Fire_alarm",
    420: "Explosion", 421: "Gunshot", 422: "Machine_gun", 424: "Artillery",
    426: "Fireworks", 427: "Firecracker",
}

# 组合判定：来自不同组的信号同时出现 → 复合危险
_GROUP_SHOUT    = {6: "Shout", 7: "Bellow", 9: "Yell", 10: "Kids_shout"}
_GROUP_CROWD    = {61: "Cheering", 64: "Crowd", 65: "Hubbub"}
_GROUP_IMPACT   = {454: "Thump", 461: "Slap", 462: "Whack", 463: "Smash",
                   464: "Breaking", 437: "Shatter"}

# (组A, 组B, 标签) — 两组同时有 > DANGER_THRESHOLD 的类 → 触发
_COMBOS: list[tuple[dict[int, str], dict[int, str], str]] = [
    (_GROUP_SHOUT, _GROUP_CROWD, "Fighting"),
    (_GROUP_SHOUT, _GROUP_IMPACT, "Violence"),
    (_GROUP_CROWD, _GROUP_IMPACT, "Riot"),
]


def _sound_name(sound_type_val: int) -> str:
    """YAMNetSoundType 整数值 → 可读名称。"""
    try:
        from src.constants import YAMNetSoundType
        return YAMNetSoundType(sound_type_val).name.capitalize()
    except (ValueError, ImportError):
        return f"Sound-{sound_type_val}"


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
        url = build_pull_url(self._audio_name, "audio", self._audio_id)
        logger.info("YAMNet ffmpeg connecting view=%d url=%s", self._view_id, url)
        cmd = [
            "ffmpeg",
            "-i", url,
            "-f", "f32le", "-ac", "1", "-ar", str(YAMNET_SAMPLE_RATE),
            "-loglevel", "error",
            "pipe:1",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        logger.info("YAMNet ffmpeg connected view=%d pid=%d", self._view_id, proc.pid)
        return proc

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
        window_count = 0
        chunk_count = 0
        last_heartbeat = 0.0
        first_chunk = True
        import time as _time

        logger.info("YAMNet inference loop started view=%d", self._view_id)
        while self._state == YamnetState.ACTIVE and self._proc is not None:
            # 诊断：检查 ffmpeg 是否已退出
            if self._proc.returncode is not None:
                stderr_data = await self._proc.stderr.read() if self._proc.stderr else b""
                logger.error(
                    "YAMNet ffmpeg exited view=%d rc=%d stderr=%s",
                    self._view_id, self._proc.returncode,
                    stderr_data[-200:].decode(errors="replace") if stderr_data else "",
                )
                break

            logger.debug("YAMNet read waiting view=%d chunk=%d ...", self._view_id, chunk_count)
            try:
                chunk = await asyncio.wait_for(
                    self._proc.stdout.read(samples_per_window * 4),
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "YAMNet read timeout view=%d chunk=%d — no audio data in 15s, restarting ffmpeg",
                    self._view_id, chunk_count,
                )
                break
            chunk_count += 1
            logger.debug("YAMNet read done view=%d chunk=%d len=%d",
                         self._view_id, chunk_count, len(chunk) if chunk else 0)

            if first_chunk:
                logger.info("YAMNet first chunk received view=%d len=%d", self._view_id, len(chunk) if chunk else 0)
                first_chunk = False

            if not chunk:
                logger.warning("YAMNet audio stream ended view=%d after %d chunks",
                              self._view_id, chunk_count)
                break
            buffer.extend(chunk)
            while len(buffer) >= samples_per_window * 4:
                window = buffer[:samples_per_window * 4]
                buffer = buffer[samples_per_window * 4:]
                waveform = np.frombuffer(window, dtype=np.float32)
                await self._classify(waveform)
                window_count += 1
                now = _time.time()
                # 声波调试：每窗口（~1s）输出 top-3 + RMS
                if now - last_heartbeat >= 0.0:
                    rms = float(np.sqrt(np.mean(waveform.astype(float) ** 2)))
                    self._log_top_scores(waveform, window_count, rms)
                    last_heartbeat = now

    async def _classify(self, waveform) -> bool:
        """全 521 类推理 → 独立危险 + 组合判定 → top-2 左下角显示。

        阈值 DANGER_THRESHOLD=0.3。显示前 2 个危险标签。
        超过 YAMNET_THRESHOLD 的声音发布 EventBus 供 AlertEngine。
        """
        if self._model is None:
            return False
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
            from src.service.vision_module.vision_annotation import set_sound_label
        except ImportError:
            return False

        dangers: list[tuple[float, str]] = []

        # 1. 独立危险
        for aid, label in _DANGER_STANDALONE.items():
            if aid < len(scores_np):
                s = float(scores_np[aid])
                if s > DANGER_THRESHOLD:
                    dangers.append((s, label))

        # 2. 组合判定
        for group_a, group_b, combo_label in _COMBOS:
            a_hit = any(
                aid < len(scores_np) and float(scores_np[aid]) > DANGER_THRESHOLD
                for aid in group_a
            )
            b_hit = any(
                aid < len(scores_np) and float(scores_np[aid]) > DANGER_THRESHOLD
                for aid in group_b
            )
            if a_hit and b_hit:
                # 取两组最高分的均值作为组合得分
                a_max = max(float(scores_np[aid]) for aid in group_a if aid < len(scores_np))
                b_max = max(float(scores_np[aid]) for aid in group_b if aid < len(scores_np))
                dangers.append(((a_max + b_max) / 2, combo_label))

        # 3. 按分数降序，取 top-2
        dangers.sort(reverse=True)
        if dangers:
            label_parts = [f"{name} ({score:.2f})" for score, name in dangers[:2]]
            set_sound_label(" | ".join(label_parts))
        else:
            set_sound_label(None)  # 无危险时清除

        # 4. EventBus 发布 — 独立危险 + 组合标签（供 AlertEngine 跨模态融合）
        had_alert = False
        for score, name in dangers:
            had_alert = True
            await event_bus.publish(SOUND, {
                "type": SOUND,
                "view_id": self._view_id,
                "sound_name": name,       # "Screaming" / "Fighting" / "Riot" ...
                "score": score,
            })
        # 同时发布旧 SOUND_TYPE_MAP 格式（兼容现有 AlertEngine 规则）
        for sound_type_val, class_id in SOUND_TYPE_MAP.items():
            if class_id < len(scores_np) and scores_np[class_id] > self._threshold:
                had_alert = True
                await event_bus.publish(SOUND, {
                    "type": SOUND,
                    "view_id": self._view_id,
                    "sound_type_ids": [sound_type_val],
                    "score": float(scores_np[class_id]),
                })
        return had_alert

    def _log_top_scores(self, waveform, window_count: int, rms: float = 0.0) -> None:
        """声波调试：输出 RMS + 全 521 类的 top-3 分数。"""
        if self._model is None:
            return
        try:
            scores, _, _ = self._model(waveform)
            scores_np = scores.numpy()[0]
        except Exception:
            return
        class_names = _load_class_names()
        # 按分数取 top-3（全 521 类）
        indexed = [(float(scores_np[i]), i) for i in range(min(len(scores_np), 521))]
        indexed.sort(reverse=True)
        top3 = " ".join(
            f"{class_names.get(i, f'#{i}')}={s:.2f}"
            for s, i in indexed[:3]
        )
        logger.info(
            "[YAMNet] windows=%d rms=%.4f top3=%s",
            window_count, rms, top3,
        )

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
