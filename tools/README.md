# Tools 目录

所有迁移工具和辅助脚本

## 📁 目录结构

```
tools/
├── wiznote_downloader.py       📥 在线下载工具
├── obsidian_formatter.py       🔧 主格式化工具（推荐使用）
├── sync_deletions.py           🗑️  同步删除工具
├── migrate_attachments.py      📎 附件迁移工具
├── link_attachments.py         🔗 附件链接工具
├── normalize_attachments.py    🧹 附件归一化工具
├── config_helper.py            ⚙️  配置模块
├── config.example.json         📝 配置模板
└── README.md                   📖 本文档
```

## 🚀 快速开始

### 前置要求

```bash
# 安装依赖（仅在线下载需要）
pip3 install -r requirements.txt
# 或手动安装: pip3 install requests markdownify websocket-client
```

### 方式一：在线下载（推荐新手）

```bash
# 1. 从 WizNote 云端下载笔记
python3 tools/wiznote_downloader.py
# 输入 WizNote 账号和密码

# 2. 优化格式
python3 tools/obsidian_formatter.py
# 输出到 wiznote_obsidian/，原始 wiznote_download/ 保持不变
```

### 方式二：离线处理（已有导出文件）

```bash
# 注意：离线处理不需要额外依赖

# 执行完整流程
python3 tools/obsidian_formatter.py

# 查看帮助
python3 tools/obsidian_formatter.py --help
```

### 使用配置文件

```bash
# 复制配置模板
cp config.example.json config.json

# 编辑配置
vim config.json

# 使用配置文件
python3 tools/obsidian_formatter.py --config config.json
```

## 🛠️ 工具说明

### 主要工具

#### 1. wiznote_downloader.py（在线下载工具）

**作用**：从 WizNote 云端下载笔记并转换为 Markdown

**使用场景**：还没有导出 WizNote 笔记

**功能**：
- 直接登录 WizNote 云端
- 递归扫描所有文件夹
- 自动转换 HTML → Markdown
- ✅ 下载笔记中的图片（使用增强版 API）
- ✅ 下载笔记中的附件（PDF、XMind 等）
- ✅ 支持协作笔记下载（通过 WebSocket 协议）

**输出目录**：`wiznote_download/`（原始下载）

**格式化输出**：`wiznote_obsidian/`（在 Obsidian 中打开这个）

**注意**：
- ✅ **图片和附件下载已支持**：使用增强版 API 端点
- ✅ **协作笔记已支持**：通过 ShareJS 协议自动获取
- ✅ **加密笔记检测已支持**：自动识别并提醒用户解密
- 💡 **图片位置**：保存在 `{笔记名}_files/` 目录
- 💡 **附件位置**：保存在同目录下的 `_files/` 文件夹
- 💡 **协作笔记**：自动检测并通过 WebSocket 获取内容，转换为 Markdown
- 💡 **加密笔记**：记录在报告中，提示用户先解密再下载
- 💡 **成功率**：实测 99.6%（447/449 个笔记）

**使用方法**：
```bash
# 使用默认参数（推荐新手）
python3 tools/wiznote_downloader.py
# 按提示输入 WizNote 账号和密码

# 极速模式（网络好，快速下载）
python3 tools/wiznote_downloader.py --workers 10 --timeout 20

# 安全模式（网络差，避免卡住）
python3 tools/wiznote_downloader.py --workers 3 --timeout 10 --retries 1

# 查看所有参数
python3 tools/wiznote_downloader.py --help
```

**参数说明**：
- `--workers, -w` - 并发线程数（默认: 5，推荐: 3-10）
- `--timeout, -t` - 下载超时时间/秒（默认: 15，推荐: 10-30）
- `--retries, -r` - 失败重试次数（默认: 2，推荐: 1-3）
- `--connect-timeout, -c` - 连接超时时间/秒（默认: 10，推荐: 5-15）

**支持的笔记类型**：

| 类型 | 支持程度 | 说明 |
|------|---------|------|
| HTML 笔记 | ✅ 完全支持 | 自动转换为 Markdown |
| Lite/Markdown 笔记 | ✅ 完全支持 | 直接保存原格式 |
| 协作笔记 | ✅ 完全支持 | 通过 ShareJS 协议自动获取并转换 |
| 加密笔记 | ⚠️ 检测提醒 | 需要先在客户端解密（RSA+AES） |
| 图片/附件 | ✅ 完全支持 | 下载到 `_files/` 目录 |

**已知限制**：
- 复杂 HTML 表格转换可能不完美
- 某些协作笔记可能需要手动处理
- 加密笔记需要手动解密后重新下载

#### 2. obsidian_formatter.py（主工具）

**作用**：一体化格式化工具，整合所有功能

**使用场景**：90% 的场景都使用这个工具

**功能**：
- 语法检查
- 格式修复
- 链接转换
- 图片修复
- 附件迁移
- 附件链接
- 生成报告

**参数**：
- 无参数 - 执行基础5步（默认）
- `--all` - 执行完整流程（7步，包含附件迁移）
- `--check` - 只检查语法
- `--fix` - 只修复格式
- `--links` - 只转换链接
- `--images` - 只修复图片
- `--migrate-attachments` - 迁移附件
- `--link-attachments` - 添加附件链接
- `--report` - 生成报告
- `--dry-run` - 干运行模式

**使用方法**：
```bash
# 基础迁移（5步，推荐）
python3 tools/obsidian_formatter.py

# 完整迁移（7步，包含附件）
python3 tools/obsidian_formatter.py --all

# 只检查语法
python3 tools/obsidian_formatter.py --check

# 干运行模式（预览）
python3 tools/obsidian_formatter.py --fix --dry-run
```

#### 3. sync_deletions.py

**作用**：安全地同步两个目录的删除操作

**使用场景**：在 WizNote 中删除笔记后同步到 Obsidian

**安全特性**：
- 必须人工确认
- 执行前显示完整清单
- 生成删除日志
- 支持干运行模式

**使用方法**：
```bash
# 扫描差异（只查看）
python3 tools/sync_deletions.py --scan \
  --source wiznote_obsidian \
  --target ~/ObsidianVault

# 确认删除
python3 tools/sync_deletions.py --confirm \
  --source wiznote_obsidian \
  --target ~/ObsidianVault
```

#### 4. migrate_attachments.py

**作用**：迁移 PDF、XMind、Excel 等附件

**使用场景**：需要迁移附件文件

**注意**：已整合到主工具 `obsidian_formatter.py --migrate-attachments`

#### 5. link_attachments.py

**作用**：为笔记添加附件引用

**使用场景**：已迁移附件但笔记中没有链接

**注意**：已整合到主工具 `obsidian_formatter.py --link-attachments`

#### 6. normalize_attachments.py

**作用**：将笔记旁的 `*_files/` 图片和附件统一迁移到 Vault 根目录的 `attachments/`

**使用场景**：
- 希望按 Obsidian 常见做法集中管理附件
- 想把正文里的 `Some Note_files/foo.png` 改成 Obsidian 友好的附件引用
- 想清理导出后残留的未引用图片，例如常见的 `wizIcon_icons_l.png`、`wizIcon_icons_m.png`、`wizIcon_icons_s.png`

**功能**：
- 将被正文引用的本地图片改写为 `![[attachments/...]]`
- 将被正文引用的本地非图片附件改写为 `[[attachments/...|原文本]]`
- 修改 Markdown 前自动生成 `.attachbak` 备份
- 可选删除空图片占位 `![]()`
- 可选列出并删除 `*_files/` 中未被引用的残留图片，同时清理变空目录

**使用方法**：
```bash
# 预览即将执行的变更
python3 tools/normalize_attachments.py --dry-run

# 迁移正文实际引用到的图片/附件
python3 tools/normalize_attachments.py

# 连同空图片占位和未引用的残留图片一起清理
python3 tools/normalize_attachments.py \
  --remove-empty-placeholders \
  --delete-unreferenced-images
```

### 辅助工具

#### 7. config_helper.py

**作用**：配置管理模块

**使用场景**：开发新工具时使用

**注意**：不需要直接运行，被其他工具调用

## ⚙️ 配置说明

### 方式 1：环境变量（推荐）

```bash
export WIZNOTE_SOURCE_DIR=wiznote_download
export WIZNOTE_VAULT_DIR=wiznote_obsidian
# target_dir 默认指向 wiznote_obsidian/ 目录
export WIZNOTE_ATTACHMENTS_DIR=wiznote_obsidian/attachments
```

### 方式 2：配置文件

```bash
cp config.example.json config.json
# 编辑 config.json
python3 tools/obsidian_formatter.py --config config.json
```

### 方式 3：使用默认路径

工具会自动使用以下默认路径：
- `source_dir`: `wiznote_download/`（原始下载）
- `vault_dir`: `wiznote_obsidian/`（格式化输出）
- `target_dir`: `wiznote_obsidian/`（格式化输出）
- `attachments_dir`: `wiznote_obsidian/attachments/`

## 📖 详细文档

完整使用指南请参考：[docs/使用指南.md](../docs/使用指南.md)

## 🔍 常见问题

**Q: 我应该使用哪个工具？**

A:
- 还没有导出笔记 → 使用 `wiznote_downloader.py`
- 已有导出文件 → 使用 `obsidian_formatter.py`（默认5步）
- 需要附件管理 → 使用 `obsidian_formatter.py --all`

**Q: 输出目录在哪里？**

A:
- 原始下载：`wiznote_download/`
- 格式化输出：`wiznote_obsidian/`（在 Obsidian 中打开这个）

**Q: 如何查看工具的详细参数？**

A:
```bash
python3 tools/obsidian_formatter.py --help
python3 tools/sync_deletions.py --help
```

**Q: 主工具的参数太多，记不住怎么办？**

A:
- 记住 `--all` 就够了，90% 的场景都够用
- 需要单独功能时再查看 `--help`
