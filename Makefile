# ====================================================================
# 抱布记 (Baobaoji) — Makefile
#
# 项目管理入口，聚合常见开发 / 运维操作。
#
# 用法：
#   make start    启动后端服务（前台）
#   make start-d  启动后端服务（后台 daemon）
#   make test     运行测试
#   make install  安装依赖
#   make deploy   暂停的旧部署入口
#   make backup   备份 SQLite 数据库
#   make clean    清理 __pycache__ / .pyc / .pytest_cache
# ====================================================================

# ---- 变量 ----
SHELL           := /bin/bash
PROJECT_ROOT    := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
BACKEND_DIR     := $(PROJECT_ROOT)/backend
VENV_DIR        := $(BACKEND_DIR)/.venv
VENV_PYTHON     := $(VENV_DIR)/bin/python
VENV_PIP        := $(VENV_DIR)/bin/pip
VENV_UVICORN    := $(VENV_DIR)/bin/uvicorn
VENV_PYTEST     := $(VENV_DIR)/bin/pytest

HOST            ?= 0.0.0.0
PORT            ?= 8089
DB_FILE         ?= $(BACKEND_DIR)/baobaoji.db
BACKUP_DIR      ?= $(PROJECT_ROOT)/backups

# ---- 目标 ----
.PHONY: start start-d test install deploy backup clean

# ---- 默认目标 ----
.DEFAULT_GOAL := start

# ====================================================================
# start  — 前台启动后端
# ====================================================================
start: $(VENV_DIR)
	@echo "============================================"
	@echo "  抱布记 API 服务"
	@echo "============================================"
	@echo "  地址: http://$(HOST):$(PORT)"
	@echo "  文档: http://$(HOST):$(PORT)/docs"
	@echo "  健康: http://$(HOST):$(PORT)/api/health"
	@echo "============================================"
	cd $(BACKEND_DIR) && $(VENV_UVICORN) main:app --host $(HOST) --port $(PORT)

# ====================================================================
# start-d — 后台启动（daemon）
# ====================================================================
start-d: $(VENV_DIR)
	@mkdir -p $(BACKEND_DIR)/logs
	@cd $(BACKEND_DIR) && nohup $(VENV_UVICORN) main:app --host $(HOST) --port $(PORT) \
		> $(BACKEND_DIR)/logs/startup.log 2>&1 & \
		echo $$! > $(BACKEND_DIR)/.server.pid
	@echo "[INFO] 服务已后台启动 (PID: $$(cat $(BACKEND_DIR)/.server.pid))"
	@echo "[INFO] 查看日志: tail -f $(BACKEND_DIR)/logs/startup.log"
	@echo "[INFO] 停止服务: kill $$(cat $(BACKEND_DIR)/.server.pid)"

# ====================================================================
# install — 安装 / 更新依赖
# ====================================================================
install: $(VENV_DIR)
	@$(VENV_PIP) install --quiet --upgrade pip
	@$(VENV_PIP) install --quiet -r $(BACKEND_DIR)/requirements.txt
	@echo "[INFO] 依赖安装完成"

# ====================================================================
# test — 运行测试（带覆盖率建议）
# ====================================================================
test: $(VENV_DIR)
	@cd $(BACKEND_DIR) && $(VENV_PYTEST) -v --tb=short
	@echo "[INFO] 测试完成"

# ====================================================================
# deploy — 旧入口暂停，等待完整部署及回退流程
# ====================================================================
deploy:
	@echo "部署已暂停：需先完成备份、迁移及回退方案。" >&2
	@exit 1

# ====================================================================
# backup — 备份 SQLite 数据库
# ====================================================================
backup:
	@python3 "$(PROJECT_ROOT)/deploy/backup_sqlite.py" --database "$(DB_FILE)" --backup-dir "$(BACKUP_DIR)"

# ====================================================================
# clean — 清理缓存文件
# ====================================================================
clean:
	@echo "[INFO] 清理 __pycache__ 目录..."
	@find $(PROJECT_ROOT) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	@echo "[INFO] 清理 .pyc 文件..."
	@find $(PROJECT_ROOT) -type f -name "*.pyc" -delete 2>/dev/null; true
	@echo "[INFO] 清理 .pyo 文件..."
	@find $(PROJECT_ROOT) -type f -name "*.pyo" -delete 2>/dev/null; true
	@echo "[INFO] 清理 .pytest_cache..."
	@rm -rf $(BACKEND_DIR)/.pytest_cache
	@echo "[INFO] 清理完成"

# ====================================================================
# 内部：确保虚拟环境存在
# ====================================================================
$(VENV_DIR):
	@echo "[INFO] 虚拟环境不存在，正在创建..."
	@python3 -m venv $(VENV_DIR)
	@echo "[INFO] 虚拟环境已创建于: $(VENV_DIR)"
