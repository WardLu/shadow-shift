#!/usr/bin/env python3
"""
Wiznote 源文件附件修复工具
将 WikiLink 格式转换回标准 Markdown 格式，确保在 Typora 等标准 Markdown 编辑器中正常显示
"""

import os
import re
from pathlib import Path
from datetime import datetime


class WiznoteSourceFixer:
    """Wiznote 源文件修复器"""

    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}
    ATTACHMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                             '.xmind', '.zip', '.rar', '.7z', '.mp3', '.mp4', '.wav'}

    def __init__(self, wiznote_download_path: str):
        self.wiznote_download = Path(wiznote_download_path)
        self.results = {
            'total_notes': 0,
            'notes_fixed': 0,
            'wikilinks_converted': 0,
            'errors': [],
            'details': []
        }

    def should_convert_from_wikilink(self, link_name: str) -> tuple:
        """
        判断 WikiLink 是否应该转换为 Markdown

        Returns:
            (should_convert, attachment_type)
        """
        # 移除锚点和别名
        if '#' in link_name:
            link_name = link_name.split('#')[0]
        if '|' in link_name:
            link_name = link_name.split('|')[0]

        # 获取扩展名
        ext = Path(link_name).suffix.lower()

        if not ext:
            return False, None

        if ext in self.IMAGE_EXTENSIONS:
            return True, 'image'
        elif ext in self.ATTACHMENT_EXTENSIONS:
            return True, 'attachment'
        else:
            return False, None

    def find_attachment_file(self, attachment_name: str, note_path: Path) -> Path:
        """
        查找附件文件的实际位置

        优先级：
        1. 笔记所在目录的 `笔记名_files/` 子目录
        2. 笔记所在目录
        """
        # 1. 检查 `笔记名_files/` 目录
        files_dir = note_path.parent / f"{note_path.stem}_files"
        if files_dir.exists():
            potential_path = files_dir / attachment_name
            if potential_path.exists():
                return potential_path

        # 2. 检查笔记所在目录
        potential_path = note_path.parent / attachment_name
        if potential_path.exists():
            return potential_path

        return None

    def fix_wikilinks_in_note(self, note_path: Path) -> dict:
        """
        修复单个笔记中的 WikiLink，转换为标准 Markdown 格式

        Returns:
            修复统计信息
        """
        try:
            with open(note_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_content = f.read()

            content = original_content
            stats = {
                'wikilinks_converted': 0
            }

            # 查找所有 WikiLink 格式的图片和附件链接
            # 格式: ![[filename]] 或 ![[filename|alias]] 或 [[filename]] 或 [[filename|alias]]
            pattern = r'!?\[\[([^\]|#]+)(?:\|[^\]]+)?(?:#[^\]]+)?\]\]'

            for match in re.finditer(pattern, content):
                full_match = match.group(0)
                link_name = match.group(1).strip()

                # 判断是否需要转换
                should_convert, attachment_type = self.should_convert_from_wikilink(link_name)

                if not should_convert:
                    continue

                # 查找文件实际位置
                actual_path = self.find_attachment_file(link_name, note_path)

                if not actual_path:
                    # 文件不存在，跳过
                    continue

                # 确定相对路径
                files_dir_name = f"{note_path.stem}_files"
                expected_dir = note_path.parent / files_dir_name

                # 如果文件在 _files 目录中，使用相对路径
                if actual_path.parent == expected_dir:
                    relative_path = f"{files_dir_name}/{link_name}"
                else:
                    # 文件在同一目录，直接使用文件名
                    relative_path = link_name

                # 转换为 Markdown 格式
                if attachment_type == 'image':
                    markdown_link = f"![]({relative_path})"
                else:
                    markdown_link = f"[{link_name}]({relative_path})"

                # 替换原链接
                content = content.replace(full_match, markdown_link, 1)
                stats['wikilinks_converted'] += 1

            # 如果有修改，保存文件
            if content != original_content:
                with open(note_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                return stats

            return None

        except Exception as e:
            self.results['errors'].append({
                'note': str(note_path.relative_to(self.wiznote_download)),
                'error': str(e)
            })
            return None

    def run(self):
        """执行全面修复"""
        print("=" * 60)
        print("🔧 Wiznote 源文件附件修复工具")
        print("=" * 60)
        print(f"扫描目录: {self.wiznote_download}")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 获取所有 Markdown 文件
        md_files = [f for f in self.wiznote_download.rglob("*.md")
                    if "缺失图片及附件笔记" not in str(f)]

        self.results['total_notes'] = len(md_files)

        print(f"📊 找到 {len(md_files)} 个笔记文件\n")
        print("开始修复...\n")

        # 处理每个笔记
        for i, md_file in enumerate(md_files, 1):
            stats = self.fix_wikilinks_in_note(md_file)

            if stats:
                self.results['notes_fixed'] += 1
                self.results['wikilinks_converted'] += stats['wikilinks_converted']

                # 打印进度
                rel_path = str(md_file.relative_to(self.wiznote_download))
                print(f"[{i}/{len(md_files)}] ✅ {rel_path}")
                if stats['wikilinks_converted'] > 0:
                    print(f"         📝 转换 {stats['wikilinks_converted']} 个 WikiLink 为 Markdown 格式")

        # 生成报告
        self.generate_report()

        return self.results

    def generate_report(self):
        """生成修复报告"""
        print("\n" + "=" * 60)
        print("📊 修复完成报告")
        print("=" * 60)
        print(f"处理笔记: {self.results['total_notes']}")
        print(f"修复笔记: {self.results['notes_fixed']}")
        print(f"转换 WikiLink: {self.results['wikilinks_converted']}")

        if self.results['errors']:
            print(f"\n❌ 错误: {len(self.results['errors'])}")
            for error in self.results['errors']:
                print(f"  - {error['note']}: {error['error']}")

        print("\n" + "=" * 60)

        # 保存详细报告
        report_file = self.wiznote_download / f"source_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("Wiznote 源文件附件修复报告\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"处理笔记: {self.results['total_notes']}\n")
            f.write(f"修复笔记: {self.results['notes_fixed']}\n")
            f.write(f"转换 WikiLink: {self.results['wikilinks_converted']}\n\n")

            if self.results['errors']:
                f.write("错误列表:\n")
                f.write("-" * 60 + "\n")
                for error in self.results['errors']:
                    f.write(f"\n{error['note']}: {error['error']}\n")

        print(f"\n📄 详细报告已保存: {report_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='修复为知笔记源文件')
    parser.add_argument('--wiznote-dir', required=True, help='为知笔记下载目录路径')
    args = parser.parse_args()

    fixer = WiznoteSourceFixer(args.wiznote_dir)
    fixer.run()


if __name__ == '__main__':
    main()
