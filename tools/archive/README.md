# 归档工具

本目录包含已归档的工具，这些工具的功能已整合到主工具中或已被更先进的工具取代。

## 📁 目录结构

```
archive/
├── v20260228/          # 2026-02-28 归档（功能已整合到 obsidian_health_check.py）
├── diagnosis/          # 诊断工具（已被 scan_wikilinks.py 取代）
├── legacy_fixes/       # 过时的修复工具（已被 smart_migrate_to_obsidian.py 取代）
├── legacy_migration/   # 过时的迁移工具（功能已整合）
└── pdf_converters/     # PDF 转换工具（功能已整合）
```

## ⚠️ 重要说明

- **这些工具已不再维护**
- **功能已整合到主工具中**
- **保留这些工具是为了历史记录和特殊需求**
- **推荐使用主目录中的新工具**

## 📂 各目录说明

### v20260228/ - 2026-02-28 归档

**包含工具**：
- `check_duplicate_content.py` - 重复内容检查（已整合到 `obsidian_health_check.py`）
- `check_obsidian_attachments.py` - 附件检查（已整合到 `obsidian_health_check.py`）

**替代工具**：
- `tools/obsidian_health_check.py` - 健康检查工具（整合版）

**为什么归档**：
- 功能已整合到 `obsidian_health_check.py`
- 新工具提供更全面的健康检查

### diagnosis/ - 诊断工具

**包含工具**：
- `batch_diagnose_images.py` - 批量诊断图片
- `diagnose_image_download.py` - 诊断单个笔记
- `diagnose_image_issue.py` - 诊断图片问题
- `diagnose_image_loss.py` - 诊断图片丢失
- `deep_api_diagnosis.py` - API 诊断
- `generate_redownload_list.py` - 生成重下载列表

**替代工具**：
- `tools/scan_wikilinks.py` - 扫描 WikiLink 链接
- `tools/check_obsidian_attachments.py` - 检查附件完整性

**为什么归档**：
- 功能已被新工具取代
- 新工具支持 WikiLink 格式
- 新工具有更好的报告功能

### legacy_fixes/ - 过时的修复工具

**包含工具**：
- `batch_fix_missing_images.py` - 批量修复图片
- `fix_broken_images.py` - 修复损坏图片
- `fix_missing_resources.py` - 修复缺失资源
- `fix_obsidian_resources.py` - 修复资源
- `restore_missing_images.py` - 恢复缺失图片

**替代工具**：
- `tools/smart_migrate_to_obsidian.py` - 智能迁移工具

**为什么归档**：
- 功能已整合到智能迁移工具
- 新工具更智能，自动检测并修复
- 不需要单独运行修复工具

### legacy_migration/ - 过时的迁移工具

**包含工具**：
- `migrate_attachments.py` - 附件迁移
- `link_attachments.py` - 附件链接
- `process_wiznote_export.py` - 处理导出
- `redownload_notes.py` - 重新下载
- `selective_redownload.py` - 选择性重下载
- `download_images_from_html.py` - 从 HTML 下载图片
- `extract_image_urls.py` - 提取图片 URL
- `check_migration.py` - 检查迁移
- `verify_images.py` - 验证图片
- `check_obsidian_resources.py` - 检查资源
- `collaboration_note_parser.py` - 协作笔记解析
- `generate_accurate_report.py` - 生成报告
- `convert_wikilinks_to_markdown.py` - 转换 WikiLink

**替代工具**：
- `tools/smart_migrate_to_obsidian.py` - 智能迁移工具
- `tools/wiznote_downloader.py` - 在线下载工具

**为什么归档**：
- 功能已整合到主工具
- 新工具更智能、更高效
- 不需要单独运行多个工具

### pdf_converters/ - PDF 转换工具

**包含工具**：
- `convert_pdf_simple.py` - 简单 PDF 转换
- `convert_pdf_with_images.py` - 带图片转换
- `pdf_to_markdown.py` - PDF 转 Markdown

**替代工具**：
- `tools/wiznote_downloader.py` - 在线下载工具（内置 PDF 支持）

**为什么归档**：
- PDF 转换功能已整合到下载工具
- 不需要单独转换

## 🔧 如何使用归档工具

如果你确实需要使用归档工具（不推荐）：

```bash
# 直接运行归档工具
python3 tools/archive/diagnosis/batch_diagnose_images.py

# 或移动到主目录后运行
cp tools/archive/diagnosis/batch_diagnose_images.py tools/
python3 tools/batch_diagnose_images.py
```

## 📊 工具迁移对照表

| 归档工具 | 替代工具 | 说明 |
|---------|---------|------|
| `batch_diagnose_images.py` | `scan_wikilinks.py` | 更智能的扫描工具 |
| `diagnose_image_*.py` | `check_obsidian_attachments.py` | 更准确的检查工具 |
| `fix_*.py` | `smart_migrate_to_obsidian.py` | 自动修复所有问题 |
| `migrate_attachments.py` | `smart_migrate_to_obsidian.py` | 功能已整合 |
| `redownload_notes.py` | `wiznote_downloader.py` | 更强大的下载工具 |
| `convert_wikilinks_to_markdown.py` | `smart_migrate_to_obsidian.py` | 自动转换 WikiLink |
| `pdf_to_markdown.py` | `wiznote_downloader.py` | 内置 PDF 支持 |

## 🗑️ 删除政策

- **短期**：保留所有归档工具（至少 6 个月）
- **中期**：根据使用情况决定是否删除（1 年后）
- **长期**：只保留有历史价值的工具

## 📝 更新记录

### 2026-06-03
- 补充 `v20260228/` 目录说明

### 2026-02-27
- 创建归档目录结构
- 移动 27 个过时工具到归档目录
- 创建归档文档

## 💡 建议

**如果你是新手**：
- 不要使用归档工具
- 使用主目录中的新工具
- 参考 `tools/README.md`

**如果你是高级用户**：
- 归档工具仍然可用
- 但建议迁移到新工具
- 新工具有更好的功能和性能

**如果你遇到问题**：
- 先尝试新工具
- 如果新工具无法解决，再考虑归档工具
- 报告问题，帮助改进新工具

## 📞 获取帮助

- 主文档：`tools/README.md`
- WikiLink 迁移：`docs/WIKILINK_MIGRATION_FIX_REPORT.md`
- 清理分析：`docs/CLEANUP_ANALYSIS_REPORT.md`
