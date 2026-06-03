# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

将 WizNote（为知笔记）迁移到 Obsidian 的工具集。采用**开源 CLI + 商业桌面应用**双轨架构：

- `tools/` — 开源命令行工具（MIT），供所有用户免费使用
- `app/` — 商业桌面应用 "Shadow Shift"，Git submodule 指向私有仓库 `git@github.com:WardLu/shadow-shift.git`

**注意**: `app/` 需要 submodule 权限才能访问。开源用户看到空目录是正常的。

## 常用命令

### 开源工具

```bash
# 安装依赖
pip3 install -r requirements.txt

# 核心工作流（三步迁移）
python3 tools/wiznote_downloader.py              # 第1步：下载笔记
python3 tools/obsidian_formatter.py               # 第2步：格式化为 Obsidian
# 第3步：用 Obsidian 打开 wiznote_download/ 目录

# 工具帮助
python3 tools/wiznote_downloader.py --help
python3 tools/obsidian_formatter.py --help
```

### 商业应用（需要 submodule 权限）

```bash
# 安装依赖
pip install -r app/requirements.txt

# 运行 GUI
./app/run_gui.sh
python3 app/src/main.py

# 运行 License 服务器
python3 app/app.py

# 测试
./app/scripts/run_tests.sh                    # 全部测试
./app/scripts/run_tests.sh --unit             # 仅单元测试
./app/scripts/run_tests.sh --integration      # 仅集成测试
./app/scripts/run_tests.sh --e2e              # 仅 E2E 测试
./app/scripts/run_tests.sh --coverage         # 带覆盖率
python3 -m pytest app/tests/ -v               # 直接 pytest 调用

# 构建打包（PyInstaller）
./app/build.sh                                # 自动检测平台
./app/build-release.sh                        # Release 构建
```

## 架构要点

### 开源工具 (`tools/`)

核心脚本，无构建系统，直接运行：

- **`wiznote_downloader.py`** (62KB) — 通过 WizNote HTTP/WebSocket API 下载笔记，HTML→Markdown 转换，处理图片/附件
- **`obsidian_formatter.py`** (30KB) — Obsidian 格式化（语法检查、格式修复、链接转换、图片修复、报告生成）
- **`smart_migrate_to_obsidian.py`** — 智能迁移，支持 WikiLink
- **`config_helper.py`** — 共享配置模块

依赖：`requests`、`markdownify`、`websocket-client`

### 商业应用 (`app/`)

**客户端** (`app/src/`):
- `main.py` → 入口：依赖检查、单实例锁、启动 GUI
- `config.py` → 集中配置（API URL、授权模式、版本号）
- `gui/app.py` → 主窗口 (70KB，customtkinter)
- `license/` → JWT 授权客户端（设备绑定、在线激活、离线缓存）
- `core/` → 迁移逻辑、冲突检测、线程管理

**服务端** (`app/server/`):
- `app.py` → Flask API（`/api/activate`, `/api/verify`, `/api/check`, `/api/increment`）
- `lib/db_supabase.py` → Supabase 数据库集成
- `lib/secure_storage.py` → 加密本地存储
- `lib/offline_cache.py` → 离线授权缓存

**部署**: Vercel (serverless) + Render (Flask)，详见 `app/vercel.json` 和 `app/render.yaml`

### 测试结构

三层测试（`app/tests/`）：
- `unit/` — 35 个文件，快速隔离测试
- `integration/` — 11 个文件，模块交互测试
- `e2e/` — 5 个文件，完整流程测试

pytest 标记：`unit`、`integration`、`e2e`、`slow`

## 代码规范

- Python 3.6+，PEP 8，4 空格缩进
- 类名 `PascalCase`，函数/变量 `snake_case`，常量 `UPPER_SNAKE_CASE`
- Google 风格 docstring
- Commit 信息遵循 Conventional Commits：`feat:`、`fix:`、`docs:`、`refactor:`、`test:`、`chore:`

## 输出语言

使用中文（简体）进行思考和输出。代码变量名和注释使用英文，引用原文保留原语言。
