# 归档说明 (v20260228)

**归档日期**: 2026-02-28
**归档原因**: 工具整合，清理过时脚本

## 📦 归档内容

### 1. check_duplicate_content.py
- **原功能**: 检测 Obsidian 仓库中的重复内容
- **归档原因**: 功能已被 `obsidian_health_check.py` 整合
- **替代工具**: `tools/obsidian_health_check.py`

### 2. check_obsidian_attachments.py
- **原功能**: 检查 WikiLink 链接的文件是否存在
- **归档原因**: 功能已被 `obsidian_health_check.py` 整合
- **替代工具**: `tools/obsidian_health_check.py`

## 🔄 迁移指南

如果您需要使用归档工具的功能，请使用新的整合工具：

```bash
# 旧方式（已归档）
python3 tools/check_duplicate_content.py
python3 tools/check_obsidian_attachments.py

# 新方式（推荐）
python3 tools/obsidian_health_check.py
```

## ⚠️ 注意

这些脚本已不再维护，仅作为历史记录保留。如需使用相关功能，请使用新的整合工具。
