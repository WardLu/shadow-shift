#!/usr/bin/env python3
"""
WizNote 笔记重新下载/导出工具

功能：
1. 读取 redownload_list.txt 中的笔记列表
2. 批量从 WizNote 客户端导出（包含图片）
3. 或使用 WizNote API 重新下载
4. 更新到 Obsidian
"""

from pathlib import Path
import re
import json
from datetime import datetime
import shutil

class WizNoteRedownloader:
    def __init__(self):
        self.project_path = Path('/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian')
        self.redownload_list = self.project_path / 'redownload_list.txt'
        self.wiznote_download = self.project_path / 'wiznote_download'
        self.obsidian_vault = self._find_obsidian_vault()
        self.report = []

    def _find_obsidian_vault(self):
        """查找 Obsidian 仓库"""
        docs_path = Path('/Users/wardlu/Documents')
        for item in docs_path.iterdir():
            if item.is_dir() and 'obsidian' in item.name.lower() and '副本' not in item.name:
                return item
        return None

    def parse_redownload_list(self):
        """解析需要重新下载的列表"""
        notes = []

        with open(self.redownload_list, 'r', encoding='utf-8') as f:
            for line in f:
                # 格式: 文件路径 (缺失数)
                match = re.match(r'(.+\.md)\s*\((\d+) 个?\)', line.strip())
                if match:
                    notes.append({
                        'path': match.group(1).strip(),
                        'missing_count': int(match.group(2))
                    })

        return notes

    def find_in_wiznote(self, note_path):
        """在 WizNote 下载目录中查找笔记"""
        for md in self.wiznote_download.rglob('*.md'):
            if note_path in str(md) or md.name in note_path:
                return md
        return None

    def find_in_obsidian(self, note_name):
        """在 Obsidian 仓库中查找笔记"""
        for md in self.obsidian_vault.rglob('*.md'):
            if md.name == note_name:
                return md
        return None

    def check_wiznote_client(self):
        """检查 WizNote 客户端是否可用"""
        # 检查常见的 WizNote 数据目录
        possible_paths = [
            Path.home() / 'Library' / 'Application Support' / 'wiznote',
            Path.home() / '.wiznote',
            Path('/Applications/WizNote.app'),
        ]

        found = []
        for path in possible_paths:
            if path.exists():
                found.append(path)

        return found

    def analyze_notes(self):
        """分析需要重新下载的笔记"""
        print("=" * 60)
        print("WizNote 笔记重新下载分析")
        print("=" * 60)
        print()

        # 解析列表
        notes = self.parse_redownload_list()
        print(f"📋 需要处理的笔记: {len(notes)} 个")
        print(f"📊 总缺失资源: {sum(n['missing_count'] for n in notes)} 个\n")

        # 分类统计
        high_priority = [n for n in notes if n['missing_count'] >= 10]
        medium_priority = [n for n in notes if 5 <= n['missing_count'] < 10]
        low_priority = [n for n in notes if n['missing_count'] < 5]

        print("📊 优先级分类:")
        print(f"  🔴 高优先级 (≥10): {len(high_priority)} 个笔记")
        print(f"  🟡 中优先级 (5-9): {len(medium_priority)} 个笔记")
        print(f"  🟢 低优先级 (<5): {len(low_priority)} 个笔记\n")

        # 显示高优先级笔记
        if high_priority:
            print("=" * 60)
            print("🔴 高优先级笔记（建议优先处理）:")
            print("=" * 60)
            for idx, note in enumerate(high_priority, 1):
                print(f"{idx}. {note['path']}")
                print(f"   缺失: {note['missing_count']} 个")

        # 检查 WizNote 客户端
        print("\n" + "=" * 60)
        print("🔍 检测 WizNote 环境")
        print("=" * 60)

        wiznote_paths = self.check_wiznote_client()
        if wiznote_paths:
            print("✅ 找到 WizNote 相关路径:")
            for path in wiznote_paths:
                print(f"  - {path}")
        else:
            print("❌ 未找到 WizNote 客户端或数据目录")

        # 生成处理方案
        print("\n" + "=" * 60)
        print("💡 处理方案")
        print("=" * 60)
        print("""
方案 1: 使用 WizNote 客户端批量导出（推荐）
----------------------------------------
优点:
  - 可以保留完整的图片和格式
  - 官方支持，稳定可靠

步骤:
  1. 打开 WizNote 客户端
  2. 找到这些笔记（按优先级排序）
  3. 批量选择并导出为 Markdown
  4. 重新运行迁移脚本


方案 2: 使用 WizNote API（需要账号）
----------------------------------------
优点:
  - 自动化程度高
  - 可以批量处理

步骤:
  1. 获取 WizNote API Token
  2. 运行自动下载脚本
  3. 更新到 Obsidian


方案 3: 手动处理重要笔记
----------------------------------------
适用场景:
  - 只关心高优先级的笔记
  - 其他笔记可以忽略

步骤:
  1. 只处理缺失 ≥10 个资源的笔记
  2. 从 WizNote 手动导出
  3. 在 Obsidian 中更新
""")

    def generate_wiznote_selection_list(self):
        """生成 WizNote 选择列表（方便在客户端中查找）"""
        notes = self.parse_redownload_list()

        output = self.project_path / 'wiznote_selection_list.txt'

        with open(output, 'w', encoding='utf-8') as f:
            f.write('WizNote 笔记选择列表\n')
            f.write('=' * 60 + '\n\n')
            f.write('在 WizNote 客户端中搜索以下标题进行批量导出:\n\n')

            # 按优先级分组
            high = [n for n in notes if n['missing_count'] >= 10]
            medium = [n for n in notes if 5 <= n['missing_count'] < 10]
            low = [n for n in notes if n['missing_count'] < 5]

            f.write(f'总计: {len(notes)} 个笔记\n\n')

            if high:
                f.write('## 🔴 高优先级（缺失 ≥10）\n\n')
                for n in high:
                    # 提取笔记名称
                    name = Path(n['path']).stem
                    f.write(f'{name}\n')
                f.write('\n')

            if medium:
                f.write('## 🟡 中优先级（缺失 5-9）\n\n')
                for n in medium:
                    name = Path(n['path']).stem
                    f.write(f'{name}\n')
                f.write('\n')

            if low:
                f.write('## 🟢 低优先级（缺失 <5）\n\n')
                for n in low:
                    name = Path(n['path']).stem
                    f.write(f'{name}\n')
                f.write('\n')

        print(f'✅ 选择列表已生成: {output}')
        return output

    def generate_export_instructions(self):
        """生成详细的导出指导"""
        output = self.project_path / 'wiznote_export_guide.md'

        content = '''# WizNote 批量导出指导

## 📋 概述

- **需要导出的笔记**: 51 个
- **缺失图片**: 340 张
- **缺失附件**: 1 个

## 🔧 导出步骤

### 方法 1: 使用 WizNote 桌面客户端（推荐）

#### 步骤 1: 批量选择笔记

1. 打开 WizNote 客户端
2. 使用搜索功能，按标题搜索（参考 `wiznote_selection_list.txt`）
3. 按住 Cmd/Ctrl 多选笔记

#### 步骤 2: 导出为 Markdown

1. 右键点击选中的笔记
2. 选择 "导出" → "Markdown"
3. 选择导出位置（建议创建新文件夹）
4. 勾选 "包含图片" 选项
5. 开始导出

#### 步骤 3: 重新迁移

导出完成后：

```bash
# 将新导出的文件复制到项目目录
cp -r /path/to/export/* /Users/wardlu/Documents/VibeCoding/Wiznote\ to\ Obisidian/wiznote_download/

# 重新运行迁移脚本
cd /Users/wardlu/Documents/VibeCoding/Wiznote\ to\ Obisidian
python3 tools/migrate_to_obsidian.py
```

### 方法 2: 分批导出（推荐用于大量笔记）

#### 第一批：高优先级（11 个）

缺失 ≥10 个资源的笔记：

1. 银行股评级（2017.7-2018.12） - 集思录
2. 智能制造MES拆解
3. 人人都是开发者——无代码产品轻流CPO严琦东Joseph Yan
4. 产品年度规划怎么做
5. 2022年下半年小棉猫产品路线图
6. ToB老人家 SaaS拆解系列——第二讲：Oracle多组织架构
7. 微信公众号模板消息
8. 2023年下半年小棉猫产品路线图
9. 穿得不好看，谁还想看你不穿衣服的样子？
10. 抵制处女情结，从我做起｜这5类二手物品让你甘做接盘侠
11. 2024年上半年小棉猫产品路线图

#### 第二批：中优先级（11 个）

缺失 5-9 个资源的笔记

#### 第三批：低优先级（29 个）

缺失 <5 个资源的笔记（可以考虑跳过）

## ✅ 验证导出完整性

导出后，检查每个笔记的图片：

```bash
# 检查图片文件数量
find /path/to/export -name "*.png" -o -name "*.jpg" | wc -l

# 应该至少有 340 个图片文件
```

## 🔄 重新迁移

导出完成后，运行迁移脚本更新 Obsidian：

```bash
cd /Users/wardlu/Documents/VibeCoding/Wiznote\ to\ Obisidian

# 重新运行迁移
python3 tools/migrate_to_obsidian.py

# 检查结果
python3 tools/check_obsidian_resources.py
```

## 📝 注意事项

1. **备份**: 导出前建议备份现有 Obsidian 仓库
2. **增量更新**: 可以只导出高优先级笔记，避免全量覆盖
3. **图片验证**: 导出后检查图片是否完整
4. **冲突处理**: 如果笔记已存在，可以选择覆盖或合并

---

*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
'''

        output.write_text(content, encoding='utf-8')
        print(f'✅ 导出指导已生成: {output}')
        return output

def main():
    print("\n" + "=" * 60)
    print("WizNote 笔记重新下载工具")
    print("=" * 60 + "\n")

    tool = WizNoteRedownloader()

    # 分析笔记
    tool.analyze_notes()

    # 生成辅助文件
    print("\n" + "=" * 60)
    print("生成辅助文件")
    print("=" * 60 + "\n")

    tool.generate_wiznote_selection_list()
    tool.generate_export_instructions()

    print("\n✅ 分析完成！")
    print("\n下一步:")
    print("1. 查看 wiznote_selection_list.txt - 笔记列表")
    print("2. 查看 wiznote_export_guide.md - 详细导出指导")
    print("3. 按照指导在 WizNote 客户端中导出笔记")
    print()

if __name__ == '__main__':
    main()
