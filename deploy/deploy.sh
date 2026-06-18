#!/bin/bash
# 抱布记 自动部署脚本
# 在服务器上执行：git pull → 安装依赖 → 重启服务
set -euo pipefail

cd /home/ubuntu/accounting-miniprogram

echo "[1/4] 拉取最新代码..."
git pull origin main

echo "[2/4] 安装依赖..."
cd backend
.venv/bin/pip install -r requirements.txt -q

echo "[3/4] 运行测试..."
.venv/bin/python -m pytest tests/ -q || {
    echo "⚠️  测试未通过，跳过部署"
    exit 1
}

echo "[4/4] 重启服务..."
sudo systemctl restart baobaoji

echo "✅ 部署完成"
