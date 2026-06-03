#!/usr/bin/env python3
"""
Obsidian 仓库资源链接检测工具
检测所有 Markdown 笔记中缺失的图片和附件
"""

import os
import re
from pathlib import Path
from collections import defaultdict
import json
import glob

# 自动检测 Obsidian 仓库路径（处理特殊字符）
def find_obsidian_vault():
    """自动查找 Obsidian 仓库路径"""
    docs_path = Path("/Users/wardlu/Documents")
    # 查找所有包含 "Obsidian" 的目录（排除副本）
    candidates = []
    for item in docs_path.iterdir():
        if item.is_dir() and 'obsidian' in item.name.lower() and '副本' not in item.name:
            candidates.append(item)

    if not candidates:
        raise FileNotFoundError("未找到 Obsidian 仓库")

    # 返回第一个匹配的目录
    return candidates[0]

# 配置路径
OBSIDIAN_VAULT_PATH = find_obsidian_vault()
OUTPUT_REPORT = "/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/broken_links_report.md"

# 支持的图片和附件格式
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp'}
ATTACHMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar', '.mp3', '.mp4', '.wav'}

class ResourceChecker:
    def __init__(self, vault_path):
        self.vault_path = Path(vault_path)
        self.broken_links = defaultdict(list)  # {note_path: [broken_resources]}
        self.stats = {
            'total_notes': 0,
            'notes_with_issues': 0,
            'total_broken_links': 0,
            'missing_images': 0,
            'missing_attachments': 0
        }

    def extract_links(self, content):
        """提取所有资源链接"""
        links = []

        # Markdown 格式: ![alt](path)
        markdown_pattern = r'!\[.*?\]\((.*?)\)'
        for match in re.finditer(markdown_pattern, content):
            links.append(('markdown', match.group(1)))

        # WikiLinks 格式: ![[filename]]
        wikilinks_pattern = r'!\[\[(.*?)\]\]'
        for match in re.finditer(wikilinks_pattern, content):
            links.append(('wikilink', match.group(1)))

        return links

    def check_resource_exists(self, link_path, note_path):
        """检查资源文件是否存在"""
        # 处理 WikiLinks（可能只有文件名，没有路径）
        if not link_path.startswith(('http://', 'https://', '/', '~')):
            # 相对路径，基于笔记位置或仓库根目录查找
            possible_paths = [
                note_path.parent / link_path,  # 相对于笔记
                self.vault_path / link_path,    # 相对于仓库根
            ]

            # 如果是纯文件名，在仓库中递归查找
            if '/' not in link_path and '\\' not in link_path:
                for file in self.vault_path.rglob(link_path):
                    return True, file

            for path in possible_paths:
                if path.exists():
                    return True, path

            return False, None
        else:
            # 网络链接，跳过检查
            return True, None

    def scan_note(self, note_path):
        """扫描单个笔记文件"""
        # 统计所有笔记（不管是否有链接）
        self.stats['total_notes'] += 1

        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()

            links = self.extract_links(content)
            if not links:
                return

            broken = []

            for link_type, link_path in links:
                exists, actual_path = self.check_resource_exists(link_path, note_path)

                if not exists:
                    # 判断是图片还是附件
                    ext = Path(link_path).suffix.lower()
                    if ext in IMAGE_EXTENSIONS:
                        resource_type = 'image'
                        self.stats['missing_images'] += 1
                    elif ext in ATTACHMENT_EXTENSIONS:
                        resource_type = 'attachment'
                        self.stats['missing_attachments'] += 1
                    else:
                        resource_type = 'unknown'

                    broken.append({
                        'type': resource_type,
                        'link_type': link_type,
                        'path': link_path,
                        'extension': ext
                    })

            if broken:
                self.broken_links[str(note_path.relative_to(self.vault_path))] = broken
                self.stats['notes_with_issues'] += 1
                self.stats['total_broken_links'] += len(broken)

        except Exception as e:
            print(f"处理文件时出错 {note_path}: {e}")

    def scan_vault(self):
        """扫描整个 Obsidian 仓库"""
        print(f"开始扫描 Obsidian 仓库: {self.vault_path}")
        print(f"这可能需要几分钟...\n")

        # 遍历所有 Markdown 文件
        for note_path in self.vault_path.rglob('*.md'):
            # 跳过 .trash 等隐藏目录
            if any(part.startswith('.') for part in note_path.parts):
                continue

            self.scan_note(note_path)

        print(f"扫描完成！\n")

    def generate_report(self, output_path):
        """生成 Markdown 格式的报告"""
        report_lines = [
            "# Obsidian 笔记资源链接问题报告",
            "",
            f"**扫描时间**: {self._get_current_time()}",
            f"**仓库路径**: `{self.vault_path}`",
            "",
            "## 📊 统计概览",
            "",
            f"- **总扫描笔记数**: {self.stats['total_notes']}",
            f"- **存在问题的笔记**: {self.stats['notes_with_issues']}",
            f"- **缺失资源总数**: {self.stats['total_broken_links']}",
            f"  - 缺失图片: {self.stats['missing_images']}",
            f"  - 缺失附件: {self.stats['missing_attachments']}",
            ""
        ]

        if not self.broken_links:
            report_lines.extend([
                "## ✅ 检查结果",
                "",
                "**未发现缺失的资源链接！** 所有图片和附件引用正常。",
                ""
            ])
        else:
            report_lines.extend([
                "## ❌ 问题详情",
                "",
                f"共发现 **{len(self.broken_links)}** 个笔记存在资源缺失问题：",
                "",
                "---",
                ""
            ])

            # 按文件排序
            for note_path in sorted(self.broken_links.keys()):
                broken = self.broken_links[note_path]

                report_lines.extend([
                    f"### 📄 `{note_path}`",
                    "",
                    f"**缺失资源数**: {len(broken)}",
                    "",
                    "| 类型 | 链接格式 | 资源路径 | 扩展名 |",
                    "|------|---------|---------|--------|"
                ])

                for item in broken:
                    resource_icon = '🖼️' if item['type'] == 'image' else '📎'
                    link_icon = 'MD' if item['link_type'] == 'markdown' else 'WL'
                    report_lines.append(
                        f"| {resource_icon} {item['type']} | {link_icon} | `{item['path']}` | {item['extension']} |"
                    )

                report_lines.extend(["", "---", ""])

        # 添加修复建议
        report_lines.extend([
            "## 🔧 修复建议",
            "",
            "### 1. 检查原始 WizNote 下载目录",
            "```bash",
            f"# 查看原始下载目录中的资源文件",
            "ls -la '/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download'",
            "```",
            "",
            "### 2. 批量查找缺失的图片",
            "```bash",
            "# 在 WizNote 下载目录中查找特定图片",
            "find '/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download' -name '图片名称.png'",
            "```",
            "",
            "### 3. 批量复制缺失资源到 Obsidian",
            "```bash",
            "# 创建资源目录（如果不存在）",
            "mkdir -p \"/Users/wardlu/Documents/Ward's Obsidian/assets\"",
            "",
            "# 复制所有图片",
            "cp -r '/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download/**/*.png' \"/Users/wardlu/Documents/Ward's Obsidian/assets/\"",
            "```",
            "",
            "### 4. 使用 Obsidian 插件修复",
            "- **Attachment Manager**: 自动整理附件",
            "- **Broken Links**: 检测并修复断开的链接",
            "- **Find unlinked files**: 查找未链接的文件",
            "",
            "---",
            "",
            "## 📝 检测范围",
            "",
            "**检测的链接格式**:",
            "- Markdown 图片: `![alt](path/to/image.png)`",
            "- WikiLinks 图片: `![[image.png]]`",
            "- 附件链接: `[file](path/to/file.pdf)`",
            "",
            "**检测的文件类型**:",
            f"- 图片: {', '.join(IMAGE_EXTENSIONS)}",
            f"- 附件: {', '.join(ATTACHMENT_EXTENSIONS)}",
            "",
            "**注意事项**:",
            "- 网络链接（http/https）已自动跳过",
            "- 隐藏目录（以 . 开头）已自动跳过",
            "- 仅检测 Markdown 文件（.md）",
            "",
            "---",
            "",
            "*报告生成工具: Obsidian Resource Checker v1.0*"
        ])

        # 写入文件
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        print(f"报告已生成: {output_path}")

    def _get_current_time(self):
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def main():
    print("=" * 60)
    print("Obsidian 仓库资源链接检测工具")
    print("=" * 60)
    print()

    checker = ResourceChecker(OBSIDIAN_VAULT_PATH)
    checker.scan_vault()
    checker.generate_report(OUTPUT_REPORT)

    print()
    print("=" * 60)
    print("摘要:")
    print(f"  - 扫描笔记: {checker.stats['total_notes']} 个")
    print(f"  - 问题笔记: {checker.stats['notes_with_issues']} 个")
    print(f"  - 缺失资源: {checker.stats['total_broken_links']} 个")
    print("=" * 60)


if __name__ == '__main__':
    main()
