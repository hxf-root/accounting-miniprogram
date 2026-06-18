#!/usr/bin/env bash
# ====================================================================
# 抱布记 (Baobaoji) — 一键启动脚本
#
# 功能：
#   1. 检查 Python venv 是否存在，不存在则创建
#   2. 安装 / 更新依赖
#   3. 用 uvicorn 直接启动后端
#   4. 打印清晰的启动信息（含 URL）
#
# 用法：
#   ./start.sh              # 前台启动
#   ./start.sh --daemon     # 后台启动（nohup）
# ====================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"
REQUIREMENTS="$BACKEND_DIR/requirements.txt"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8089}"

# ---- 颜色 ----
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---- 1. 检查 Python ----
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    error "未找到 Python，请先安装 Python 3.9+"
    exit 1
fi
info "使用 Python: $( "$PYTHON" --version 2>&1 )"

# ---- 2. 检查 / 创建虚拟环境 ----
if [ ! -d "$VENV_DIR" ]; then
    info "虚拟环境不存在，正在创建..."
    "$PYTHON" -m venv "$VENV_DIR"
    info "虚拟环境已创建于: $VENV_DIR"
else
    info "虚拟环境已存在，跳过创建"
fi

# ---- 3. 激活虚拟环境 & 安装依赖 ----
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
info "已激活虚拟环境: $(which python)"

if [ -f "$REQUIREMENTS" ]; then
    info "正在安装 / 更新依赖..."
    pip install --quiet --upgrade pip -r "$REQUIREMENTS"
    info "依赖安装完成"
else
    warn "未找到 requirements.txt: $REQUIREMENTS"
fi

# ---- 4. 切换到后端目录 ----
cd "$BACKEND_DIR"

# ---- 5. 启动服务 ----
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  抱布记 API 服务${NC}"
echo -e "${CYAN}============================================${NC}"
echo -e "  地址:   ${GREEN}http://$HOST:$PORT${NC}"
echo -e "  文档:   ${GREEN}http://$HOST:$PORT/docs${NC}"
echo -e "  健康:   ${GREEN}http://$HOST:$PORT/api/health${NC}"
echo -e "  目录:   $BACKEND_DIR"
echo -e "  退出:   Ctrl+C"
echo -e "${CYAN}============================================${NC}"
echo ""

if [ "${1:-}" = "--daemon" ]; then
    # 后台启动
    LOG_FILE="$BACKEND_DIR/logs/startup.log"
    mkdir -p "$(dirname "$LOG_FILE")"
    DAEMON_FLAGS=""
    info "以 daemon 模式启动，日志: $LOG_FILE"
    nohup uvicorn main:app --host "$HOST" --port "$PORT" "$DAEMON_FLAGS" > "$LOG_FILE" 2>&1 &
    PID=$!
    echo "$PID" > "$BACKEND_DIR/.server.pid"
    echo -e "${GREEN}服务已后台启动 (PID: $PID)${NC}"
    echo -e "${GREEN}停止: kill \$(cat $BACKEND_DIR/.server.pid)${NC}"
else
    # 前台启动（默认）
    exec uvicorn main:app --host "$HOST" --port "$PORT"
fi
