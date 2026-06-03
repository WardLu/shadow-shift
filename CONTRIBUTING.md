# 贡献指南

感谢你考虑为 WizNote to Obsidian 项目做出贡献！

## 🤝 如何贡献

### 报告问题

如果你发现了 bug 或有功能建议：

1. 检查 [Issues](https://github.com/WardLu/wiznote-to-obsidian/issues) 是否已有类似问题
2. 如果没有，创建新的 Issue，包含：
   - 清晰的标题
   - 详细的问题描述
   - 复现步骤
   - 期望行为
   - 实际行为
   - 环境信息（OS、Python 版本等）
   - 相关日志或截图

### 提交代码

#### 1. Fork 项目

点击 GitHub 页面右上角的 "Fork" 按钮

#### 2. 克隆你的 Fork

```bash
git clone https://github.com/WardLu/wiznote-to-obsidian.git
cd wiznote-to-obsidian
```

#### 3. 创建特性分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

分支命名规范：
- `feature/` - 新功能
- `fix/` - Bug 修复
- `docs/` - 文档更新
- `refactor/` - 代码重构
- `test/` - 测试相关
- `chore/` - 构建/工具相关

#### 4. 进行开发

遵循项目的代码风格：
- 使用 4 空格缩进
- 遵循 PEP 8 规范
- 添加必要的注释
- 编写清晰的 commit 信息

#### 5. 测试你的更改

```bash
# 运行主工具
python3 tools/obsidian_formatter.py --help

# 测试具体功能
python3 tools/obsidian_formatter.py --check
```

#### 6. 提交更改

```bash
git add .
git commit -m "feat: 添加某功能描述"
```

Commit 信息规范（使用 Conventional Commits）：
- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档更新
- `style:` - 代码格式（不影响功能）
- `refactor:` - 代码重构
- `test:` - 测试相关
- `chore:` - 构建/工具相关

示例：
```
feat: 添加图片路径自动修复功能
fix: 修复标题层级检测问题
docs: 更新 README 使用说明
```

#### 7. 推送到你的 Fork

```bash
git push origin feature/your-feature-name
```

#### 8. 创建 Pull Request

1. 访问你 Fork 的 GitHub 页面
2. 点击 "New Pull Request"
3. 填写 PR 描述：
   - 清晰的标题
   - 详细描述更改内容
   - 关联相关 Issue（如 `Fixes #123`）
   - 添加截图（如果适用）

## 📋 代码审查标准

### 必须满足

- ✅ 代码符合 PEP 8 规范
- ✅ 添加必要的注释
- ✅ 不引入新的警告或错误
- ✅ 通过现有测试
- ✅ Commit 信息清晰
- ✅ 不破坏现有功能

### 加分项

- ⭐ 添加新测试
- ⭐ 更新相关文档
- ⭐ 性能优化
- ⭐ 改进用户体验

## 🎨 代码风格

### Python 代码

```python
# 好的示例
class MarkdownFixer:
    """Markdown 语法修复器"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.fixes_applied = []

    def fix(self) -> Tuple[List[str], List[str]]:
        """执行所有自动修复"""
        # 实现
        pass
```

### 命名规范

- **类名**: `PascalCase` (如 `MarkdownFixer`)
- **函数/方法**: `snake_case` (如 `fix_format`)
- **常量**: `UPPER_SNAKE_CASE` (如 `MAX_FILES`)
- **变量**: `snake_case` (如 `file_path`)

### 文档字符串

使用 Google 风格：

```python
def fix_markdown(file_path: str) -> bool:
    """修复 Markdown 文件格式

    Args:
        file_path: Markdown 文件路径

    Returns:
        修复是否成功

    Raises:
        FileNotFoundError: 文件不存在
    """
    pass
```

## 🐛 Bug 报告模板

```markdown
### 问题描述
简要描述问题

### 复现步骤
1. 步骤 1
2. 步骤 2
3. 步骤 3

### 期望行为
描述你期望发生什么

### 实际行为
描述实际发生了什么

### 环境信息
- OS: [如 macOS 14.0]
- Python 版本: [如 3.11.0]
- 工具版本: [如 v1.2.0]

### 相关日志
```
粘贴错误日志
```

### 截图
如果适用，添加截图
```

## ✨ 功能请求模板

```markdown
### 功能描述
简要描述你想要的功能

### 使用场景
描述什么情况下需要这个功能

### 期望的实现
描述你希望如何实现

### 替代方案
描述你考虑过的其他解决方案

### 附加信息
其他相关信息或示例
```

## 📚 文档贡献

如果你只想改进文档：

1. 直接编辑 Markdown 文件
2. 预览你的更改
3. 提交 PR
4. 标题使用 `docs:` 前缀

## 🎯 优先级标签

- `priority: critical` - 阻塞使用，需要立即修复
- `priority: high` - 重要功能，需要尽快处理
- `priority: medium` - 常规问题，按计划处理
- `priority: low` - 锦上添花，有空再做

## 📧 联系方式

如有问题：
- 在 [GitHub Issues](https://github.com/WardLu/wiznote-to-obsidian/issues) 中提问
- GitHub: [@WardLu](https://github.com/WardLu)

## 🌟 贡献者

感谢所有贡献者！

<!-- 这里会自动显示贡献者列表 -->

---

**再次感谢你的贡献！** 🎉
