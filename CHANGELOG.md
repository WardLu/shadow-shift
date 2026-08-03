# 更新日志

本文档记录 WizNote to Obsidian 项目的所有重要更改。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

> **版本说明**：主仓库（开源工具）和 `app/` 子模块（商业应用）使用独立版本线。
> 主仓库版本：v1.0.0 → v1.1.0 → v1.2.0 → v1.2.1
> app/ 子模块变更记录见 `app/CHANGELOG.md`

---

## [1.2.1] - 2026-08-03

### 修复

- 🐛 修复登录失败后仍继续扫描目录的问题，避免请求 `None/ks/...` 无效地址。
- 🐛 校验知识库 API 地址，拒绝无效值并保留默认地址回退。
- 🐛 修复格式化工具源目录不存在时直接抛出 Python 堆栈的问题。

### 改进

- 🔧 `obsidian_formatter.py` 新增 `--source` 和 `--target` 参数。
- 📝 补充二次登录验证和路径错误的故障排查说明。
- ✅ 增加登录流程和路径处理的回归测试。

---

## [1.2.0] - 2026-06-03

### 新增

#### 仓库维护工具

- 📦 **`consolidate_attachments.py`** — 散落资源整合工具
  - 将 `*_files`、`attachments`、`images` 等散落目录统一到顶层 `attachments/`
  - 三种模式：`scan`（扫描）、`dry-run`（预览）、`migrate`（执行）
  - 自动更新 Markdown 中的引用路径（支持 `![]()` 和 `[[]]` 语法）
  - 配置化：资源目录名和后缀可通过 `config.json` 的 `cleanup` 节点自定义

- 🧹 **`vault_cleaner.py`** — 仓库清理工具（五种模式）
  - `fix`：修复失效引用，将孤儿文件重新链接到笔记
  - `fuzzy`：检测近似重复笔记（按标题+纯文本比对，显示相似度百分比）
  - `dedup`：按内容哈希去重，自动更新引用
  - `orphan`：检测孤儿文件，预览时列出文件详情
  - `clean`：检测并清理空笔记、空目录，支持 `--fix-untitled` 清理「无标题」占位符
  - `--threshold`：自定义近似重复相似度阈值
  - 模板保护：文件名含 `template`/`模板`/`tpl` 的笔记不会被删除
  - 默认排除 `.pdf`、`.xls`、`.xlsx`、`.xmind`
  - 配置化：资源目录名、排除扩展名、模板保护关键词可通过 `config.json` 自定义

#### 配置扩展

- `config.example.json` 新增 `cleanup` 配置节
  - `resource_dir_names`：资源目录名列表
  - `resource_dir_suffixes`：资源目录后缀列表
  - `exclude_extensions`：孤儿检测默认排除的扩展名
  - `protected_filenames`：fuzzy 模式保护的文件名关键词

### 改进

- 🔧 所有工具脚本移除硬编码个人路径，改用 argparse 命令行参数
- 📝 工具文档按使用场景分类：迁移工具、迁移检查、仓库维护
- 📝 新增 `QUICK_REFERENCE.md` 快速参考指南
- 📝 `tools/README.md` 补充辅助工具完整说明

### 修复

- 🐛 修复 `obsidian_health_check.py` 默认路径硬编码为个人目录的问题
- 🐛 修复 fuzzy 模式代码块内容被错误删除导致相似度计算不准的问题
- 🐛 修复 fuzzy 模式 title 带 `.md` 后缀导致同标题笔记不匹配的问题
- 🐛 修复去重后引用更新逻辑未处理不同文件名场景的问题
- 🐛 修复孤儿检测仅按文件名匹配导致同名不同路径误判的问题

---

## [1.1.0] - 2026-02-16

### 新增功能

- ✅ **协作笔记支持** - 通过 ShareJS 协议自动获取协作笔记内容
  - 实现完整的 WebSocket 握手协议（3次 hs + 认证）
  - 自动获取协作笔记内容（fetch + 双次接收）
  - 转换 ShareJS 格式为标准 Markdown
  - 支持所有 block 类型（text、list、code、table、embed）
  - 支持评论系统、数学公式、流程图等高级功能

- ✅ **协作笔记解析器** (`tools/collaboration_note_parser.py`)
  - 450+ 行完整实现
  - 策略模式处理不同的 block 类型
  - 完整的 Markdown 转换支持

- ✅ **附件集中管理** - `--all` 参数可选执行附件迁移
  - 附件复制到 `attachments/` 目录
  - 自动添加附件链接

- ✅ **安全输出目录** - 格式化输出到 `wiznote_obsidian/`
  - 原始 `wiznote_download/` 保持不变
  - 避免修改源数据

### 性能提升

- ⚡ 协作笔记成功率：0% → 100%（25/25）
- ⚡ 总体成功率：94% → 99.6%（447/449）
- ⚡ 并发下载：3 线程，2分20秒完成 449 个笔记

### 改进

- 🔧 修复登录逻辑（支持两种 returnCode 格式）
- 🔧 添加 user_guid 保存（WebSocket 认证需要）
- 🔧 优化 Markdown 处理（协作笔记直接保存）
- 🔧 改进错误提示和调试输出
- 🔧 简化命令：默认执行基础5步，`--all` 执行完整7步

### 文档更新

- 📝 整合所有文档到 README.md
- 📝 更新工具说明
- 📝 添加使用场景和常见问题

### 实际测试结果

```
测试环境：真实 WizNote 账号
笔记总数：449 个
成功下载：447 个（99.6%）
图片：7198 张（100%）
附件：30 个（100%）
协作笔记：25 个（100%）
总耗时：2 分 20 秒
```

### 参考实现

感谢 [awaken233/wiz2obsidian](https://github.com/awaken233/wiz2obsidian) 项目提供的 ShareJS 协议参考实现。

---

## [1.0.0] - 2026-01-27

### 首次发布

- ✅ 在线下载工具（`wiznote_downloader.py`）
- ✅ 离线格式化工具（`obsidian_formatter.py`）
- ✅ HTML → Markdown 转换
- ✅ 图片自动下载
- ✅ 附件自动下载
- ✅ WikiLinks 链接转换
- ✅ 语法检查和格式修复
- ✅ 同步删除工具
- ✅ 附件迁移工具
