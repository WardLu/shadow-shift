# 图片诊断工具集 - 使用说明更新日志

> 更新时间：2026-02-26

## 📋 更新内容

### 1. 统一了所有工具的使用说明格式

所有诊断工具现在都包含：

#### ✅ 详细的文档字符串（docstring）

每个脚本开头都包含：
- **功能描述** - 工具的主要功能
- **使用方法** - 常见的使用示例
- **输出说明** - 生成的文件和内容
- **示例** - 实际运行的输出示例

#### ✅ argparse 参数支持

所有工具现在都支持：
- `-h, --help` - 显示详细的帮助信息
- 命令行参数 - 支持非交互式使用
- 使用示例 - 在帮助信息中显示常见用法
- 输出文件说明 - 明确告知生成的文件

#### ✅ 一致的用户体验

- 统一的帮助信息格式
- 统一的输出格式
- 统一的错误提示
- 统一的成功提示

---

### 2. 创建的工具文档

#### 📖 IMAGE_DIAGNOSIS_TOOLS.md

**内容**：
- 完整的工具集概览
- 每个工具的详细说明
- 参数说明表格
- 输出示例
- 常见问题解答
- 工作流程建议

**特点**：
- 清晰的目录结构
- 丰富的使用示例
- 详细的参数说明
- 问题排查指南

#### 📖 tools/README.md 更新

**新增内容**：
- 图片诊断工具章节
- 工具对比表格
- 快速开始指南
- 常见用法示例

---

### 3. 工具改进详情

#### batch_diagnose_images.py

**新增功能**：
- ✅ `--download-dir, -d` - 指定下载目录
- ✅ `--severe-only, -s` - 只显示严重问题
- ✅ 详细的帮助信息和使用示例

**改进**：
- 报告文件路径跟随下载目录
- 更清晰的输出格式

#### diagnose_image_download.py

**新增功能**：
- ✅ `--note, -n` - 直接指定笔记标题（非交互式）
- ✅ `--save-debug` - 保存完整的 API 响应
- ✅ 详细的帮助信息和使用示例

**改进**：
- 支持命令行参数和交互式两种模式
- 更清晰的诊断步骤输出

#### generate_redownload_list.py

**新增功能**：
- ✅ `--report, -r` - 指定报告文件路径
- ✅ `--severe-threshold, -t` - 自定义严重问题阈值
- ✅ 详细的帮助信息和使用示例

**改进**：
- 完全重构为函数式结构
- 支持命令行参数
- 更灵活的配置选项

---

## 🎯 使用示例

### 查看帮助信息

```bash
# 所有工具都支持 --help
python3 tools/batch_diagnose_images.py --help
python3 tools/diagnose_image_download.py --help
python3 tools/generate_redownload_list.py --help
```

### 完整诊断流程

```bash
# 1. 批量扫描（只看严重问题）
python3 tools/batch_diagnose_images.py --severe-only

# 2. 生成重新下载列表（自定义阈值）
python3 tools/generate_redownload_list.py --severe-threshold 5

# 3. 诊断特定笔记（保存调试信息）
python3 tools/diagnose_image_download.py \
  --note "智能制造MES拆解" \
  --save-debug
```

### 非交互式使用

```bash
# 适合脚本化操作
python3 tools/batch_diagnose_images.py --download-dir ~/wiznote --severe-only > severe_issues.txt
python3 tools/generate_redownload_list.py --report missing_images_report.txt
```

---

## 📊 工具对比

### 改进前

```bash
# batch_diagnose_images.py
python3 tools/batch_diagnose_images.py  # 只有这一种用法

# diagnose_image_download.py
python3 tools/diagnose_image_download.py  # 必须交互式输入

# generate_redownload_list.py
python3 tools/generate_redownload_list.py  # 固定配置
```

### 改进后

```bash
# batch_diagnose_images.py
python3 tools/batch_diagnose_images.py --help
python3 tools/batch_diagnose_images.py --download-dir ~/my_dir
python3 tools/batch_diagnose_images.py --severe-only

# diagnose_image_download.py
python3 tools/diagnose_image_download.py --help
python3 tools/diagnose_image_download.py --note "笔记标题"
python3 tools/diagnose_image_download.py --note "笔记标题" --save-debug

# generate_redownload_list.py
python3 tools/generate_redownload_list.py --help
python3 tools/generate_redownload_list.py --report ~/report.txt
python3 tools/generate_redownload_list.py --severe-threshold 5
```

---

## 📁 文件清单

### 新增文件

```
tools/
├── IMAGE_DIAGNOSIS_TOOLS.md       📖 图片诊断工具完整文档
└── diagnose_image_download.py     🔍 单个笔记诊断工具（重构）
```

### 更新文件

```
tools/
├── batch_diagnose_images.py       ✨ 添加 argparse 支持
├── diagnose_image_download.py     ✨ 添加 argparse 支持
├── generate_redownload_list.py    ✨ 重构为函数式结构
└── README.md                      ✨ 添加图片诊断工具章节
```

---

## ✅ 验证清单

- [x] 所有工具支持 `--help` 参数
- [x] 所有工具有详细的文档字符串
- [x] 所有工具支持命令行参数
- [x] 帮助信息包含使用示例
- [x] 帮助信息包含输出文件说明
- [x] 创建了完整的工具文档
- [x] 更新了主 README
- [x] 测试所有工具能正常运行

---

## 🎓 学习路径

### 新手用户

1. 阅读 `tools/README.md` 了解工具概览
2. 运行 `batch_diagnose_images.py` 扫描问题
3. 查看生成的报告文件
4. 根据提示处理问题

### 高级用户

1. 阅读 `IMAGE_DIAGNOSIS_TOOLS.md` 了解详细功能
2. 使用命令行参数定制诊断流程
3. 结合其他工具（wiznote_downloader.py, obsidian_formatter.py）完整处理
4. 自动化批量处理流程

---

## 🔄 后续改进建议

### 可能的增强功能

1. **批量诊断报告**
   - 生成 HTML 格式的报告
   - 包含图表和统计信息
   - 支持导出为 PDF

2. **自动化修复**
   - 自动重试下载失败的图片
   - 自动修复常见的链接问题
   - 批量更新图片路径

3. **集成测试**
   - 添加单元测试
   - 添加集成测试
   - CI/CD 支持

4. **性能优化**
   - 并行处理多个笔记
   - 缓存 API 响应
   - 增量扫描

---

## 📝 总结

### 改进成果

✅ **统一性** - 所有工具现在有一致的使用体验
✅ **可用性** - 详细的帮助信息和使用示例
✅ **灵活性** - 支持命令行参数和交互式两种模式
✅ **文档化** - 完整的工具文档和常见问题解答

### 用户受益

- 📖 **更容易学习** - 清晰的文档和示例
- 🚀 **更高效使用** - 命令行参数支持自动化
- 🔍 **更深入诊断** - 保存调试信息用于分析
- 💡 **更好的体验** - 统一的输出格式和错误提示

---

**更新完成时间**：2026-02-26
**验证状态**：✅ 所有功能已测试通过
