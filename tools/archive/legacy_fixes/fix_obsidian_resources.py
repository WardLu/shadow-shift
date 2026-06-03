#!/usr/bin/env python3
"""
修复 Obsidian 仓库中缺失的图片和附件
从 WizNote 下载目录复制缺失的资源
"""

import os
import re
import shutil
from pathlib import Path
from collections import defaultdict
import json
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
WIZNOTE_DOWNLOAD_PATH = Path("/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download")
OUTPUT_REPORT = "/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/fix_report.md"

# 支持的图片和附件格式
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp'}
ATTACHMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar', '.mp3', '.mp4', '.wav'}

class ResourceFixer:
    def __init__(self, vault_path, wiznote_path):
        self.vault_path = Path(vault_path)
        self.wiznote_path = Path(wiznote_path)
        self.broken_links = defaultdict(list)
        self.found_resources = []  # 找到并复制的资源
        self.not_found_resources = []  # 未找到的资源
        self.stats = {
            'total_notes': 0,
            'notes_with_issues': 0,
            'total_broken_links': 0,
            'found_and_copied': 0,
            'not_found': 0
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

    def find_resource_in_wiznote(self, resource_name):
        """在 WizNote 下载目录中查找资源"""
        # 递归搜索文件名
        for file in self.wiznote_path.rglob(resource_name):
            return file
        return None

    def copy_resource_to_obsidian(self, source_path, note_path, link_path):
        """复制资源到 Obsidian 仓库"""
        # 确定目标目录
        # 策略1: 保持笔记所在目录结构
        note_dir = note_path.parent

        # 策略2: 如果链接路径包含目录，保持该结构
        link_path_obj = Path(link_path)
        if link_path_obj.parent != Path('.'):
            # 链接包含目录路径
            target_dir = self.vault_path / link_path_obj.parent
        else:
            # 只有文件名，放在笔记同目录
            target_dir = note_dir

        # 创建目标目录
        target_dir.mkdir(parents=True, exist_ok=True)

        # 目标文件路径
        target_path = target_dir / source_path.name

        # 复制文件
        try:
            shutil.copy2(source_path, target_path)
            return True, target_path
        except Exception as e:
            print(f"复制失败: {e}")
            return False, None

    def scan_and_fix_note(self, note_path):
        """扫描并修复单个笔记文件"""
        self.stats['total_notes'] += 1

        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()

            links = self.extract_links(content)
            if not links:
                return

            broken = []

            for link_type, link_path in links:
                # 跳过网络链接
                if link_path.startswith(('http://', 'https://')):
                    continue

                # 检查资源是否存在
                exists = False
                # 检查相对路径
                if (note_path.parent / link_path).exists():
                    exists = True
                # 检查绝对路径
                elif (self.vault_path / link_path).exists():
                    exists = True

                if not exists:
                    # 判断是图片还是附件
                    ext = Path(link_path).suffix.lower()
                    if ext in IMAGE_EXTENSIONS:
                        resource_type = 'image'
                    elif ext in ATTACHMENT_EXTENSIONS:
                        resource_type = 'attachment'
                    else:
                        resource_type = 'unknown'

                    # 尝试在 WizNote 中查找
                    resource_name = Path(link_path).name
                    wiznote_resource = self.find_resource_in_wiznote(resource_name)

                    if wiznote_resource:
                        # 找到了，复制到 Obsidian
                        success, target_path = self.copy_resource_to_obsidian(
                            wiznote_resource, note_path, link_path
                        )

                        if success:
                            self.found_resources.append({
                                'note': str(note_path.relative_to(self.vault_path)),
                                'original_link': link_path,
                                'source': str(wiznote_resource.relative_to(self.wiznote_path)),
                                'target': str(target_path.relative_to(self.vault_path))
                            })
                            self.stats['found_and_copied'] += 1
                            broken.append({
                                'type': resource_type,
                                'link_type': link_type,
                                'path': link_path,
                                'extension': ext,
                                'fixed': True
                            })
                        else:
                            self.stats['not_found'] += 1
                            broken.append({
                                'type': resource_type,
                                'link_type': link_type,
                                'path': link_path,
                                'extension': ext,
                                'fixed': False,
                                'reason': '复制失败'
                            })
                    else:
                        # 未找到
                        self.not_found_resources.append({
                            'note': str(note_path.relative_to(self.vault_path)),
                            'resource': link_path
                        })
                        self.stats['not_found'] += 1
                        broken.append({
                            'type': resource_type,
                            'link_type': link_type,
                            'path': link_path,
                            'extension': ext,
                            'fixed': False,
                            'reason': '在 WizNote 中未找到'
                        })

            if broken:
                self.broken_links[str(note_path.relative_to(self.vault_path))] = broken
                self.stats['notes_with_issues'] += 1
                self.stats['total_broken_links'] += len(broken)

        except Exception as e:
            print(f"处理文件时出错 {note_path}: {e}")

    def scan_and_fix_vault(self):
        """扫描并修复整个 Obsidian 仓库"""
        print(f"开始扫描并修复 Obsidian 仓库: {self.vault_path}")
        print(f"从 WizNote 下载目录复制缺失资源: {self.wiznote_path}")
        print(f"这可能需要几分钟...\n")

        # 遍历所有 Markdown 文件
        for note_path in self.vault_path.rglob('*.md'):
            # 跳过隐藏目录
            if any(part.startswith('.') for part in note_path.parts):
                continue

            self.scan_and_fix_note(note_path)

        print(f"扫描和修复完成！\n")

    def generate_report(self, output_path):
        """生成修复报告"""
        report_lines = [
            "# Obsidian 笔记资源修复报告",
            "",
            f"**修复时间**: {self._get_current_time()}",
            f"**Obsidian 仓库**: `{self.vault_path}`",
            f"**WizNote 下载目录**: `{self.wiznote_path}`",
            "",
            "## 📊 修复统计",
            "",
            f"- **总扫描笔记数**: {self.stats['total_notes']}",
            f"- **存在问题的笔记**: {self.stats['notes_with_issues']}",
            f"- **缺失资源总数**: {self.stats['total_broken_links']}",
            f"- **✅ 成功修复**: {self.stats['found_and_copied']}",
            f"- **❌ 未找到资源**: {self.stats['not_found']}",
            ""
        ]

        # 成功修复的资源
        if self.found_resources:
            report_lines.extend([
                "## ✅ 成功修复的资源",
                "",
                f"共修复 **{len(self.found_resources)}** 个资源：",
                "",
                "| 笔记 | 原链接 | 源文件 | 目标位置 |",
                "|------|--------|--------|----------|"
            ])

            for item in self.found_resources:
                report_lines.append(
                    f"| `{item['note']}` | `{item['original_link']}` | `{item['source']}` | `{item['target']}` |"
                )

            report_lines.extend(["", "---", ""])

        # 未找到的资源
        if self.not_found_resources:
            report_lines.extend([
                "## ❌ 未找到的资源",
                "",
                f"共 **{len(self.not_found_resources)}** 个资源在 WizNote 下载目录中未找到：",
                "",
                "| 笔记 | 缺失资源 |",
                "|------|----------|"
            ])

            for item in self.not_found_resources:
                report_lines.append(
                    f"| `{item['note']}` | `{item['resource']}` |"
                )

            report_lines.extend(["", "---", ""])

        # 仍需手动处理的问题
        if self.stats['not_found'] > 0:
            report_lines.extend([
                "## 🔧 手动修复建议",
                "",
                "以下资源在 WizNote 下载目录中未找到，可能需要：",
                "",
                "1. **检查原始来源**：这些图片可能是网络图片或已被删除",
                "2. **重新下载**：如果是网络图片，尝试重新下载",
                "3. **删除引用**：如果图片不再需要，可以删除笔记中的引用",
                "",
                "### 查找网络图片",
                "```bash",
                "# 在笔记中搜索 http 开头的图片链接",
                f"grep -r 'http' \"{self.vault_path}\" --include=\"*.md\"",
                "```",
                ""
            ])

        report_lines.extend([
            "---",
            "",
            "*报告生成工具: Obsidian Resource Fixer v1.0*"
        ])

        # 写入文件
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        print(f"修复报告已生成: {output_path}")

    def _get_current_time(self):
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def main():
    print("=" * 60)
    print("Obsidian 仓库资源修复工具")
    print("=" * 60)
    print()

    fixer = ResourceFixer(OBSIDIAN_VAULT_PATH, WIZNOTE_DOWNLOAD_PATH)
    fixer.scan_and_fix_vault()
    fixer.generate_report(OUTPUT_REPORT)

    print()
    print("=" * 60)
    print("修复摘要:")
    print(f"  - 扫描笔记: {fixer.stats['total_notes']} 个")
    print(f"  - 问题笔记: {fixer.stats['notes_with_issues']} 个")
    print(f"  - 缺失资源: {fixer.stats['total_broken_links']} 个")
    print(f"  - ✅ 成功修复: {fixer.stats['found_and_copied']} 个")
    print(f"  - ❌ 未找到: {fixer.stats['not_found']} 个")
    print("=" * 60)


if __name__ == '__main__':
    main()
