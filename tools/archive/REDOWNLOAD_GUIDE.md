# 重新下载图片缺失笔记 - 完整指南

> 更新时间：2026-02-26

## 🎯 两种方案

### 方案 1：选择性重新下载（推荐）

**只重新下载图片缺失的笔记**

✅ **优点**：
- 节省时间（只下载需要的笔记）
- 节省带宽
- 不会影响已有的笔记

❌ **缺点**：
- 需要额外的步骤

### 方案 2：全量重新下载

**删除所有下载，重新下载所有笔记**

✅ **优点**：
- 操作简单
- 确保所有笔记都是最新的

❌ **缺点**：
- 耗时长
- 浪费带宽
- 可能再次遇到相同的问题

---

## 📋 方案 1：选择性重新下载（推荐）

### 步骤概览

```
1. 批量扫描缺失图片
   ↓
2. 生成重新下载列表
   ↓
3. 预览将要删除的文件（干运行）
   ↓
4. 删除目标笔记的 Markdown 文件
   ↓
5. 运行在线下载工具重新下载
```

### 详细步骤

#### Step 1: 批量扫描缺失图片

```bash
# 扫描所有笔记
python3 tools/batch_diagnose_images.py

# 或只查看严重问题（缺失 >= 10 张图片）
python3 tools/batch_diagnose_images.py --severe-only
```

**输出**：`missing_images_report.txt`

---

#### Step 2: 生成重新下载列表

```bash
# 生成列表
python3 tools/generate_redownload_list.py

# 或只生成严重问题列表
python3 tools/generate_redownload_list.py --severe-threshold 10
```

**输出**：`redownload_list.txt`

---

#### Step 3: 预览将要删除的文件（干运行）

```bash
# 预览将要删除的文件（不实际删除）
python3 tools/selective_redownload.py --dry-run
```

**示例输出**：

```
======================================================================
🔄 选择性重新下载工具
======================================================================

📋 将要处理 50 个笔记：

将要删除 50 个 Markdown 文件：

   1. 技术笔记/产品经理PM/智能制造MES拆解.md
   2. 技术笔记/产品经理PM/人人都是开发者——无代码产品...
   ...

🔍 干运行模式 - 不会实际删除文件

💡 移除 --dry-run 参数以执行删除操作
```

---

#### Step 4: 删除目标笔记的 Markdown 文件

```bash
# 执行删除（会询问确认）
python3 tools/selective_redownload.py

# 或强制执行（不询问确认）
python3 tools/selective_redownload.py --force

# 或只处理严重问题
python3 tools/selective_redownload.py --severe-only
```

**示例输出**：

```
======================================================================
🔄 选择性重新下载工具
======================================================================

📋 将要处理 9 个笔记：

将要删除 9 个 Markdown 文件：

   1. 技术笔记/产品经理PM/智能制造MES拆解.md
   ...

⚠️  确认删除这 9 个文件？[y/N] y

🗑️  正在删除 9 个 Markdown 文件...

   ✅ 已删除: 技术笔记/产品经理PM/智能制造MES拆解.md
   ...

======================================================================
📊 删除统计
======================================================================
   ✅ 成功删除: 9 个文件

======================================================================
💡 下一步
======================================================================

1. 运行在线下载工具重新下载这些笔记：
   python3 tools/wiznote_downloader.py

2. wiznote_downloader.py 会自动跳过已存在的笔记
   您删除的 9 个笔记将被重新下载
```

---

#### Step 5: 运行在线下载工具重新下载

```bash
# 标准模式
python3 tools/wiznote_downloader.py

# 或极速模式（网络好）
python3 tools/wiznote_downloader.py --workers 10 --timeout 20
```

**重要**：`wiznote_downloader.py` 会自动：
- ✅ 跳过已存在的笔记（第 502 行）
- ✅ 只下载被删除的笔记
- ✅ 尝试下载图片和附件

---

## 📋 方案 2：全量重新下载

### 步骤

#### 选项 A：删除 wiznote_download 目录（不推荐）

```bash
# ⚠️ 警告：这会删除所有已下载的笔记

# 1. 删除现有下载
rm -rf wiznote_download

# 2. 重新下载
python3 tools/wiznote_downloader.py
```

**缺点**：
- 所有笔记都会重新下载
- 浪费时间和带宽
- 可能再次遇到相同的问题

---

#### 选项 B：保留 wiznote_download，让工具自动跳过

```bash
# wiznote_downloader.py 会自动跳过已存在的笔记
python3 tools/wiznote_downloader.py
```

**工作原理**：

```python
# wiznote_downloader.py 第 502 行
if md_file_path.exists():
    return {"status": "skip", "title": safe_title}
```

**问题**：
- ❌ 如果 Markdown 文件存在但图片缺失，也会跳过
- ❌ 不会重新下载缺失的图片

---

## 🎓 推荐工作流程

### 完整诊断和修复流程

```bash
# 1. 批量扫描
python3 tools/batch_diagnose_images.py

# 2. 生成重新下载列表
python3 tools/generate_redownload_list.py

# 3. 预览（干运行）
python3 tools/selective_redownload.py --dry-run

# 4. 执行删除
python3 tools/selective_redownload.py --severe-only

# 5. 重新下载
python3 tools/wiznote_downloader.py

# 6. 验证结果
python3 tools/batch_diagnose_images.py --severe-only
```

---

## 🔧 工具参数详解

### selective_redownload.py

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--list` | `-l` | 重新下载列表文件 | redownload_list.txt |
| `--download-dir` | `-d` | 下载目录 | wiznote_download |
| `--severe-only` | `-s` | 只处理严重问题 | False |
| `--dry-run` | - | 干运行模式 | False |
| `--force` | `-f` | 强制执行（不询问确认） | False |

### wiznote_downloader.py

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--workers` | `-w` | 并发线程数 | 5 |
| `--timeout` | `-t` | 下载超时时间/秒 | 15 |
| `--retries` | `-r` | 失败重试次数 | 2 |
| `--connect-timeout` | `-c` | 连接超时时间/秒 | 10 |

---

## 📊 方案对比

| 特性 | 方案 1（选择性） | 方案 2（全量） |
|------|----------------|---------------|
| 下载时间 | ⚡ 快（只下载缺失的） | 🐢 慢（下载全部） |
| 带宽消耗 | ✅ 少 | ❌ 多 |
| 操作复杂度 | 🟡 中等（5 步） | 🟢 简单（2 步） |
| 成功率 | ✅ 高（针对性修复） | 🟡 中（可能再次失败） |
| 推荐程度 | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## ⚠️ 常见问题

### Q1: wiznote_downloader.py 会自动跳过已存在的笔记吗？

**A**: ✅ 是的。代码第 502 行：

```python
if md_file_path.exists():
    return {"status": "skip", "title": safe_title}
```

**但是**：
- ❌ 如果 Markdown 文件存在但图片缺失，也会跳过
- ✅ 所以需要先删除 Markdown 文件

---

### Q2: 删除 Markdown 文件会丢失笔记内容吗？

**A**: ❌ 不会。因为：
- ✅ 笔记内容存储在 WizNote 云端
- ✅ wiznote_downloader.py 会从云端重新下载
- ✅ 只是触发重新下载机制

---

### Q3: 重新下载能保证图片都下载成功吗？

**A**: 🟡 不一定。因为：
- ❌ 为知笔记 API 本身可能有缺陷
- ✅ 但重新下载可以解决网络问题导致的失败
- ✅ 建议使用离线导出方式作为备选方案

---

### Q4: 如果重新下载仍然失败怎么办？

**A**: 使用离线导出方式：

```bash
# 1. 在 WizNote 客户端中导出笔记
#    - 选择所有笔记
#    - 文件 → 导出 → Markdown 格式
#    - 导出到 ~/wiznote_export

# 2. 使用迁移工具处理
export WIZNOTE_SOURCE_DIR=~/wiznote_export
python3 tools/wiznote_to_obsidian.py --all
```

---

## 📝 总结

### 推荐方案

**✅ 方案 1：选择性重新下载**

```bash
# 完整流程（5 步）
python3 tools/batch_diagnose_images.py
python3 tools/generate_redownload_list.py
python3 tools/selective_redownload.py --dry-run  # 预览
python3 tools/selective_redownload.py           # 执行
python3 tools/wiznote_downloader.py             # 重新下载
```

### 关键要点

1. **wiznote_downloader.py 会自动跳过已存在的笔记**
   - 只检查 `.md` 文件是否存在
   - 不检查图片是否完整

2. **selective_redownload.py 的作用**
   - 删除图片缺失笔记的 `.md` 文件
   - 触发重新下载机制

3. **推荐先使用 --dry-run 预览**
   - 确认要删除的文件
   - 避免误操作

4. **离线导出是备选方案**
   - 如果在线下载仍有问题
   - 使用 WizNote 客户端导出

---

**更新时间**：2026-02-26
**工具版本**：v1.1.0
