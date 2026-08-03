# WizNote to Obsidian

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.2.0-green.svg)](CHANGELOG.md)

> 一键将 WizNote 笔记迁移到 Obsidian，支持协作笔记、图片、附件
>
> 📖 **[快速参考指南](QUICK_REFERENCE.md)** | 📚 **[文档索引](DOCUMENTATION_INDEX.md)**

---

## 目录

- [前置要求](#前置要求)
- [快速开始](#-快速开始)
- [命令详解](#-命令详解)
- [使用场景](#-使用场景)
- [常见问题](#-常见问题)
- [高级功能](#-高级功能)
- [项目特性](#-项目特性)
- [工具说明](#-工具说明)
- [已知局限性](#-已知局限性)
- [项目架构](#-项目架构)

---

## 前置要求

```bash
# 1. 检查 Python 版本（需要 3.6+）
python3 --version

# 2. 克隆项目
git clone https://github.com/WardLu/wiznote-to-obsidian.git
cd wiznote-to-obsidian

# 3. 安装依赖（仅在线下载需要）
pip3 install -r requirements.txt
# 或手动安装: pip3 install requests markdownify websocket-client
```

**注意**：离线格式化工具（`obsidian_formatter.py`）是纯 Python 实现，不需要额外依赖。

---

## 快速开始

### 3 步完成迁移

```bash
# 1. 下载笔记
python3 tools/wiznote_downloader.py
# 输入 WizNote 账号密码

# 2. 格式化笔记（基础5步）
python3 tools/obsidian_formatter.py
# 会创建 wiznote_obsidian/ 目录，原始 wiznote_download/ 保持不变

# 3. 在 Obsidian 中打开 wiznote_obsidian 目录
```

**就这么简单！** 99% 的用户只需要这两个命令。

**命令说明**：
- **第 1 步**：下载所有笔记到 `wiznote_download/`（原始数据）
- **第 2 步**：复制到 `wiznote_obsidian/` 并执行 5 步格式化（语法检查 → 格式修复 → 链接转换 → 图片修复 → 生成报告）

**目录说明**：
- `wiznote_download/` - 原始下载的笔记（不会被修改）
- `wiznote_obsidian/` - 格式化后的笔记（在 Obsidian 中打开这个）

**完整迁移**（包含附件集中管理）：
```bash
python3 tools/obsidian_formatter.py --all
```

---

## 命令详解

### 核心命令

#### 1. `python3 tools/wiznote_downloader.py` - 下载笔记

**做什么**：
- 登录 WizNote 云端
- 扫描所有笔记分类
- 下载 449 个笔记（HTML、Lite、协作笔记）
- 下载 7198 张图片
- 下载 30 个附件
- 自动转换为 Markdown 格式
- 生成下载报告

**输出**：
- `wiznote_download/` 目录（包含所有笔记和图片）
- `wiznote_download/download_report.md`（下载报告）

**参数**（可选）：
```bash
# 极速模式（网络好）
python3 tools/wiznote_downloader.py --workers 10 --timeout 20

# 安全模式（网络差）
python3 tools/wiznote_downloader.py --workers 3 --timeout 10 --retries 1

# 查看所有参数
python3 tools/wiznote_downloader.py --help
```

---

#### 2. `python3 tools/obsidian_formatter.py` - 格式化笔记（基础5步）

**做什么**（自动执行以下 5 步）：

##### 步骤 1/5：检查语法
```
检查 Markdown 语法...
   - 检查标题格式（# 后需要空格）
   - 检查标题层级跳跃
   - 检查列表格式
   - 检查代码块语言标识
```

##### 步骤 2/5：修复格式
```
修复格式问题...
   - 修复标题后的空格
   - 统一列表标记（使用 -）
   - 修复空行问题
   - 移除多余空格
```

##### 步骤 3/5：转换链接
```
转换链接为 WikiLinks...
   - 将 [文本](URL) 转换为 [[笔记名]]
   - 转换 WizNote 内部链接
   - 转换附件链接
```

##### 步骤 4/5：修复图片
```
修复图片路径...
   - 统一图片路径格式
   - 修复相对路径
   - 确保图片能正确显示
```

##### 步骤 5/5：生成报告
```
生成统计报告...
   - 统计 Markdown 文件数量（446 个）
   - 统计 WikiLinks 数量（32 个）
```

**输出**：格式化后的 Markdown 文件（直接修改 wiznote_download/ 中的文件）

**注意**：这是默认行为，不带任何参数即可执行

如果 WizNote 导出目录不在项目根目录下，可以显式指定源目录和输出目录：

```bash
python3 tools/obsidian_formatter.py \
  --source /path/to/wiznote_export \
  --target /path/to/wiznote_obsidian
```

如果源目录不存在，工具会在复制前给出明确错误，不再直接显示 Python 堆栈。

---

#### 3. `python3 tools/obsidian_formatter.py --all` - 完整迁移（7步）

**做什么**（基础5步 + 附件迁移）：
1-5. 同上（语法检查 → 格式修复 → 链接转换 → 图片修复 → 生成报告）
6. 迁移附件到 `attachments/` 目录
7. 为笔记添加附件链接

**需要吗？**

**不需要**（大多数情况）：
- 图片已经能正常显示（在 `*_files/` 目录中）
- 只是想查看笔记

**需要**（少数情况）：
- 要长期使用 Obsidian
- 想要在多个笔记间共享附件
- 想要符合 Obsidian 的最佳实践

---

### 单步命令

如果你只想执行特定步骤：

```bash
# 只检查语法（不修改文件）
python3 tools/obsidian_formatter.py --check

# 只修复格式
python3 tools/obsidian_formatter.py --fix

# 只转换链接
python3 tools/obsidian_formatter.py --links

# 只修复图片
python3 tools/obsidian_formatter.py --images

# 只迁移附件（已包含在 --all 中）
python3 tools/obsidian_formatter.py --migrate-attachments

# 只添加附件链接（已包含在 --all 中）
python3 tools/obsidian_formatter.py --link-attachments

# 只生成报告
python3 tools/obsidian_formatter.py --report
```

### 调试命令

```bash
# 干运行模式（预览将要做的修改，不实际修改）
python3 tools/obsidian_formatter.py --fix --dry-run

# 查看配置
python3 tools/obsidian_formatter.py --config config.json --report
```

---

## 使用场景

### 场景 1：首次迁移（推荐，99% 用户）

```bash
# 1. 下载笔记
python3 tools/wiznote_downloader.py

# 2. 格式化（默认5步）
python3 tools/obsidian_formatter.py

# 3. 在 Obsidian 中打开 wiznote_obsidian 目录
# 完成！
```

**说明**：
- 原始 `wiznote_download/` 保持不变
- 格式化后的笔记在 `wiznote_obsidian/`
- 图片已经能正常显示（在 `*_files/` 目录中）

---

### 场景 2：完整迁移（长期使用 Obsidian）

```bash
# 1. 下载笔记
python3 tools/wiznote_downloader.py

# 2. 完整迁移（7步，包含附件管理）
python3 tools/obsidian_formatter.py --all
```

**说明**：
- 适合计划长期使用 Obsidian 的用户
- 附件集中管理，符合 Obsidian 最佳实践

---

### 场景 3：预览修改（谨慎的用户）

```bash
# 1. 下载笔记
python3 tools/wiznote_downloader.py

# 2. 检查语法（不修改）
python3 tools/obsidian_formatter.py --check

# 3. 干运行模式（预览修改）
python3 tools/obsidian_formatter.py --fix --dry-run

# 4. 确认无误后执行
python3 tools/obsidian_formatter.py
```

---

### 场景 4：只修复图片

```bash
# 如果图片显示不正常
python3 tools/obsidian_formatter.py --images
```

---

### 场景 5：重新下载（更新笔记）

```bash
# 1. 重新下载（会跳过已存在的笔记）
python3 tools/wiznote_downloader.py

# 2. 重新格式化（只处理新下载的笔记）
python3 tools/obsidian_formatter.py
```

---

### 场景 6：离线处理（已有导出文件）

如果你已经有 WizNote 导出的文件：

```bash
# 设置路径
export WIZNOTE_SOURCE_DIR=~/wiznote_export

# 执行迁移
python3 tools/obsidian_formatter.py
```

---

## 常见问题

### Q1: 登录后出现 `None/ks/...` 或无法获取目录怎么办？

**A**：这通常表示登录没有真正成功，但旧版本仍继续请求目录接口。当前版本会在登录失败后停止扫描并显示登录错误。

如果账号启用了二次登录验证，请先在 **WizNote X 或网页版**关闭二次登录验证，再重新运行下载工具；经典版客户端没有关闭选项。

---

### Q2: 默认命令和 `--all` 的区别？

**A**:
- `python3 tools/obsidian_formatter.py`（默认）：执行基础5步
  - 语法检查、格式修复、链接转换、图片修复、生成报告
  - 图片保持在原位置（`*_files/` 目录）

- `python3 tools/obsidian_formatter.py --all`（完整）：执行7步
  - 基础5步 + 附件迁移 + 附件链接
  - 附件复制到 `attachments/` 目录

**大多数用户只需要默认命令**，图片已经能正常显示。

---

### Q3: 我需要运行 `--all` 吗？

**A**: 大多数情况下**不需要**。

**不需要**的情况（用默认命令即可）：
- 图片已经能正常显示
- 只是想查看笔记
- 保留原始结构

**需要**的情况：
- 长期使用 Obsidian
- 想要集中管理附件
- 需要在多个笔记间共享附件

---

### Q4: 下载后笔记在哪里？

**A**:
- 原始数据：`wiznote_download/` 目录（不会被修改）
- 格式化后：`wiznote_obsidian/` 目录（在 Obsidian 中打开这个）

```
wiznote_download/          ← 原始下载的笔记
├── My Notes/              # 你的笔记分类
├── 微信收藏/
└── download_report.md     # 下载报告

wiznote_obsidian/          ← 格式化后的笔记（在 Obsidian 中打开）
├── My Notes/
├── 微信收藏/
└── 微博收藏/
```

---

### Q5: 图片在哪里？

**A**: 在每个笔记旁边的 `*_files/` 目录中。

```
wiznote_obsidian/
└── My Notes/
    └── 某某笔记/
        ├── 某某笔记.md
        └── 某某笔记_files/   ← 图片在这里
            ├── image1.jpg
            └── image2.png
```

图片已经在 Markdown 中正确引用，能正常显示。

---

### Q5: 执行顺序是什么？

**A**:

```bash
# 推荐顺序（大多数用户）
python3 tools/wiznote_downloader.py          # 1. 下载（必须）
python3 tools/obsidian_formatter.py          # 2. 格式化（默认5步，必须）

# 如果需要附件集中管理
python3 tools/obsidian_formatter.py --all    # 或直接用 --all 完成所有步骤
```

---

### Q6: 如何在 Obsidian 中使用？

**A**:
1. 打开 Obsidian
2. 点击"打开文件夹作为仓库"
3. 选择 `wiznote_obsidian` 目录（不是 wiznote_download）
4. 完成！

---

### Q7: 格式化会修改原文件吗？

**A**: 不会。格式化会将文件复制到 `wiznote_obsidian/` 目录并修改，原始的 `wiznote_download/` 保持不变。

---

### Q8: 处理了 0 个文件，怎么办？

**A**: 工具会自动检测 `wiznote_download/` 目录。

如果还是 0 个文件：
```bash
# 检查目录是否存在
ls wiznote_download/

# 或使用配置文件
python3 tools/obsidian_formatter.py --config config_wiznote_download.json
```

---

### Q9: 附件迁移后找不到？

**A**: 如果使用 `--all` 命令，附件会被复制到 `attachments/` 目录：

```bash
# 检查附件目录
ls wiznote_obsidian/attachments/
```

---

### Q10: 同步删除工具误删文件怎么办？

**A**: 安全措施：

1. **默认不删除**：
   - 使用 `--scan` 模式，只查看不删除
   - 必须明确使用 `--confirm` 才执行

2. **备份机制**：
   - 删除的文件备份到 `.sync_delete_trash/`
   - 可以从备份恢复

3. **恢复方法**：
   ```bash
   # 从备份恢复
   cp .sync_delete_trash/文件名.md 目标路径/
   ```

---

## 高级功能

### 自定义配置

创建配置文件 `config.json`：

```json
{
  "source_dir": "~/wiznote_export",
  "target_dir": "~/我的笔记",
  "attachments_dir": "wiznote_obsidian/attachments"
}
```

使用配置：
```bash
python3 tools/obsidian_formatter.py --config config.json
```

### 参数调优

#### wiznote_downloader.py 参数

| 参数 | 简写 | 默认值 | 说明 |
|-----|------|--------|------|
| `--workers` | `-w` | 5 | 并发线程数（3-10） |
| `--timeout` | `-t` | 15 | 下载超时/秒（10-30） |
| `--retries` | `-r` | 2 | 失败重试次数（1-3） |
| `--connect-timeout` | `-c` | 10 | 连接超时/秒（5-15） |

**示例**：
```bash
# 网络好，快速下载
python3 tools/wiznote_downloader.py -w 10 -t 20

# 网络差，稳定下载
python3 tools/wiznote_downloader.py -w 3 -t 10 -r 1
```

**性能对比**：

| 模式 | workers | timeout | 适用场景 | 预估速度 |
|------|---------|---------|---------|---------|
| 默认模式 | 5 | 15s | 大部分网络 | 基准 |
| 极速模式 | 10 | 20s | 网络好 | 2-3倍 |
| 安全模式 | 3 | 10s | 网络差 | 0.6倍 |

---

## 项目特性

### 笔记类型支持

#### 完全支持

| 笔记类型 | 说明 | 处理方式 |
|---------|------|---------|
| **HTML 笔记** | WizNote 默认笔记类型（富文本编辑器） | 自动下载并转换为 Markdown |
| **Lite/Markdown 笔记** | Markdown 格式笔记 | 直接保存，保持原格式 |
| **协作笔记** | 多人实时协作的笔记（ShareJS 协议） | 通过 WebSocket 自动获取并转换为 Markdown |
| **图片资源** | 笔记中的内嵌图片（JPG、PNG、GIF 等） | 下载到 `{笔记名}_files/` 目录 |
| **附件文件** | PDF、XMind、Excel、PPT 等 | 下载到 `{笔记名}_files/` 目录 |

#### 部分支持

| 笔记类型 | 说明 | 限制 | 处理方式 |
|---------|------|------|---------|
| **加密笔记** | 密码保护的笔记 | 需要 RSA+AES 解密 | 检测并记录在报告中；需用户在客户端解密后重新下载 |

#### 不支持

| 笔记类型 | 说明 | 替代方案 |
|---------|------|---------|
| **已删除的笔记** | 回收站中的笔记 | 在 WizNote 客户端中恢复后再下载 |
| **共享给我的笔记** | 他人共享但未协作的笔记 | 请求所有者转为协作笔记或手动复制 |

### 核心功能

- **自动化迁移** - 一键完成笔记迁移
- **格式优化** - 自动修复 Markdown 语法
- **图片处理** - 统一管理所有图片
- **附件迁移** - 完整迁移 PDF、XMind 等附件
- **链接转换** - 自动转换为 WikiLinks
- **同步删除** - 安全地同步删除操作
- **完整报告** - 详细的迁移统计
- **并发下载** - 多线程加速，2 分 20 秒完成 449 个笔记
- **协作笔记支持** - 通过 WebSocket 自动下载协作笔记（v1.1 新增）
- **加密笔记检测** - 自动识别加密笔记并提醒用户解密（v1.1 新增）

### 实际测试数据

基于真实 WizNote 账号的完整迁移测试结果：

| 指标 | 数量 | 成功率 |
|-----|------|--------|
| **笔记** | 447/449 | 99.6% |
| **图片** | 7198/7198 | 100% |
| **附件** | 30/30 | 100% |
| **协作笔记** | 25/25 | 100% |

**性能指标**：
- **总耗时**: 2 分 20 秒（140 秒）
- **平均速度**: 3.2 个笔记/秒
- **失败笔记**: 2 个（文件名异常）

---

## 工具说明

所有工具位于 `tools/` 目录：

### 主要工具

| 工具 | 作用 | 使用场景 |
|------|------|---------|
| `wiznote_downloader.py` | 在线下载工具 | 从 WizNote 云端下载笔记 |
| `obsidian_formatter.py` | 离线格式化工具 | 处理已导出的 Markdown 文件 |

### 辅助工具

#### 1. sync_deletions.py（同步删除工具）

**作用**：安全地同步两个目录的删除操作

**使用场景**：
- 在 WizNote 导出目录中删除了笔记
- 需要在 Obsidian Vault 中同步删除
- 需要清理不需要的文件

**安全特性**：
- 不会自动删除，必须人工确认
- 执行前显示完整的删除清单
- 显示两边文件的映射关系
- 生成删除日志，可追溯
- 支持干运行模式（只显示，不删除）

**使用流程**：
```bash
# 步骤 1: 扫描差异（只查看，不删除）
python3 tools/sync_deletions.py --scan \
  --source ~/wiznote_export \
  --target ~/ObsidianVault

# 步骤 2: 查看报告，确认要删除的文件

# 步骤 3: 确认删除
python3 tools/sync_deletions.py --confirm \
  --source ~/wiznote_export \
  --target ~/ObsidianVault

# 步骤 4: 查看日志
cat sync_delete_*.log
```

**注意**：
- 删除操作不可逆，请仔细查看报告
- 删除的文件会备份到 `.sync_delete_trash/` 目录
- 建议先使用 `--dry-run` 模式预览

---

#### 2. config_helper.py（配置助手模块）

**作用**：配置管理助手，供其他工具使用

**功能**：
- 支持环境变量配置
- 支持 JSON 配置文件
- 统一配置管理

**使用场景**：
- 开发新工具时使用
- 不需要直接运行

**配置方式**：

方式 1：环境变量（推荐）
```bash
export WIZNOTE_SOURCE_DIR=~/wiznote_export
export WIZNOTE_VAULT_DIR=~/ObsidianVault
export WIZNOTE_ATTACHMENTS_DIR=wiznote_obsidian/attachments
```

方式 2：配置文件
```bash
cd tools
cp config.example.json config.json
# 编辑 config.json
python3 tools/obsidian_formatter.py --config config.json
```

---

## 已知局限性

### 技术限制

1. **API 访问限制**
   - WizNote API 可能有速率限制
   - 某些企业版/团队版账号可能有额外权限限制
   - **建议**：使用适当的并发参数（默认 5 线程）

2. **加密笔记解密**
   - 采用 RSA + AES 混合加密，需要证书和密码
   - 工具无法自动解密
   - **建议**：在 WizNote 客户端中批量解密后再运行工具

### 格式转换限制

3. **HTML → Markdown 转换**
   - 复杂的 HTML 表格可能转换不完美
   - 嵌套列表可能出现缩进问题
   - 特殊 HTML 标签（如 `<iframe>`）会被移除
   - **建议**：下载后使用 `obsidian_formatter.py` 优化格式

4. **图片路径引用**
   - 某些旧版本笔记的图片路径可能无法正确识别
   - **建议**：手动检查并修复图片链接

5. **附件类型识别**
   - 某些特殊文件类型可能无法正确识别为附件
   - **建议**：检查下载报告中的失败附件列表

### 网络和环境限制

6. **网络稳定性**
   - 大量下载时可能因网络问题导致部分失败
   - **建议**：使用稳定网络；网络差时使用"安全模式"参数

7. **WizNote 服务可用性**
   - WizNote 服务器维护或故障时无法下载
   - **建议**：错峰下载或等待服务恢复

8. **Python 环境**
   - 需要 Python 3.6+
   - 需要 `websocket-client` 库支持协作笔记
   - **建议**：使用虚拟环境隔离依赖

### 数据完整性

9. **笔记元数据**
   - 某些笔记的创建时间、标签等元数据可能缺失
   - **建议**：下载后手动补充重要元数据

10. **版本兼容性**
    - 早期 WizNote 版本创建的笔记格式可能不兼容
    - **建议**：在 WizNote 客户端中更新笔记格式

---

## 最佳实践

为了避免上述局限性带来的问题，建议：

1. **分批下载**：先小批量测试，确认无误后再全量下载
2. **检查报告**：每次下载后仔细查看 `download_report.md`
3. **双重备份**：下载完成后保留原始 WizNote 数据一段时间
4. **格式优化**：使用 `obsidian_formatter.py` 优化下载的笔记
5. **手动验证**：在 Obsidian 中抽查重要笔记的内容完整性

---

## 贡献

欢迎贡献代码、报告问题或提出建议！

---

## 许可证

[MIT License](LICENSE)

---

## 项目架构

本项目采用 **开源工具 + 商业应用** 的双轨架构。

### 架构说明

- **开源部分**：本仓库的 `tools/` 目录，包含所有命令行工具，完全免费
- **商业部分**：`app/` 目录（Git Submodule），提供图形界面的桌面应用

详细架构说明请查看：**[ARCHITECTURE.md](ARCHITECTURE.md)**

### 快速选择

- ✅ **技术用户** → 使用本仓库的命令行工具
- ✅ **非技术用户** → 使用商业桌面应用（图形界面）

---

## 联系方式

如有问题或建议，请提交 [GitHub Issue](https://github.com/WardLu/wiznote-to-obsidian/issues)

---

**如果这个项目对你有帮助，请给一个 Star！**
