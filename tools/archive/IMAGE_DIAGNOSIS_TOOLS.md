# WizNote 图片下载诊断工具集

> 用于诊断和修复 WizNote 笔记图片下载问题的工具集

## 📋 目录

- [概述](#概述)
- [工具列表](#工具列表)
- [快速开始](#快速开始)
- [详细使用说明](#详细使用说明)
- [常见问题](#常见问题)

---

## 概述

在使用 WizNote 在线下载工具时，某些笔记的图片可能无法正常下载。这些诊断工具帮助你：

- ✅ 批量扫描所有笔记，发现缺失的图片
- ✅ 诊断特定笔记的图片下载问题
- ✅ 生成重新下载列表
- ✅ 分析 API 响应，找出根本原因

---

## 工具列表

| 工具 | 功能 | 使用场景 |
|------|------|---------|
| **batch_diagnose_images.py** | 批量扫描缺失图片 | 发现所有图片缺失的笔记 |
| **diagnose_image_download.py** | 诊断单个笔记 | 深入分析特定笔记的问题 |
| **generate_redownload_list.py** | 生成重新下载列表 | 生成需要重新下载的笔记清单 |
| **selective_redownload.py** | 选择性重新下载 | 只重新下载图片缺失的笔记 |

---

## 快速开始

### 第一步：批量扫描

```bash
# 扫描所有笔记，找出缺失图片
cd /Users/wardlu/Documents/VibeCoding/Wiznote\ to\ Obisidian
python3 tools/batch_diagnose_images.py
```

**输出**：
- 控制台：显示缺失图片的笔记列表
- `missing_images_report.txt`：详细的缺失图片报告

### 第二步：生成重新下载列表

```bash
# 生成按严重程度排序的重新下载列表
python3 tools/generate_redownload_list.py
```

**输出**：
- 控制台：显示严重问题列表
- `redownload_list.txt`：需要重新下载的笔记清单

### 第三步：预览将要删除的文件（推荐）

```bash
# 干运行模式 - 只预览，不实际删除
python3 tools/selective_redownload.py --dry-run

# 或只预览严重问题
python3 tools/selective_redownload.py --dry-run --severe-only
```

**输出**：
- 显示将要删除的 Markdown 文件列表
- 不会实际删除文件

### 第四步：删除目标笔记的 Markdown 文件

```bash
# 执行删除（会询问确认）
python3 tools/selective_redownload.py

# 或只处理严重问题
python3 tools/selective_redownload.py --severe-only

# 或强制执行（不询问确认）
python3 tools/selective_redownload.py --force
```

**输出**：
- 删除目标笔记的 `.md` 文件
- 生成删除日志 `deleted_files_log.txt`

### 第五步：重新下载

```bash
# 标准模式
python3 tools/wiznote_downloader.py

# 或极速模式（网络好）
python3 tools/wiznote_downloader.py --workers 10 --timeout 20
```

**重要**：
- ✅ `wiznote_downloader.py` 会自动跳过已存在的笔记
- ✅ 只下载被删除的笔记
- ✅ 尝试下载图片和附件

---

## 详细使用说明

### 1. batch_diagnose_images.py - 批量图片诊断

#### 功能
- 扫描 `wiznote_download` 目录下的所有 Markdown 文件
- 检查每个笔记的图片引用与实际下载的图片数量
- 生成详细的缺失图片报告

#### 使用方法

```bash
# 基本用法（扫描默认目录）
python3 tools/batch_diagnose_images.py

# 指定下载目录
python3 tools/batch_diagnose_images.py --download-dir ~/my_wiznote

# 只显示严重问题（缺失 >= 10 张图片）
python3 tools/batch_diagnose_images.py --severe-only
```

#### 参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--download-dir` | `-d` | 下载目录路径 | wiznote_download |
| `--severe-only` | `-s` | 只显示严重问题 | False |

#### 输出示例

```
======================================================================
🔍 批量图片下载诊断工具
======================================================================

⚠️  发现 50 个笔记存在图片缺失问题：

文件名                                                引用     下载     缺失
----------------------------------------------------------------------
技术笔记/产品经理PM/智能制造MES拆解.md                36     0      36
人人都是开发者——无代码产品...                       24     0      24
产品年度规划怎么做.md                              21     0      21
...

总计                                                340

📄 详细报告已保存到: missing_images_report.txt
```

---

### 2. diagnose_image_download.py - 单个笔记诊断

#### 功能
- 诊断特定笔记的图片下载问题
- 检查 API 返回的资源列表
- 分析 Markdown 中的图片引用
- 保存完整的 API 响应用于调试

#### 使用方法

```bash
# 交互式使用（会提示输入笔记标题）
python3 tools/diagnose_image_download.py

# 直接指定笔记标题
python3 tools/diagnose_image_download.py --note "智能制造MES拆解"

# 保存调试信息
python3 tools/diagnose_image_download.py --note "智能制造MES拆解" --save-debug
```

#### 参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--note` | `-n` | 要诊断的笔记标题 | 交互式输入 |
| `--save-debug` | - | 保存完整的 API 响应 | False |

#### 输出示例

```
======================================================================
🔍 诊断笔记: 智能制造MES拆解
======================================================================

Step 1: 搜索笔记...
✅ 找到笔记: abc123...

Step 2: 检查 API 返回的资源列表...
⚠️  API 返回的资源列表为空！

Step 3: 查看原始 API 响应...
📦 API 返回的字段:
   - html: 12345 字符
   - resources: 0 项

📄 完整 API 响应已保存到: debug_api_response.json

⚠️  问题确认: API 没有返回图片资源，但 Markdown 中有图片引用
💡 解决方案:
   1. 使用离线导出方式（在 WizNote 客户端中导出）
   2. 手动下载图片并放到对应的 _files 文件夹
```

---

### 3. generate_redownload_list.py - 生成重新下载列表

#### 功能
- 读取 `missing_images_report.txt`
- 按缺失图片数量排序
- 标记严重问题（缺失 >= 10 张图片）
- 生成 `redownload_list.txt`

#### 使用方法

```bash
# 基本用法
python3 tools/generate_redownload_list.py

# 指定报告文件路径
python3 tools/generate_redownload_list.py --report ~/missing_images_report.txt

# 自定义严重问题阈值
python3 tools/generate_redownload_list.py --severe-threshold 5
```

#### 参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--report` | `-r` | 缺失图片报告文件路径 | missing_images_report.txt |
| `--severe-threshold` | `-t` | 严重问题的缺失图片数阈值 | 10 |

#### 输出示例

```
======================================================================
📝 需要重新下载的笔记列表
======================================================================

✅ 已生成重新下载列表: redownload_list.txt
   共 50 个笔记需要处理

🚨 严重问题（缺失 >= 10 张图片）：9 个笔记

   - 微信收藏/银行股评级（2017.7-2018.12） (64 张)
   - 技术笔记/产品经理PM/智能制造MES拆解.md (36 张)
   ...

💡 建议：
   1. 在 WizNote 客户端中导出这些笔记
   2. 使用离线迁移工具处理导出的文件
   3. 或手动下载缺失的图片到对应的 _files 文件夹
```

---

### 4. selective_redownload.py - 选择性重新下载

#### 功能
- 读取 `redownload_list.txt` 或 `missing_images_report.txt`
- 删除目标笔记的 Markdown 文件（触发重新下载）
- 支持干运行模式预览
- 生成删除日志

#### 使用方法

```bash
# 干运行模式（预览将要删除的文件）
python3 tools/selective_redownload.py --dry-run

# 执行删除
python3 tools/selective_redownload.py

# 只处理严重问题
python3 tools/selective_redownload.py --severe-only

# 强制执行（不询问确认）
python3 tools/selective_redownload.py --force
```

#### 参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--list` | `-l` | 重新下载列表文件 | redownload_list.txt |
| `--download-dir` | `-d` | 下载目录 | wiznote_download |
| `--severe-only` | `-s` | 只处理严重问题 | False |
| `--dry-run` | - | 干运行模式 | False |
| `--force` | `-f` | 强制执行 | False |

#### 输出示例

```
======================================================================
🔄 选择性重新下载工具
======================================================================

📋 将要处理 9 个笔记：

将要删除 9 个 Markdown 文件：

   1. 技术笔记/产品经理PM/智能制造MES拆解.md
   2. 技术笔记/产品经理PM/人人都是开发者——无代码产品...
   ...

⚠️  确认删除这 9 个文件？[y/N] y

🗑️  正在删除 9 个 Markdown 文件...

   ✅ 已删除: 技术笔记/产品经理PM/智能制造MES拆解.md
   ...

======================================================================
📊 删除统计
======================================================================
   ✅ 成功删除: 9 个文件

💡 下一步：
   运行 wiznote_downloader.py 重新下载这些笔记
```

#### 工作原理

1. **读取重新下载列表**
   - 从 `redownload_list.txt` 读取需要处理的笔记

2. **查找 Markdown 文件**
   - 在 `wiznote_download` 目录中查找对应的 `.md` 文件

3. **删除 Markdown 文件**
   - 删除目标笔记的 `.md` 文件
   - 触发 `wiznote_downloader.py` 的重新下载机制

4. **生成删除日志**
   - 保存到 `deleted_files_log.txt`

**重要**：`wiznote_downloader.py` 会自动跳过已存在的笔记（代码第 502 行）：

```python
if md_file_path.exists():
    return {"status": "skip", "title": safe_title}
```

所以需要先删除 `.md` 文件才能触发重新下载。

---

## 常见问题

### Q1: 为什么下载报告显示 0 张图片，但实际有图片链接？

**A**: 这是为知笔记 API 的缺陷。`/ks/note/download/` API 在某些笔记上不返回 `resources` 字段，导致下载工具误判为"没有图片"。

**解决方案**：
1. 使用 `batch_diagnose_images.py` 扫描所有笔记
2. 使用离线导出方式（在 WizNote 客户端中导出）
3. 或重新运行在线下载工具

---

### Q2: wiznote_downloader.py 会自动跳过已存在的笔记吗？

**A**: ✅ 是的。代码第 502 行：

```python
if md_file_path.exists():
    return {"status": "skip", "title": safe_title}
```

**但是**：
- ❌ 如果 Markdown 文件存在但图片缺失，也会跳过
- ✅ 所以需要使用 `selective_redownload.py` 先删除 Markdown 文件

**工作流程**：
1. 运行 `selective_redownload.py` 删除图片缺失笔记的 `.md` 文件
2. 运行 `wiznote_downloader.py` 重新下载
3. 工具会自动跳过已存在的笔记，只下载被删除的

---

### Q3: 如何判断哪些笔记需要优先处理？

**A**: 运行 `generate_redownload_list.py`，它会按缺失图片数量排序，并标记严重问题（缺失 >= 10 张图片）。

```bash
python3 tools/generate_redownload_list.py --severe-threshold 10
```

---

### Q4: 能否只修复部分图片缺失的笔记？

**A**: 可以。步骤如下：

1. 运行批量扫描，找出所有缺失图片的笔记
```bash
python3 tools/batch_diagnose_images.py
```

2. 查看报告，选择需要修复的笔记
```bash
cat missing_images_report.txt
```

3. 预览将要删除的文件
```bash
python3 tools/selective_redownload.py --dry-run
```

4. 执行删除并重新下载
```bash
python3 tools/selective_redownload.py
python3 tools/wiznote_downloader.py
```

---

### Q5: 诊断工具需要登录 WizNote 账号吗？

**A**:
- `batch_diagnose_images.py` - **不需要**（只扫描本地文件）
- `diagnose_image_download.py` - **需要**（需要调用 API）
- `generate_redownload_list.py` - **不需要**（只处理报告文件）
- `selective_redownload.py` - **不需要**（只删除本地文件）
- `wiznote_downloader.py` - **需要**（需要从云端下载）

---

### Q6: 删除 Markdown 文件会丢失笔记内容吗？

**A**: ❌ 不会。因为：
- ✅ 笔记内容存储在 WizNote 云端
- ✅ wiznote_downloader.py 会从云端重新下载
- ✅ 只是触发重新下载机制

---

### Q7: 重新下载能保证图片都下载成功吗？

**A**: 🟡 不一定。因为：
- ❌ 为知笔记 API 本身可能有缺陷
- ✅ 但重新下载可以解决网络问题导致的失败
- ✅ 建议使用离线导出方式作为备选方案

**备选方案**：
```bash
# 在 WizNote 客户端中导出笔记
# 然后使用迁移工具处理
export WIZNOTE_SOURCE_DIR=~/wiznote_export
python3 tools/wiznote_to_obsidian.py --all
```

---

### Q8: 生成的报告文件保存在哪里？

**A**:
- `missing_images_report.txt` - 在项目根目录
- `redownload_list.txt` - 在项目根目录
- `deleted_files_log.txt` - 在项目根目录（执行删除后）
- `debug_api_response.json` - 在项目根目录（使用 `--save-debug` 时）

---

### Q9: 如何验证重新下载是否成功？

**A**: 再次运行批量扫描工具：

```bash
# 扫描所有笔记
python3 tools/batch_diagnose_images.py

# 或只检查严重问题
python3 tools/batch_diagnose_images.py --severe-only
```

如果成功，应该显示：
```
✅ 所有图片都已正确下载！
```

或严重问题数量减少。

---

### Q10: 如果重新下载仍然失败怎么办？

**A**: 使用离线导出方式（最可靠）：

```bash
# 1. 在 WizNote 客户端中导出笔记
#    - 打开 WizNote 客户端
#    - 选择所有笔记
#    - 文件 → 导出 → Markdown 格式
#    - 导出到 ~/wiznote_export

# 2. 使用迁移工具处理
export WIZNOTE_SOURCE_DIR=~/wiznote_export
python3 tools/wiznote_to_obsidian.py --all
```

**优点**：
- ✅ 100% 可靠（不依赖 API）
- ✅ 图片和附件都会正确导出
- ✅ 不受网络问题影响

## 工作流程建议

### 完整诊断流程（推荐）

```bash
# 1. 批量扫描
python3 tools/batch_diagnose_images.py

# 2. 生成重新下载列表
python3 tools/generate_redownload_list.py

# 3. 预览将要删除的文件（推荐）
python3 tools/selective_redownload.py --dry-run

# 4. 执行删除
python3 tools/selective_redownload.py

# 5. 重新下载
python3 tools/wiznote_downloader.py

# 6. 验证结果
python3 tools/batch_diagnose_images.py
```

### 快速诊断流程

```bash
# 一行命令完成扫描和列表生成
python3 tools/batch_diagnose_images.py && python3 tools/generate_redownload_list.py
```

### 只处理严重问题

```bash
# 1. 只扫描严重问题
python3 tools/batch_diagnose_images.py --severe-only

# 2. 生成列表（自定义阈值）
python3 tools/generate_redownload_list.py --severe-threshold 10

# 3. 预览严重问题
python3 tools/selective_redownload.py --dry-run --severe-only

# 4. 执行删除（严重问题）
python3 tools/selective_redownload.py --severe-only

# 5. 重新下载
python3 tools/wiznote_downloader.py

# 6. 验证
python3 tools/batch_diagnose_images.py --severe-only
```

### 离线导出流程（最可靠）

如果在线下载仍有问题，使用此流程：

```bash
# 1. 在 WizNote 客户端中导出
#    - 打开 WizNote 客户端
#    - 选择所有笔记
#    - 文件 → 导出 → Markdown 格式
#    - 导出到 ~/wiznote_export

# 2. 使用迁移工具处理
export WIZNOTE_SOURCE_DIR=~/wiznote_export
python3 tools/wiznote_to_obsidian.py --all
```

---

## 相关文档

- [主工具使用指南](../README.md)
- [P0 问题修复器](./fix_p0_issues.py)
- [在线下载工具](./wiznote_downloader.py)
- [迁移工具](./wiznote_to_obsidian.py)

---

## 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 1.0.0 | 2026-02-26 | 初始版本，包含三个诊断工具 |

---

## 贡献

如发现问题或有改进建议，请提交 Issue 或 Pull Request。
