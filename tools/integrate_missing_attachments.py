#!/usr/bin/env python3
"""
整合"缺失图片及附件笔记"到源文件
将笔记中的图片和附件整合到 wiznote_download 的原始位置
"""

import os
import re
import shutil
from pathlib import Path
from collections import defaultdict


class AttachmentIntegrator:
    """附件整合器"""

    def __init__(self, wiznote_download_path: str):
        self.wiznote_download = Path(wiznote_download_path)
        self.missing_folder = self.wiznote_download / "缺失图片及附件笔记"
        self.results = {
            'notes_processed': 0,
            'notes_found_original': 0,
            'attachments_moved': 0,
            'images_moved': 0,
            'errors': [],
            'details': []
        }

    def find_original_note(self, note_name: str) -> Path:
        """在 wiznote_download 中查找笔记的原始位置"""
        # 排除"缺失图片及附件笔记"目录
        for md_file in self.wiznote_download.rglob("*.md"):
            if "缺失图片及附件笔记" in str(md_file):
                continue
            if md_file.name == note_name:
                return md_file
        return None

    def extract_image_links(self, content: str) -> list:
        """提取笔记中的图片链接"""
        images = []

        # WikiLink 格式: ![[image.png]]
        wikilink_pattern = r'!\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
        for match in re.finditer(wikilink_pattern, content):
            images.append(match.group(1).strip())

        # Markdown 格式: ![](image.png)
        md_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        for match in re.finditer(md_pattern, content):
            images.append(match.group(2).strip())

        return images

    def find_image_in_missing_folder(self, image_name: str) -> Path:
        """在"缺失图片及附件笔记"目录中查找图片"""
        # 搜索位置
        search_paths = [
            self.missing_folder / "images" / image_name,
            self.missing_folder / "attachments" / image_name,
        ]

        # 搜索 _files 目录
        for files_dir in self.missing_folder.rglob("*_files"):
            potential_path = files_dir / image_name
            if potential_path.exists():
                return potential_path

        # 如果还找不到，在整个目录中搜索
        matches = list(self.missing_folder.rglob(image_name))
        if matches:
            return matches[0]

        return None

    def process_note(self, note_path: Path):
        """处理单个笔记"""
        try:
            print(f"\n处理笔记: {note_path.name}")

            # 1. 查找原始位置
            original_note = self.find_original_note(note_path.name)

            if not original_note:
                print(f"  ⚠️  未找到原始位置，跳过")
                return

            print(f"  ✓ 找到原始位置: {original_note.relative_to(self.wiznote_download)}")

            # 2. 读取笔记内容，提取图片链接
            with open(note_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            images = self.extract_image_links(content)
            print(f"  📷 找到 {len(images)} 个图片链接")

            # 3. 查找并复制图片/附件
            original_dir = original_note.parent
            original_files_dir = original_dir / f"{original_note.stem}_files"

            moved_count = 0
            for image_link in images:
                # 提取图片文件名（移除路径）
                image_name = Path(image_link).name

                # 在"缺失图片及附件笔记"中查找图片
                source_image = self.find_image_in_missing_folder(image_name)

                if source_image:
                    # 确定目标位置
                    # 优先使用 _files 目录
                    target_dir = original_files_dir if original_files_dir.exists() else original_dir
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_path = target_dir / image_name

                    # 复制图片（不覆盖已存在的文件）
                    if not target_path.exists():
                        shutil.copy2(source_image, target_path)
                        print(f"    ✓ 复制: {image_name} -> {target_path.relative_to(self.wiznote_download)}")
                        moved_count += 1
                    else:
                        print(f"    - 跳过（已存在）: {image_name}")

            self.results['notes_processed'] += 1
            self.results['notes_found_original'] += 1
            self.results['images_moved'] += moved_count

            self.results['details'].append({
                'note': note_path.name,
                'original': str(original_note.relative_to(self.wiznote_download)),
                'images_found': len(images),
                'images_moved': moved_count
            })

        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
            self.results['errors'].append({
                'note': note_path.name,
                'error': str(e)
            })

    def run(self):
        """执行整合"""
        print("=" * 60)
        print("🔄 整合缺失图片及附件笔记")
        print("=" * 60)
        print(f"源目录: {self.missing_folder}")
        print(f"目标目录: {self.wiznote_download}\n")

        # 获取所有笔记文件
        notes = list(self.missing_folder.glob("*.md"))

        print(f"📊 找到 {len(notes)} 个笔记文件\n")
        print("开始处理...\n")

        # 处理每个笔记
        for note_path in notes:
            self.process_note(note_path)

        # 生成报告
        self.generate_report()

        return self.results

    def generate_report(self):
        """生成报告"""
        print("\n" + "=" * 60)
        print("📊 整合完成报告")
        print("=" * 60)
        print(f"\n处理笔记: {self.results['notes_processed']}")
        print(f"找到原始位置: {self.results['notes_found_original']}")
        print(f"复制图片/附件: {self.results['images_moved']}")

        if self.results['errors']:
            print(f"\n❌ 错误: {len(self.results['errors'])}")
            for error in self.results['errors']:
                print(f"  - {error['note']}: {error['error']}")

        print("\n" + "=" * 60)

        # 保存详细报告
        report_file = self.wiznote_download / "attachment_integration_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("缺失图片及附件整合报告\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"处理笔记: {self.results['notes_processed']}\n")
            f.write(f"找到原始位置: {self.results['notes_found_original']}\n")
            f.write(f"复制图片/附件: {self.results['images_moved']}\n\n")

            if self.results['details']:
                f.write("详细列表:\n")
                f.write("-" * 60 + "\n")
                for detail in self.results['details']:
                    f.write(f"\n笔记: {detail['note']}\n")
                    f.write(f"原始位置: {detail['original']}\n")
                    f.write(f"图片链接: {detail['images_found']}\n")
                    f.write(f"图片复制: {detail['images_moved']}\n")

            if self.results['errors']:
                f.write("\n错误列表:\n")
                f.write("-" * 60 + "\n")
                for error in self.results['errors']:
                    f.write(f"\n{error['note']}: {error['error']}\n")

        print(f"\n📄 详细报告已保存: {report_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='集成缺失的附件')
    parser.add_argument('--wiznote-dir', required=True, help='为知笔记下载目录路径')
    args = parser.parse_args()

    integrator = AttachmentIntegrator(args.wiznote_dir)
    integrator.run()


if __name__ == '__main__':
    main()
