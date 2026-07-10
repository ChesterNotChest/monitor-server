"""E2E 音频管线: Node RTMP stream -> YAMNet -> terminal display.

Usage: python demo_e2e_audio.py
Requires: Node running with RTMP_DEBUG=true
"""

import subprocess
import sys
import time

import numpy as np

SAMPLE_RATE = 16000
DURATION = 2
SOUND_NAMES = {0:"GUNSHOT",1:"SCREAM",2:"SIREN",3:"EXPLOSION",4:"GLASS_BREAKING",5:"DOG_BARKING",
               6:"CAR_HORN",7:"ENGINE",8:"BABY_CRYING",9:"ALARM",10:"THUNDER",
               11:"WIND",12:"RAIN",13:"FOOTSTEPS",14:"SILENCE"}
SOUND_MAP = {0:430,1:2,2:417,3:457,4:441,5:74,6:424,7:491,8:25,9:460,10:484,11:497,12:488,13:38,14:499}

# AudioSet common class_id → human readable
AS_NAMES = {0:"Speech",1:"Male speech",2:"Female speech/scream-like",3:"Music/Singing",
            4:"Child speech",5:"Inside large room",7:"Chuckle",8:"Giggle",
            12:"Chatter",13:"Knock",19:"Clang",25:"Baby cry/infant cry",
            36:"Snort",38:"Footsteps",42:"Bass drum",74:"Bark",
            132:"Clatter",133:"Shatter",156:"Squeak",249:"Keys jangling",
            372:"Door",417:"Siren",424:"Car horn",430:"Gunshot/artillery fire",
            441:"Glass break",457:"Explosion",460:"Alarm/emergency siren",
            484:"Thunder",485:"Water",488:"Rain",491:"Engine",
            494:"Silence",497:"Wind",498:"Environmental noise",499:"Background noise",
            500:"Ambient noise",501:"Humming",504:"Idling engine"}

def _find_ffmpeg():
    import os, shutil
    p = shutil.which("ffmpeg")
    if p: return p
    for base in [r"C:\ffmpeg\bin", r"C:\Program Files\ffmpeg\bin"]:
        exe = os.path.join(base, "ffmpeg.exe")
        if os.path.isfile(exe): return exe
    from pathlib import Path
    winget = Path(os.getenv("LOCALAPPDATA",""))/"Microsoft"/"WinGet"/"Packages"
    if winget.exists():
        for exe in winget.rglob("ffmpeg.exe"): return str(exe)
    return "ffmpeg"

FFMPEG = _find_ffmpeg()

# Use puller.py format: same as Node push
from src.network.rtmp.puller import build_pull_url
RTMP_URL = build_pull_url("麦克风阵列 (Realtek(R) Audio)", "audio", 0)

print("Loading YAMNet...")
import tensorflow_hub as hub
model = hub.load("https://tfhub.dev/google/yamnet/1")
print("RTMP URL:", RTMP_URL)
print("Listening (Ctrl+C to stop)...\n")

# 长连接 FFmpeg —— -re 按原生帧率读取, reconnect 选项处理断连
n_per_window = SAMPLE_RATE * DURATION
cmd = [FFMPEG, "-re", "-rw_timeout", "5000000",
       "-i", RTMP_URL,
       "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE),
       "-loglevel", "error", "pipe:1"]
ffmpeg_proc = None
buf = bytearray()

def _start_ffmpeg():
    global ffmpeg_proc
    if ffmpeg_proc:
        try: ffmpeg_proc.terminate()
        except: pass
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

ffmpeg_proc = _start_ffmpeg()

try:
    while True:
        chunk = ffmpeg_proc.stdout.read(n_per_window * 4)
        if not chunk:
            print("FFmpeg disconnected, reconnecting...")
            ffmpeg_proc = _start_ffmpeg()
            buf = bytearray()
            time.sleep(0.5)
            continue
        buf.extend(chunk)
        while len(buf) >= n_per_window * 4:
            window = buf[:n_per_window * 4]
            buf = buf[n_per_window * 4:]
            wf = np.frombuffer(window, dtype=np.float32)
            peak = abs(wf).max()
            rms = np.sqrt(np.mean(wf.astype(np.float64) ** 2))
            scores, _, _ = model(wf.astype(np.float32))
            snp = scores.numpy()[0]
            top5 = np.argsort(snp)[-5:][::-1]
            bar_len = min(30, int(rms * 300))
            bar = "#" * bar_len + " " * (30 - bar_len)
            print(f"[{time.strftime('%H:%M:%S')}] peak={peak:.4f}|rms={rms:.4f} [{bar}] ", end="")
            hits = [(sv, snp[cid]) for sv, cid in SOUND_MAP.items() if cid < 521 and snp[cid] > 0.3]
            if hits:
                for sv, s in hits:
                    print(f"\033[91m>>> {SOUND_NAMES[sv]:16s} {s:.3f}\033[0m | ", end="")
                print()
            elif peak < 0.001:
                print("\033[93mSILENCE - mic may be muted or disconnected\033[0m")
            else:
                n1 = AS_NAMES.get(top5[0], f"cls{top5[0]}")
                n2 = AS_NAMES.get(top5[1], f"cls{top5[1]}")
                print(f"top: {n1}={snp[top5[0]]:.2f}  {n2}={snp[top5[1]]:.2f}")
except KeyboardInterrupt:
    ffmpeg_proc.terminate()
    print("\nStopped.")
