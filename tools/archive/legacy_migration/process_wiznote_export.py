#!/usr/bin/env python3
"""
处理 WizNote 导出的 Markdown 文件

使用场景：
1. 在 WizNote 客户端中导出 Markdown（包含图片）
2. 将导出的文件放到一个目录
3. 运行此脚本自动处理和更新到 Obsidian
"""

from pathlib import Path
import re
import shutil
from datetime import datetime

class WizNoteExportProcessor:
    def __init__(self, export_dir):
        """
        Args:
            export_dir: WizNote 导出目录的路径
        """
        self.export_dir = Path(export_dir)
        self.obsidian_vault = self._find_obsidian_vault()
        self.project_path = Path('/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian')

        self.stats = {
            'total_notes': 0,
            'updated_notes': 0,
            'copied_images': 0,
            'skipped_notes': 0
        }

    def _find_obsidian_vault(self):
        """查找 Obsidian 仓库"""
        docs_path = Path('/Users/wardlu/Documents')
        for item in docs_path.iterdir():
            if item.is_dir() and 'obsidian' in item.name.lower() and '副本' not in item.name:
                return item
        return None

    def scan_exported_notes(self):
        """扫描导出的笔记"""
        print(f"扫描导出目录: {self.export_dir}\n")

        notes = []
        for md_file in self.export_dir.rglob('*.md'):
            # 检查是否有对应的图片目录
            note_dir = md_file.parent
            images = list(note_dir.glob('*.png')) + list(note_dir.glob('*.jpg')) + list(note_dir.glob('*.gif'))

            notes.append({
                'file': md_file,
                'name': md_file.stem,
                'images': images,
                'image_count': len(images)
            })

        self.stats['total_notes'] = len(notes)
        print(f"找到 {len(notes)} 个导出的笔记\n")

        return notes

    def find_in_obsidian(self, note_name):
        """在 Obsidian 中查找对应的笔记"""
        # 清理名称（移除特殊字符）
        clean_name = re.sub(r'[^\w\s\u4e00-\u9fa5-]', '', note_name)

        for md in self.obsidian_vault.rglob('*.md'):
            if clean_name in md.stem or note_name in md.stem:
                return md

        return None

    def process_note(self, note_info, dry_run=True):
        """处理单个笔记"""
        md_file = note_info['file']
        note_name = note_info['name']
        images = note_info['images']

        print(f"\n处理: {note_name}")
        print(f"  导出文件: {md_file.name}")
        print(f"  图片数: {len(images)}")

        # 在 Obsidian 中查找对应的笔记
        obsidian_note = self.find_in_obsidian(note_name)

        if not obsidian_note:
            print(f"  ⚠️ 在 Obsidian 中未找到对应笔记")
            self.stats['skipped_notes'] += 1
            return

        print(f"  Obsidian 位置: {obsidian_note.relative_to(self.obsidian_vault)}")

        # 读取导出的内容
        exported_content = md_file.read_text(encoding='utf-8')
        obsidian_content = obsidian_note.read_text(encoding='utf-8')

        # 检查图片链接
        exported_images = re.findall(r'!\[.*?\]\((.*?)\)', exported_content)
        obsidian_images = re.findall(r'!\[.*?\]\(.*?\)', obsidian_content)

        print(f"  导出图片链接: {len(exported_images)}")
        print(f"  Obsidian 图片链接: {len(obsidian_images)}")

        if len(exported_images) <= len(obsidian_images):
            print(f"  ✅ Obsidian 图片数 ≥ 导出图片数，跳过")
            return

        # 复制图片到 Obsidian
        if images and not dry_run:
            # 创建 attachments 目录
            att_dir = obsidian_note.parent / 'attachments'
            att_dir.mkdir(exist_ok=True)

            # 复制图片
            for img in images:
                target = att_dir / img.name
                if not target.exists():
                    shutil.copy2(img, target)
                    self.stats['copied_images'] += 1
                    print(f"    ✅ 复制图片: {img.name}")

        # 更新笔记内容（替换图片链接）
        if not dry_run:
            # 保留 Obsidian 的 frontmatter
            frontmatter = ''
            if obsidian_content.startswith('---'):
                parts = obsidian_content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = '---' + parts[1] + '---\n\n'

            # 转换图片链接为 Obsidian 格式
            new_content = exported_content
            for img_name in exported_images:
                old_link = f'!]({img_name})'
                new_link = f'![[attachments/{img_name}]]'
                new_content = new_content.replace(old_link, new_link)

            # 合并内容
            final_content = frontmatter + new_content

            # 保存
            obsidian_note.write_text(final_content, encoding='utf-8')
            self.stats['updated_notes'] += 1
            print(f"  ✅ 更新笔记")
        else:
            print(f"  [DRY RUN] 将更新笔记和 {len(images)} 个图片")

    def process_all(self, dry_run=True):
        """处理所有导出的笔记"""
        print("=" * 60)
        print("WizNote 导出文件处理工具")
        print("=" * 60)
        print()

        if not self.export_dir.exists():
            print(f"❌ 导出目录不存在: {self.export_dir}")
            return

        # 扫描笔记
        notes = self.scan_exported_notes()

        if not notes:
            print("❌ 未找到导出的笔记")
            return

        # 按图片数排序（优先处理缺失多的）
        notes.sort(key=lambda x: x['image_count'], reverse=True)

        print("=" * 60)
        print("开始处理笔记")
        print("=" * 60)

        for note in notes:
            self.process_note(note, dry_run)

        # 显示统计
        print("\n" + "=" * 60)
        print("处理完成")
        print("=" * 60)
        print(f"总笔记数: {self.stats['total_notes']}")
        print(f"更新笔记: {self.stats['updated_notes']}")
        print(f"复制图片: {self.stats['copied_images']}")
        print(f"跳过笔记: {self.stats['skipped_notes']}")
        print()

def main():
    import sys

    print("\n" + "=" * 60)
    print("WizNote 导出文件处理工具")
    print("=" * 60)
    print()

    # 使用说明
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python3 process_wiznote_export.py <导出目录路径> [--execute]\n")
        print("参数:")
        print("  <导出目录路径>  WizNote 导出 Markdown 的目录")
        print("  --execute       执行实际更新（默认为预览模式）\n")
        print("示例:")
        print("  # 预览模式")
        print("  python3 process_wiznote_export.py ~/Downloads/wiznote_export\n")
        print("  # 执行更新")
        print("  python3 process_wiznote_export.py ~/Downloads/wiznote_export --execute\n")
        return

    export_dir = sys.argv[1]
    dry_run = '--execute' not in sys.argv

    if dry_run:
        print("⚠️  预览模式（不会修改文件）")
        print("使用 --execute 参数执行实际更新\n")
    else:
        print("⚠️  执行模式（将修改文件）\n")

    processor = WizNoteExportProcessor(export_dir)
    processor.process_all(dry_run)

if __name__ == '__main__':
    main()
