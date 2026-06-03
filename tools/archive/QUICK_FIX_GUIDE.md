# 一键修复图片/附件缺失 - 快速指南

> 从 5 步简化到 2 步！

## 🎯 新的工作流程（只需 2 步）

```bash
# 第 1 步：一键修复（扫描 + 生成列表 + 删除文件）
python3 tools/fix_missing_resources.py

# 第 2 步：重新下载
python3 tools/wiznote_downloader.py
```

---

## 📋 详细说明

### 第 1 步：一键修复

#### 基本用法（推荐）

```bash
# 完整流程：扫描 → 生成列表 → 删除文件
python3 tools/fix_missing_resources.py
```

**会询问确认**：删除文件前会询问 `[y/N]`

---

#### 只扫描，不删除

```bash
# 只生成报告，不删除文件
python3 tools/fix_missing_resources.py --scan-only
```

**适用场景**：先查看问题，再决定是否修复

---

#### 只处理严重问题

```bash
# 只处理总缺失 >= 10 个的笔记
python3 tools/fix_missing_resources.py --severe-only
```

**适用场景**：优先修复严重问题

---

#### 预览模式（推荐）

```bash
# 预览将要删除的文件，不实际删除
python3 tools/fix_missing_resources.py --dry-run
```

**适用场景**：先预览，确认无误后再执行

---

#### 强制执行（不询问）

```bash
# 不询问确认，直接删除
python3 tools/fix_missing_resources.py --force
```

**适用场景**：已确认要删除，不想手动确认

---

### 第 2 步：重新下载

```bash
# 标准模式
python3 tools/wiznote_downloader.py

# 或极速模式（网络好）
python3 tools/wiznote_downloader.py --workers 10 --timeout 20
```

**自动跳过**：wiznote_downloader.py 会自动跳过已存在的笔记，只下载被删除的

---

## 📊 输出文件

运行 `fix_missing_resources.py` 后会生成：

| 文件 | 说明 |
|------|------|
| `missing_resources_report.txt` | 详细的缺失报告（图片+附件） |
| `redownload_list.txt` | 重新下载列表 |
| `deleted_files_log.txt` | 删除日志（仅执行删除后） |

---

## 🎓 常见用法

### 场景 1：完整修复流程（推荐）

```bash
# 1. 预览将要删除的文件
python3 tools/fix_missing_resources.py --dry-run

# 2. 确认无误后执行
python3 tools/fix_missing_resources.py

# 3. 重新下载
python3 tools/wiznote_downloader.py

# 4. 验证结果
python3 tools/fix_missing_resources.py --scan-only
```

---

### 场景 2：只修复严重问题

```bash
# 1. 预览严重问题
python3 tools/fix_missing_resources.py --dry-run --severe-only

# 2. 执行修复
python3 tools/fix_missing_resources.py --severe-only

# 3. 重新下载
python3 tools/wiznote_downloader.py
```

---

### 场景 3：自动化流程

```bash
# 一行命令完成所有操作
python3 tools/fix_missing_resources.py --force && python3 tools/wiznote_downloader.py
```

---

## ⚙️ 参数说明

### fix_missing_resources.py

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--download-dir` | `-d` | 下载目录 | wiznote_download |
| `--scan-only` | - | 只扫描，不删除 | False |
| `--severe-only` | `-s` | 只处理严重问题 | False |
| `--severe-threshold` | `-t` | 严重问题阈值 | 10 |
| `--dry-run` | - | 干运行模式 | False |
| `--force` | `-f` | 强制执行 | False |

### wiznote_downloader.py

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--workers` | `-w` | 并发线程数 | 5 |
| `--timeout` | `-t` | 超时时间/秒 | 15 |
| `--retries` | `-r` | 重试次数 | 2 |

---

## 🔄 工作流程对比

### 旧流程（5 步）

```bash
# 1. 批量扫描
python3 tools/batch_diagnose_images.py

# 2. 生成列表
python3 tools/generate_redownload_list.py

# 3. 预览删除
python3 tools/selective_redownload.py --dry-run

# 4. 执行删除
python3 tools/selective_redownload.py

# 5. 重新下载
python3 tools/wiznote_downloader.py
```

### 新流程（2 步）

```bash
# 1. 一键修复
python3 tools/fix_missing_resources.py

# 2. 重新下载
python3 tools/wiznote_downloader.py
```

---

## 💡 关键说明

### wiznote_downloader.py 的跳过逻辑

**简单来说**：只要 `.md` 文件存在，就会跳过整个笔记

```python
# 代码第 502 行
if md_file_path.exists():
    return {"status": "skip", "title": safe_title}
```

**所以需要**：
1. ✅ 先删除有问题的 `.md` 文件
2. ✅ 然后运行 wiznote_downloader.py 重新下载

---

## 🚨 常见问题

### Q1: 删除 .md 文件会丢失笔记吗？

**A**: ❌ 不会。笔记内容存储在 WizNote 云端，删除只是触发重新下载机制。

---

### Q2: 能否只修复图片，不修复附件？

**A**: ❌ 不支持。工具同时检查图片和附件，统一修复。

---

### Q3: 如果重新下载仍然失败怎么办？

**A**: 使用离线导出方式（最可靠）：

```bash
# 1. 在 WizNote 客户端中导出笔记
#    - 文件 → 导出 → Markdown 格式
#    - 导出到 ~/wiznote_export

# 2. 使用迁移工具处理
export WIZNOTE_SOURCE_DIR=~/wiznote_export
python3 tools/wiznote_to_obsidian.py --all
```

---

## 📚 相关工具

保留的独立工具（高级用户）：

- `batch_diagnose_images.py` - 只扫描
- `generate_redownload_list.py` - 只生成列表
- `selective_redownload.py` - 只删除文件

**大多数用户只需要**：
- `fix_missing_resources.py` - 一键修复
- `wiznote_downloader.py` - 重新下载

---

**更新时间**：2026-02-26
**工具版本**：v1.2.0
