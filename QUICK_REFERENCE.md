# 工具快速参考指南

> **版本**: v1.2.1 | **更新日期**: 2026-08-03

## 🚀 快速开始

### 新手推荐
```bash
# 1. 下载笔记（如果还没有）
python3 tools/wiznote_downloader.py

# 2. 智能迁移（推荐）
python3 tools/smart_migrate_to_obsidian.py
```

### 检查附件
```bash
# 1. 扫描 WikiLink
python3 tools/scan_wikilinks.py

# 2. 健康检查（含附件完整性）
python3 tools/obsidian_health_check.py
```

## 📋 工具速查表

### 迁移工具（WizNote → Obsidian）

| 场景 | 使用工具 | 命令 |
|------|---------|------|
| 从云端下载 | wiznote_downloader | `python3 tools/wiznote_downloader.py` |
| 智能迁移 | smart_migrate | `python3 tools/smart_migrate_to_obsidian.py` |
| 格式化 | obsidian_formatter | `python3 tools/obsidian_formatter.py` |
| 修复源文件 | fix_wiznote_source_files | `python3 tools/fix_wiznote_source_files.py` |
| 整合缺失附件 | integrate_missing_attachments | `python3 tools/integrate_missing_attachments.py` |

### 仓库维护工具（Obsidian 日常清理）

> vault_cleaner.py 支持五种模式：`fix`（引用修复）、`fuzzy`（近似重复）、`dedup`（去重）、`orphan`（孤儿文件）、`clean`（空内容清理）

| 场景 | 使用工具 | 命令 |
|------|---------|------|
| 整合散落资源 | consolidate_attachments | `python3 tools/consolidate_attachments.py scan /path/to/vault` |
| 去重删除 | vault_cleaner | `python3 tools/vault_cleaner.py dedup /path/to/vault` |
| 近似重复笔记 | vault_cleaner | `python3 tools/vault_cleaner.py fuzzy /path/to/vault` |
| 空笔记/空目录 | vault_cleaner | `python3 tools/vault_cleaner.py clean /path/to/vault` |
| 孤儿文件检测 | vault_cleaner | `python3 tools/vault_cleaner.py orphan /path/to/vault` |
| 修复失效引用 | vault_cleaner | `python3 tools/vault_cleaner.py fix /path/to/vault` |
| 健康检查 | obsidian_health_check | `python3 tools/obsidian_health_check.py` |
| 扫描 WikiLink | scan_wikilinks | `python3 tools/scan_wikilinks.py` |
| 同步删除 | sync_deletions | `python3 tools/sync_deletions.py --scan` |

## 🎯 常见任务

### 任务 1：首次迁移
```bash
python3 tools/wiznote_downloader.py
python3 tools/smart_migrate_to_obsidian.py
```

### 任务 2：修复附件丢失
```bash
python3 tools/scan_wikilinks.py
python3 tools/obsidian_health_check.py
python3 tools/smart_migrate_to_obsidian.py
```

### 任务 3：检查完整性
```bash
python3 tools/scan_wikilinks.py
python3 tools/obsidian_health_check.py
```

### 任务 4：清理仓库

**推荐流程**：`fix` → `fuzzy` → `dedup` → `orphan` → `clean`

```bash
# 1. 整合散落资源
python3 tools/consolidate_attachments.py scan /path/to/vault
python3 tools/consolidate_attachments.py migrate /path/to/vault

# 2. 修复失效引用
python3 tools/vault_cleaner.py fix /path/to/vault --apply

# 3. 清理近似重复笔记（带引用重定向，默认阈值 0.8）
python3 tools/vault_cleaner.py fuzzy /path/to/vault --apply
# 降低阈值检测更多（如账号密码类笔记内容少，需降低阈值）
python3 tools/vault_cleaner.py fuzzy /path/to/vault --threshold 0.25 --apply

# 4. 去重
python3 tools/vault_cleaner.py dedup /path/to/vault --apply

# 5. 再修一次（去重可能产生新失效引用）
python3 tools/vault_cleaner.py fix /path/to/vault --apply

# 6. 清理孤儿文件（默认排除 .pdf .xls .xlsx .xmind）
python3 tools/vault_cleaner.py orphan /path/to/vault --apply

# 7. 清理空笔记、空目录、「无标题」占位符
python3 tools/vault_cleaner.py clean /path/to/vault --fix-untitled --apply
```

**fuzzy 模式说明**：
- 文件名含 `template`/`模板`/`tpl` 的笔记自动保护，不会被删除
- `--threshold` 调整相似度阈值（默认 0.8）
- `--fix-untitled` 清理 WizNote 导出的「无标题」占位符

## 🔍 故障排除

### 问题：附件找不到
**解决**：
```bash
python3 tools/smart_migrate_to_obsidian.py
```

### 问题：图片缺失
**解决**：
```bash
python3 tools/smart_migrate_to_obsidian.py
```

### 问题：WikiLink 没有转换
**解决**：
```bash
python3 tools/smart_migrate_to_obsidian.py
```

## 📚 详细文档

- [完整工具说明](./tools/README.md)
- [文档索引](./DOCUMENTATION_INDEX.md)
- [归档工具说明](./tools/archive/README.md)

## 🔧 辅助工具

### 迁移辅助

| 场景 | 工具 | 命令 |
|------|------|------|
| 手动迁移特定笔记 | migrate_manual_notes | `python3 tools/migrate_manual_notes.py` |
| 重新迁移单个笔记 | remigrate_single_note | `python3 tools/remigrate_single_note.py` |
| 移动笔记到正确路径 | move_note_to_correct_path | `python3 tools/move_note_to_correct_path.py` |

### 迁移检查

| 场景 | 工具 | 命令 |
|------|------|------|
| 附件迁移完整性检查 | check_attachment_migration | `python3 tools/check_attachment_migration.py` |
| 附件迁移检查（修复版） | check_attachment_migration_fixed | `python3 tools/check_attachment_migration_fixed.py` |
| 附件完整性最终检查 | check_attachments_final | `python3 tools/check_attachments_final.py` |
| 迁移结果对比 | compare_migration | `python3 tools/compare_migration.py` |
| 缺失笔记诊断 | diagnose_missing_notes | `python3 tools/diagnose_missing_notes.py` |

## 💡 最佳实践

1. **首次迁移**：使用 `smart_migrate_to_obsidian.py`
2. **定期检查**：使用 `scan_wikilinks.py` 和 `obsidian_health_check.py`
3. **发现问题**：重新运行 `smart_migrate_to_obsidian.py`

## 🆘 获取帮助

```bash
# 查看工具帮助
python3 tools/smart_migrate_to_obsidian.py --help
python3 tools/wiznote_downloader.py --help

# 查看文档
cat tools/README.md
```

## 🎓 学习路径

### 新手
1. 阅读 `tools/README.md`
2. 运行 `wiznote_downloader.py`
3. 运行 `smart_migrate_to_obsidian.py`

### 中级
1. 使用 `scan_wikilinks.py` 了解 WikiLink
2. 使用 `obsidian_health_check.py` 检查完整性
3. 根据需要调整配置

### 高级
1. 自定义配置文件
2. 使用环境变量
3. 查看源码了解实现
