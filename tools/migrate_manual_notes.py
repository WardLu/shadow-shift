#!/usr/bin/env python3
"""
手动导出笔记迁移工具
将手动导出的笔记及其图片、附件迁移到目标目录
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

class ManualNoteMigrator:
    def __init__(self, source_dir, target_base_dir):
        self.source_dir = Path(source_dir)
        self.target_base_dir = Path(target_base_dir)
        self.results = {
            "total_notes": 0,
            "migrated_notes": 0,
            "skipped_notes": 0,
            "total_images": 0,
            "copied_images": 0,
            "total_attachments": 0,
            "copied_attachments": 0,
            "errors": [],
            "migrations": []
        }

    def find_target_file(self, note_name):
        """在目标目录中查找对应的笔记文件"""
        # 递归搜索目标目录
        for md_file in self.target_base_dir.rglob("*.md"):
            if md_file.name == note_name:
                return md_file
        return None

    def extract_image_links(self, content):
        """提取 Markdown 中的图片链接"""
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.findall(pattern, content)
        return [(alt, path) for alt, path in matches]

    def extract_attachment_links(self, content):
        """提取 Markdown 中的附件链接"""
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(pattern, content)

        attachments = []
        for text, path in matches:
            if not path.startswith(('http://', 'https://')):
                ext = Path(path).suffix.lower()
                if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']:
                    attachments.append((text, path))
        return attachments

    def migrate_note(self, source_note):
        """迁移单个笔记及其资源"""
        note_name = source_note.name
        print(f"\n📝 处理笔记: {note_name}")

        # 查找目标文件
        target_note = self.find_target_file(note_name)

        if not target_note:
            print(f"  ⚠️  未找到目标文件，跳过")
            self.results["skipped_notes"] += 1
            self.results["errors"].append({
                "note": note_name,
                "error": "未找到目标文件"
            })
            return False

        print(f"  ✅ 找到目标: {target_note.relative_to(self.target_base_dir)}")

        # 读取源笔记内容
        try:
            with open(source_note, 'r', encoding='utf-8') as f:
                source_content = f.read()
        except Exception as e:
            print(f"  ❌ 读取源文件失败: {e}")
            self.results["errors"].append({
                "note": note_name,
                "error": f"读取源文件失败: {e}"
            })
            return False

        # 准备目标资源目录（*_files）
        note_stem = target_note.stem
        target_files_dir = target_note.parent / f"{note_stem}_files"

        # 如果目标资源目录不存在，创建它
        if not target_files_dir.exists():
            target_files_dir.mkdir(parents=True, exist_ok=True)
            print(f"  📁 创建资源目录: {target_files_dir.name}")

        # 提取图片链接
        image_links = self.extract_image_links(source_content)
        attachment_links = self.extract_attachment_links(source_content)

        print(f"  🖼️  图片链接: {len(image_links)} 个")
        print(f"  📎 附件链接: {len(attachment_links)} 个")

        # 复制图片
        new_content = source_content
        copied_images = 0

        for alt, img_path in image_links:
            # 源图片路径
            source_img = self.source_dir / img_path

            if not source_img.exists():
                print(f"    ⚠️  图片不存在: {img_path}")
                continue

            # 目标图片路径
            img_name = Path(img_path).name
            target_img = target_files_dir / img_name

            # 复制图片
            try:
                shutil.copy2(source_img, target_img)
                copied_images += 1

                # 更新链接
                old_link = f"]({img_path})"
                new_link = f"]({target_files_dir.name}/{img_name})"
                new_content = new_content.replace(old_link, new_link)

            except Exception as e:
                print(f"    ❌ 复制图片失败 {img_name}: {e}")
                self.results["errors"].append({
                    "note": note_name,
                    "error": f"复制图片失败 {img_name}: {e}"
                })

        print(f"  ✅ 复制图片: {copied_images}/{len(image_links)} 个")

        # 复制附件
        copied_attachments = 0

        for text, att_path in attachment_links:
            # 源附件路径
            source_att = self.source_dir / att_path

            if not source_att.exists():
                print(f"    ⚠️  附件不存在: {att_path}")
                continue

            # 目标附件路径
            att_name = Path(att_path).name
            target_att = target_files_dir / att_name

            # 复制附件
            try:
                shutil.copy2(source_att, target_att)
                copied_attachments += 1

                # 更新链接
                old_link = f"]({att_path})"
                new_link = f"]({target_files_dir.name}/{att_name})"
                new_content = new_content.replace(old_link, new_link)

            except Exception as e:
                print(f"    ❌ 复制附件失败 {att_name}: {e}")
                self.results["errors"].append({
                    "note": note_name,
                    "error": f"复制附件失败 {att_name}: {e}"
                })

        if attachment_links:
            print(f"  ✅ 复制附件: {copied_attachments}/{len(attachment_links)} 个")

        # 备份原始文件
        backup_path = target_note.parent / f"{target_note.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{target_note.suffix}"
        try:
            shutil.copy2(target_note, backup_path)
            print(f"  💾 备份原文件: {backup_path.name}")
        except Exception as e:
            print(f"  ⚠️  备份失败: {e}")

        # 写入新内容
        try:
            with open(target_note, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  ✅ 更新笔记内容")
        except Exception as e:
            print(f"  ❌ 写入失败: {e}")
            self.results["errors"].append({
                "note": note_name,
                "error": f"写入失败: {e}"
            })
            return False

        # 记录统计
        self.results["migrated_notes"] += 1
        self.results["total_images"] += len(image_links)
        self.results["copied_images"] += copied_images
        self.results["total_attachments"] += len(attachment_links)
        self.results["copied_attachments"] += copied_attachments

        self.results["migrations"].append({
            "note": note_name,
            "target": str(target_note.relative_to(self.target_base_dir)),
            "images": copied_images,
            "attachments": copied_attachments
        })

        return True

    def run(self):
        """执行迁移"""
        print("=" * 60)
        print("🚀 手动导出笔记迁移工具")
        print("=" * 60)
        print(f"源目录: {self.source_dir}")
        print(f"目标目录: {self.target_base_dir}")
        print()

        # 获取所有 Markdown 文件
        md_files = list(self.source_dir.glob("*.md"))
        self.results["total_notes"] = len(md_files)

        print(f"📊 找到 {len(md_files)} 个笔记文件")
        print()

        # 迁移每个笔记
        for md_file in md_files:
            self.migrate_note(md_file)

        # 生成报告
        self.generate_report()

        return self.results

    def generate_report(self):
        """生成迁移报告"""
        report = []
        report.append("\n" + "=" * 60)
        report.append("📊 迁移报告")
        report.append("=" * 60)

        report.append("\n## 总体统计")
        report.append(f"笔记总数: {self.results['total_notes']}")
        report.append(f"成功迁移: {self.results['migrated_notes']}")
        report.append(f"跳过笔记: {self.results['skipped_notes']}")
        report.append(f"图片总数: {self.results['total_images']}")
        report.append(f"复制图片: {self.results['copied_images']}")
        report.append(f"附件总数: {self.results['total_attachments']}")
        report.append(f"复制附件: {self.results['copied_attachments']}")

        if self.results["migrations"]:
            report.append("\n## 迁移详情")
            for migration in self.results["migrations"]:
                report.append(f"\n✅ {migration['note']}")
                report.append(f"   目标: {migration['target']}")
                report.append(f"   图片: {migration['images']} 个")
                if migration['attachments'] > 0:
                    report.append(f"   附件: {migration['attachments']} 个")

        if self.results["errors"]:
            report.append("\n## 错误信息")
            for error in self.results["errors"]:
                report.append(f"\n❌ {error['note']}")
                report.append(f"   {error['error']}")

        report.append("\n" + "=" * 60)
        report.append("迁移完成！")
        report.append("=" * 60)

        print("\n".join(report))

        # 保存报告
        report_file = self.source_dir / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(report))

        print(f"\n📄 报告已保存: {report_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='手动笔记迁移工具')
    parser.add_argument('--source-dir', required=True, help='待迁移笔记目录路径')
    parser.add_argument('--target-dir', required=True, help='为知笔记下载根目录路径')
    args = parser.parse_args()

    # 执行迁移
    migrator = ManualNoteMigrator(args.source_dir, args.target_dir)
    migrator.run()


if __name__ == "__main__":
    main()
