#!/bin/bash
# 安装 systemd 服务
set -euo pipefail

SERVICE_NAME=baobaoji
SERVICE_SRC=/home/ubuntu/accounting-miniprogram/deploy/baobaoji.service
SERVICE_DST=/etc/systemd/system/${SERVICE_NAME}.service

# 确保日志目录存在
mkdir -p /home/ubuntu/accounting-miniprogram/backend/logs

echo "安装 systemd 服务..."
sudo cp "$SERVICE_SRC" "$SERVICE_DST"
sudo systemctl daemon-reload

echo "停止当前手动启动的进程..."
CURRENT_PID=$(pgrep -f "python3 main.py" | head -1 || true)
if [ -n "$CURRENT_PID" ]; then
    kill "$CURRENT_PID" 2>/dev/null || true
    sleep 2
fi

echo "启动 systemd 服务..."
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
sleep 2

echo "检查状态..."
sudo systemctl status "$SERVICE_NAME" --no-pager

echo "✅ 安装完成"
