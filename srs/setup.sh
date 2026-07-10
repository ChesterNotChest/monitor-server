#!/bin/bash
# SRS 本地部署 — 下载并启动（Windows 用 Git Bash 或 WSL）
# 依赖本地已经在跑的 docker，或者直接拉 Windows 包
set -e

SRS_VERSION="5.0-r0"
SRS_URL="https://github.com/ossrs/srs/releases/download/v$SRS_VERSION/SRS-Windows-x86_64-$SRS_VERSION.zip"
SRS_BIN_DIR="./srs-bin"
SRS_CONFIG="srs/srs.conf"

if command -v docker &> /dev/null; then
    echo "[SRS] Starting via Docker ..."
    docker run -d --name srs \
      -p 1935:1935 -p 8080:8080 -p 1985:1985 -p 8000:8000/udp \
      -v "$(pwd)/$SRS_CONFIG:/usr/local/srs/conf/srs.conf" \
      ossrs/srs:5
    echo "[SRS] Docker container started (name=srs)"
    echo "[SRS] Stop: docker stop srs && docker rm srs"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    if [ ! -f "$SRS_BIN_DIR/srs.exe" ]; then
        echo "[SRS] Downloading Windows binary ..."
        mkdir -p "$SRS_BIN_DIR"
        curl -L -o srs-windows.zip "$SRS_URL"
        unzip -o srs-windows.zip -d "$SRS_BIN_DIR"
        rm srs-windows.zip
    fi
    echo "[SRS] Starting ..."
    "$SRS_BIN_DIR/srs.exe" -c "$SRS_CONFIG"
else
    echo "[SRS] No Docker found and not on Windows. Install SRS manually:"
    echo "  https://github.com/ossrs/srs#usage"
    exit 1
fi
