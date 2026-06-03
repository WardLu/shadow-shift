#!/usr/bin/env python3
"""
Obsidian 仓库重复内容检测工具
检测重复的笔记、图片和附件
"""

import os
import hashlib
from pathlib import Path
from collections import defaultdict
import glob

# 自动检测路径
def find_obsidian_vault():
    """自动查找 Obsidian 仓库路径"""
    docs_path = Path("/Users/wardlu/Documents")
    for item in docs_path.iterdir():
        if item.is_dir() and 'obsidian' in item.name.lower() and '副本' not in item.name:
            return item
    raise FileNotFoundError("未找到 Obsidian 仓库")

OBSIDIAN_VAULT_PATH = find_obsidian_vault()
OUTPUT_REPORT = "/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/duplicate_content_report.md"

# 支持的文件类型
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp'}
ATTACHMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar', '.mp3', '.mp4', '.wav'}

class DuplicateChecker:
    def __init__(self, vault_path):
        self.vault_path = Path(vault_path)
        self.duplicates = {
            'notes': {
                'by_name': defaultdict(list),  # 按文件名
                'by_content': defaultdict(list),  # 按内容哈希
                'by_size': defaultdict(list)  # 按文件大小
            },
            'images': {
                'by_name': defaultdict(list),
                'by_hash': defaultdict(list),
                'by_size': defaultdict(list)
            },
            'attachments': {
                'by_name': defaultdict(list),
                'by_hash': defaultdict(list),
                'by_size': defaultdict(list)
            }
        }
        self.stats = {
            'total_notes': 0,
            'total_images': 0,
            'total_attachments': 0,
            'duplicate_notes': 0,
            'duplicate_images': 0,
            'duplicate_attachments': 0
        }

    def get_file_hash(self, file_path, chunk_size=8192):
        """计算文件的 MD5 哈希值"""
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            print(f"计算哈希失败 {file_path}: {e}")
            return None

    def get_file_size(self, file_path):
        """获取文件大小（字节）"""
        try:
            return file_path.stat().st_size
        except Exception as e:
            print(f"获取文件大小失败 {file_path}: {e}")
            return 0

    def scan_notes(self):
        """扫描所有 Markdown 笔记"""
        print("扫描笔记文件...")

        for note_path in self.vault_path.rglob('*.md'):
            # 跳过隐藏目录
            if any(part.startswith('.') for part in note_path.parts):
                continue

            self.stats['total_notes'] += 1
            rel_path = str(note_path.relative_to(self.vault_path))

            # 按文件名分组
            file_name = note_path.name
            self.duplicates['notes']['by_name'][file_name].append(rel_path)

            # 按文件大小分组
            file_size = self.get_file_size(note_path)
            if file_size > 0:
                self.duplicates['notes']['by_size'][file_size].append(rel_path)

            # 按内容哈希分组
            content_hash = self.get_file_hash(note_path)
            if content_hash:
                self.duplicates['notes']['by_content'][content_hash].append(rel_path)

        print(f"  扫描了 {self.stats['total_notes']} 个笔记")

    def scan_images(self):
        """扫描所有图片文件"""
        print("扫描图片文件...")

        for ext in IMAGE_EXTENSIONS:
            for img_path in self.vault_path.rglob(f'*{ext}'):
                # 跳过隐藏目录
                if any(part.startswith('.') for part in img_path.parts):
                    continue

                self.stats['total_images'] += 1
                rel_path = str(img_path.relative_to(self.vault_path))

                # 按文件名分组
                file_name = img_path.name
                self.duplicates['images']['by_name'][file_name].append(rel_path)

                # 按文件大小分组
                file_size = self.get_file_size(img_path)
                if file_size > 0:
                    self.duplicates['images']['by_size'][file_size].append(rel_path)

                # 按内容哈希分组
                content_hash = self.get_file_hash(img_path)
                if content_hash:
                    self.duplicates['images']['by_hash'][content_hash].append(rel_path)

        print(f"  扫描了 {self.stats['total_images']} 个图片")

    def scan_attachments(self):
        """扫描所有附件文件"""
        print("扫描附件文件...")

        for ext in ATTACHMENT_EXTENSIONS:
            for att_path in self.vault_path.rglob(f'*{ext}'):
                # 跳过隐藏目录
                if any(part.startswith('.') for part in att_path.parts):
                    continue

                self.stats['total_attachments'] += 1
                rel_path = str(att_path.relative_to(self.vault_path))

                # 按文件名分组
                file_name = att_path.name
                self.duplicates['attachments']['by_name'][file_name].append(rel_path)

                # 按文件大小分组
                file_size = self.get_file_size(att_path)
                if file_size > 0:
                    self.duplicates['attachments']['by_size'][file_size].append(rel_path)

                # 按内容哈希分组
                content_hash = self.get_file_hash(att_path)
                if content_hash:
                    self.duplicates['attachments']['by_hash'][content_hash].append(rel_path)

        print(f"  扫描了 {self.stats['total_attachments']} 个附件")

    def scan_vault(self):
        """扫描整个 Obsidian 仓库"""
        print(f"开始扫描 Obsidian 仓库: {self.vault_path}\n")

        self.scan_notes()
        self.scan_images()
        self.scan_attachments()

        print("\n扫描完成！\n")

    def analyze_duplicates(self):
        """分析重复内容"""
        print("分析重复内容...")

        # 分析笔记重复
        for group_type in ['by_name', 'by_content', 'by_size']:
            for key, paths in self.duplicates['notes'][group_type].items():
                if len(paths) > 1:
                    self.stats['duplicate_notes'] += len(paths) - 1

        # 分析图片重复
        for group_type in ['by_name', 'by_hash', 'by_size']:
            for key, paths in self.duplicates['images'][group_type].items():
                if len(paths) > 1:
                    self.stats['duplicate_images'] += len(paths) - 1

        # 分析附件重复
        for group_type in ['by_name', 'by_hash', 'by_size']:
            for key, paths in self.duplicates['attachments'][group_type].items():
                if len(paths) > 1:
                    self.stats['duplicate_attachments'] += len(paths) - 1

        print("分析完成！\n")

    def generate_report(self, output_path):
        """生成 Markdown 格式的报告"""
        report_lines = [
            "# Obsidian 仓库重复内容检测报告",
            "",
            f"**扫描时间**: {self._get_current_time()}",
            f"**仓库路径**: `{self.vault_path}`",
            "",
            "## 📊 扫描统计",
            "",
            f"- **笔记总数**: {self.stats['total_notes']} 个",
            f"  - 疑似重复: {self.stats['duplicate_notes']} 个",
            f"- **图片总数**: {self.stats['total_images']} 个",
            f"  - 疑似重复: {self.stats['duplicate_images']} 个",
            f"- **附件总数**: {self.stats['total_attachments']} 个",
            f"  - 疑似重复: {self.stats['duplicate_attachments']} 个",
            ""
        ]

        # 笔记重复详情
        report_lines.extend(self._generate_section('notes', '笔记'))
        # 图片重复详情
        report_lines.extend(self._generate_section('images', '图片'))
        # 附件重复详情
        report_lines.extend(self._generate_section('attachments', '附件'))

        # 添加清理建议
        report_lines.extend([
            "## 🔧 清理建议",
            "",
            "### 1. 删除完全相同的文件（内容哈希相同）",
            "```bash",
            "# 查看重复文件",
            f"cd \"{self.vault_path}\"",
            "# 建议手动检查后删除",
            "```",
            "",
            "### 2. 合并文件名相同的文件",
            "如果文件名相同但内容不同，建议：",
            "- 重命名其中一个文件",
            "- 合并内容",
            "",
            "### 3. 使用 Obsidian 插件",
            "- **Find unlinked files**: 查找未链接的文件",
            "- **Duplicate Code Block**: 检测重复内容块",
            "- **Janitor**: 清理重复附件",
            "",
            "### 4. 手动检查",
            "建议逐个检查报告中的重复文件，确认是否真的重复，再决定删除或保留。",
            "",
            "---",
            "",
            "*报告生成工具: Obsidian Duplicate Checker v1.0*"
        ])

        # 写入文件
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        print(f"报告已生成: {output_path}")

    def _generate_section(self, file_type, file_type_name):
        """生成重复内容报告的某一节"""
        lines = [
            f"## 📄 {file_type_name}重复详情",
            ""
        ]

        # 按内容哈希分组（最准确）
        hash_key = 'by_hash' if file_type != 'notes' else 'by_content'
        duplicates_by_hash = {
            k: v for k, v in self.duplicates[file_type][hash_key].items()
            if len(v) > 1
        }

        if duplicates_by_hash:
            lines.extend([
                f"### 🔍 内容完全相同的{file_type_name}（按哈希值）",
                "",
                f"共发现 **{len(duplicates_by_hash)}** 组完全相同的{file_type_name}：",
                ""
            ])

            for idx, (hash_val, paths) in enumerate(sorted(duplicates_by_hash.items(), key=lambda x: len(x[1]), reverse=True)[:20], 1):
                lines.append(f"#### 组 {idx}（{len(paths)} 个文件）")
                lines.append("")
                for path in sorted(paths):
                    lines.append(f"- `{path}`")
                lines.append("")

            if len(duplicates_by_hash) > 20:
                lines.append(f"*...还有 {len(duplicates_by_hash) - 20} 组重复，详见完整数据*")
                lines.append("")

        # 按文件名分组
        duplicates_by_name = {
            k: v for k, v in self.duplicates[file_type]['by_name'].items()
            if len(v) > 1
        }

        if duplicates_by_name:
            lines.extend([
                f"### 📝 文件名相同的{file_type_name}",
                "",
                f"共发现 **{len(duplicates_by_name)}** 组同名{file_type_name}：",
                "",
                "| 文件名 | 位置 |",
                "|--------|------|"
            ])

            for file_name, paths in sorted(duplicates_by_name.items())[:30]:
                for idx, path in enumerate(sorted(paths)):
                    if idx == 0:
                        lines.append(f"| `{file_name}` | `{path}` |")
                    else:
                        lines.append(f"| | `{path}` |")

            lines.extend(["", "---", ""])

        # 按文件大小分组（可能重复）
        duplicates_by_size = {
            k: v for k, v in self.duplicates[file_type]['by_size'].items()
            if len(v) > 1 and k > 1024  # 只关注大于 1KB 的文件
        }

        if duplicates_by_size:
            lines.extend([
                f"### 📏 文件大小相同的{file_type_name}（可能重复）",
                "",
                f"共发现 **{len(duplicates_by_size)}** 组大小相同的{file_type_name}：",
                "",
                "| 文件大小 | 文件数量 | 示例文件 |",
                "|----------|----------|----------|"
            ])

            for size, paths in sorted(duplicates_by_size.items(), key=lambda x: x[0], reverse=True)[:20]:
                size_kb = size / 1024
                size_mb = size_kb / 1024
                if size_mb >= 1:
                    size_str = f"{size_mb:.2f} MB"
                else:
                    size_str = f"{size_kb:.2f} KB"

                example = paths[0]
                lines.append(f"| {size_str} | {len(paths)} | `{example}` |")

            lines.extend(["", "---", ""])

        return lines

    def _get_current_time(self):
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def main():
    print("=" * 60)
    print("Obsidian 仓库重复内容检测工具")
    print("=" * 60)
    print()

    checker = DuplicateChecker(OBSIDIAN_VAULT_PATH)
    checker.scan_vault()
    checker.analyze_duplicates()
    checker.generate_report(OUTPUT_REPORT)

    print()
    print("=" * 60)
    print("摘要:")
    print(f"  - 笔记: {checker.stats['total_notes']} 个（{checker.stats['duplicate_notes']} 个疑似重复）")
    print(f"  - 图片: {checker.stats['total_images']} 个（{checker.stats['duplicate_images']} 个疑似重复）")
    print(f"  - 附件: {checker.stats['total_attachments']} 个（{checker.stats['duplicate_attachments']} 个疑似重复）")
    print("=" * 60)


if __name__ == '__main__':
    main()
