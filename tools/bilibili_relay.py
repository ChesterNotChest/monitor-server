#!/usr/bin/env python3
"""B站直播 → SRS RTMP 中继 watchdog。

用法:
    python tools/bilibili_relay.py <房间号> [--name <流名>] [--srs rtmp://127.0.0.1:1935/live/]
    python tools/bilibili_relay.py 23608828
    python tools/bilibili_relay.py 23120489 --name highway_test

特性:
    - 定时刷新 B站 FLV URL（API 鉴权参数有时效）
    - ffmpeg 断线自动重启
    - 静默运行，Ctrl+C 退出
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [relay] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bilibili_relay")

BILIBILI_API = "https://api.live.bilibili.com/room/v1/Room/playUrl"
HEADERS = {
    "Referer": "https://live.bilibili.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
# B站 URL 典型有效期约 2 小时，提前 30 分钟刷新
URL_REFRESH_SECONDS = 90 * 60  # 90 minutes
# ffmpeg 断线检测间隔
HEALTH_CHECK_SECONDS = 10


def fetch_flv_url(room_id: int) -> str | None:
    """从 B站 API 获取 FLV 流地址。"""
    params = {"cid": room_id, "platform": "web", "qn": 10000}
    try:
        r = requests.get(BILIBILI_API, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        log.error("获取流地址失败 (room=%d): %s", room_id, exc)
        return None

    if data.get("code") != 0:
        log.error("B站 API 返回错误 (room=%d): code=%s msg=%s",
                  room_id, data.get("code"), data.get("message", ""))
        return None

    durl = data.get("data", {}).get("durl", [])
    if not durl:
        log.error("B站 API 返回空 durl (room=%d)", room_id)
        return None

    return durl[0]["url"]


def start_ffmpeg(flv_url: str, rtmp_push_url: str) -> subprocess.Popen | None:
    """启动 ffmpeg 子进程：拉 B站 FLV → 推 SRS RTMP。"""
    cmd = [
        "ffmpeg",
        "-nostdin", "-loglevel", "error",
        "-headers", f"Referer: {HEADERS['Referer']}\r\nUser-Agent: {HEADERS['User-Agent']}",
        "-i", flv_url,
        "-c", "copy",
        "-f", "flv",
        rtmp_push_url,
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log.info("ffmpeg 已启动 (PID=%d) → %s", proc.pid, rtmp_push_url)
        return proc
    except FileNotFoundError:
        log.error("ffmpeg 未找到，请确保 ffmpeg 在 PATH 中")
        return None
    except Exception as exc:
        log.error("启动 ffmpeg 失败: %s", exc)
        return None


def is_alive(proc: subprocess.Popen) -> bool:
    """检查 ffmpeg 子进程是否仍在运行。"""
    return proc.poll() is None


def run(room_id: int, stream_name: str, srs_base: str):
    """主循环：拉流 → 推流 → 监控 → 故障恢复。"""
    rtmp_push_url = f"{srs_base.rstrip('/')}/{stream_name}"
    proc: subprocess.Popen | None = None
    flv_url: str | None = None
    last_url_fetch: float = 0

    log.info("B站房间 %d → %s", room_id, rtmp_push_url)
    log.info("URL 刷新间隔: %d 分钟 | 健康检查: %d 秒 | Ctrl+C 退出",
             URL_REFRESH_SECONDS // 60, HEALTH_CHECK_SECONDS)

    try:
        while True:
            # 1. 刷新 URL
            now = time.time()
            if flv_url is None or (now - last_url_fetch) > URL_REFRESH_SECONDS:
                new_url = fetch_flv_url(room_id)
                if new_url:
                    flv_url = new_url
                    last_url_fetch = now
                    log.info("FLV URL 已更新")
                else:
                    log.warning("URL 刷新失败，续用旧 URL")

            # 2. 进程管控
            if proc is None or not is_alive(proc):
                if proc is not None:
                    rc = proc.poll()
                    log.warning("ffmpeg 已退出 (exit=%d)，重启中...", rc)
                    proc = None

                if flv_url:
                    proc = start_ffmpeg(flv_url, rtmp_push_url)
                else:
                    log.warning("无可用 FLV URL，等待下次刷新...")

            # 3. 等待下一轮检查
            time.sleep(HEALTH_CHECK_SECONDS)

    except KeyboardInterrupt:
        log.info("收到中断信号，正在退出...")
    finally:
        if proc and is_alive(proc):
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            log.info("ffmpeg 已终止")


def main():
    parser = argparse.ArgumentParser(description="B站直播 → SRS RTMP 中继")
    parser.add_argument("room_id", type=int, help="B站直播间房间号")
    parser.add_argument("--name", "-n", default=None,
                        help="RTMP 流名 (默认: bilibili_{房间号})")
    parser.add_argument("--srs", default="rtmp://127.0.0.1:1935/live/",
                        help="SRS RTMP 推流基地址 (默认: rtmp://127.0.0.1:1935/live/)")
    args = parser.parse_args()

    stream_name = args.name or f"bilibili_{args.room_id}"
    run(args.room_id, stream_name, args.srs)


if __name__ == "__main__":
    main()
