#!/usr/bin/env python3
"""
智能笔记迁移工具
检查并迁移 WizNote 笔记到 Obsidian，只迁移有问题的笔记
"""

import os
import re
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

class SmartNoteMigrator:
    def __init__(self, source_dir, vault_dir):
        self.source_dir = Path(source_dir)
        self.vault_dir = Path(vault_dir)
        self.results = {
            "total_notes": 0,
            "already_migrated": 0,
            "need_migration": 0,
            "migrated": 0,
            "errors": [],
            "migration_list": []
        }

    def calculate_file_hash(self, file_path):
        """计算文件的 MD5 哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def extract_image_links(self, content):
        """提取 Markdown 中的图片链接"""
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.findall(pattern, content)
        return [(alt, path) for alt, path in matches if not path.startswith(('http://', 'https://'))]

    def extract_attachment_links(self, content):
        """提取 Markdown 中的附件链接（标准格式）"""
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(pattern, content)

        attachments = []
        for text, path in matches:
            if not path.startswith(('http://', 'https://')):
                ext = Path(path).suffix.lower()
                if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']:
                    attachments.append((text, path, 'markdown'))
        return attachments

    def extract_wikilink_attachments(self, content):
        """提取 WikiLink 格式的附件链接 [[path|text]] 或 [[path]]"""
        pattern = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
        matches = re.findall(pattern, content)

        attachments = []
        for path, text in matches:
            path = path.strip()
            # 跳过无扩展名的链接（可能是误识别）
            ext = Path(path).suffix.lower()
            if ext and ext not in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.md']:
                display_text = text.strip() if text else Path(path).name
                attachments.append((display_text, path, 'wikilink'))
        return attachments

    def check_resource_exists(self, note_path, resource_path, check_source=False):
        """检查资源文件是否存在"""
        note_dir = note_path.parent

        # 尝试多种可能的路径
        possible_paths = [
            note_dir / resource_path,
        ]

        # 可选：也检查源目录
        if check_source:
            possible_paths.append(self.source_dir / resource_path)

        for path in possible_paths:
            if path.exists():
                return True, str(path)

        return False, None

    def check_note_integrity(self, source_note, target_note):
        """检查目标笔记的完整性"""
        if not target_note.exists():
            return False, "目标文件不存在"

        # 读取源笔记内容（检查是否有附件）
        try:
            with open(source_note, 'r', encoding='utf-8') as f:
                source_content = f.read()
        except Exception as e:
            return False, f"无法读取源文件: {e}"

        # 读取目标笔记内容
        try:
            with open(target_note, 'r', encoding='utf-8') as f:
                target_content = f.read()
        except Exception as e:
            return False, f"无法读取目标文件: {e}"

        # 提取图片链接
        image_links = self.extract_image_links(target_content)
        attachment_links = self.extract_attachment_links(target_content)
        wikilink_attachments = self.extract_wikilink_attachments(source_content)

        # 检查图片是否存在
        missing_images = []
        for alt, img_path in image_links:
            exists, _ = self.check_resource_exists(target_note, img_path)
            if not exists:
                missing_images.append(img_path)

        # 检查附件是否存在
        missing_attachments = []
        for text, att_path, link_type in attachment_links:
            exists, _ = self.check_resource_exists(target_note, att_path)
            if not exists:
                missing_attachments.append(att_path)

        # 检查 WikiLink 附件是否存在
        missing_wikilinks = []
        for text, att_path, link_type in wikilink_attachments:
            # 在目标笔记中，WikiLink 应该已经被转换为标准 Markdown 链接
            # 所以检查转换后的链接是否存在
            att_name = Path(att_path).name
            converted_path = f"{target_note.parent.name}_files/{att_name}"

            # 也检查原始路径
            possible_paths = [
                f"{target_note.stem}_files/{att_name}",
                att_path
            ]

            found = False
            for check_path in possible_paths:
                exists, _ = self.check_resource_exists(target_note, check_path)
                if exists:
                    found = True
                    break

            if not found:
                # 检查文件是否在源目录存在但未复制
                source_att = source_note.parent / att_path
                if source_att.exists():
                    missing_wikilinks.append(att_path)

        if missing_images or missing_attachments or missing_wikilinks:
            issues = []
            if missing_images:
                issues.append(f"缺失 {len(missing_images)} 张图片")
            if missing_attachments:
                issues.append(f"缺失 {len(missing_attachments)} 个附件")
            if missing_wikilinks:
                issues.append(f"缺失 {len(missing_wikilinks)} 个 WikiLink 附件")
            return False, ", ".join(issues)

        return True, "完整"

    def find_target_note(self, source_note):
        """在 Obsidian vault 中查找对应的笔记"""
        note_name = source_note.name

        # 在 vault 中递归搜索
        for md_file in self.vault_dir.rglob("*.md"):
            if md_file.name == note_name:
                return md_file

        return None

    def migrate_note(self, source_note, target_note=None):
        """迁移单个笔记及其资源"""
        note_name = source_note.name
        print(f"\n📝 处理笔记: {note_name}")

        # 如果没有提供目标笔记，查找或创建
        if target_note is None:
            target_note = self.find_target_note(source_note)

        if target_note is None:
            # 创建目标路径（在 02_Areas/技术笔记/产品经理PM 下）
            relative_path = source_note.relative_to(self.source_dir)
            target_note = self.vault_dir / "02_Areas" / relative_path

            # 确保目标目录存在
            target_note.parent.mkdir(parents=True, exist_ok=True)

        # 检查目标笔记的完整性
        is_complete, status = self.check_note_integrity(source_note, target_note)

        if is_complete:
            print(f"  ✅ 已完整迁移: {status}")
            self.results["already_migrated"] += 1
            return True

        print(f"  ⚠️  需要迁移: {status}")

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

        # 准备目标资源目录
        note_stem = target_note.stem
        target_files_dir = target_note.parent / f"{note_stem}_files"

        # 如果目标资源目录不存在，创建它
        if not target_files_dir.exists():
            target_files_dir.mkdir(parents=True, exist_ok=True)
            print(f"  📁 创建资源目录: {target_files_dir.name}")

        # 提取资源链接
        image_links = self.extract_image_links(source_content)
        attachment_links = self.extract_attachment_links(source_content)
        wikilink_attachments = self.extract_wikilink_attachments(source_content)

        print(f"  🖼️  图片链接: {len(image_links)} 个")
        print(f"  📎 Markdown 附件链接: {len(attachment_links)} 个")
        print(f"  📎 WikiLink 附件链接: {len(wikilink_attachments)} 个")

        # 复制资源并更新链接
        new_content = source_content
        copied_images = 0
        copied_attachments = 0

        # 处理图片
        for alt, img_path in image_links:
            source_img = source_note.parent / img_path

            if not source_img.exists():
                print(f"    ⚠️  源图片不存在: {img_path}")
                continue

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

        print(f"  ✅ 复制图片: {copied_images}/{len(image_links)} 个")

        # 处理附件
        for text, att_path in attachment_links:
            source_att = source_note.parent / att_path

            if not source_att.exists():
                print(f"    ⚠️  源附件不存在: {att_path}")
                continue

            att_name = Path(att_path).name
            target_att = target_files_dir / att_name

            try:
                shutil.copy2(source_att, target_att)
                copied_attachments += 1

                old_link = f"]({att_path})"
                new_link = f"]({target_files_dir.name}/{att_name})"
                new_content = new_content.replace(old_link, new_link)

            except Exception as e:
                print(f"    ❌ 复制附件失败 {att_name}: {e}")

        if attachment_links:
            print(f"  ✅ 复制附件: {copied_attachments}/{len(attachment_links)} 个")

        # 处理 WikiLink 附件
        copied_wikilinks = 0
        for text, att_path, link_type in wikilink_attachments:
            source_att = source_note.parent / att_path

            if not source_att.exists():
                print(f"    ⚠️  源附件不存在: {att_path}")
                continue

            att_name = Path(att_path).name
            target_att = target_files_dir / att_name

            try:
                shutil.copy2(source_att, target_att)
                copied_wikilinks += 1

                # 更新链接 - 将 WikiLink 转换为标准 Markdown 链接
                old_link = f"[[{att_path}|{text}]]"
                new_link = f"[{text}]({target_files_dir.name}/{att_name})"
                new_content = new_content.replace(old_link, new_link)

                # 也处理无文本的 WikiLink 格式
                old_link_simple = f"[[{att_path}]]"
                new_content = new_content.replace(old_link_simple, new_link)

            except Exception as e:
                print(f"    ❌ 复制附件失败 {att_name}: {e}")

        if wikilink_attachments:
            print(f"  ✅ 复制 WikiLink 附件: {copied_wikilinks}/{len(wikilink_attachments)} 个")
            copied_attachments += copied_wikilinks

        # 写入新内容（不备份，因为用户要求保留源文件）
        try:
            with open(target_note, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  ✅ 更新目标笔记")
        except Exception as e:
            print(f"  ❌ 写入失败: {e}")
            self.results["errors"].append({
                "note": note_name,
                "error": f"写入失败: {e}"
            })
            return False

        # 记录统计
        self.results["migrated"] += 1
        self.results["migration_list"].append({
            "source": str(source_note.relative_to(self.source_dir)),
            "target": str(target_note.relative_to(self.vault_dir)),
            "images": copied_images,
            "attachments": copied_attachments,
            "reason": status
        })

        return True

    def run(self):
        """执行迁移"""
        print("=" * 60)
        print("🚀 智能笔记迁移工具")
        print("=" * 60)
        print(f"源目录: {self.source_dir}")
        print(f"目标目录: {self.vault_dir}")
        print()

        # 获取所有 Markdown 文件
        md_files = list(self.source_dir.rglob("*.md"))
        self.results["total_notes"] = len(md_files)

        print(f"📊 找到 {len(md_files)} 个笔记文件")
        print()

        # 检查每个笔记
        for md_file in md_files:
            # 查找目标笔记
            target_note = self.find_target_note(md_file)

            if target_note:
                # 检查完整性
                is_complete, status = self.check_note_integrity(md_file, target_note)

                if is_complete:
                    print(f"\n📝 {md_file.name}")
                    print(f"  ✅ 已完整迁移，跳过")
                    self.results["already_migrated"] += 1
                else:
                    # 需要迁移
                    self.results["need_migration"] += 1
                    self.migrate_note(md_file, target_note)
            else:
                # 目标不存在，需要迁移
                self.results["need_migration"] += 1
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
        report.append(f"已完整迁移: {self.results['already_migrated']}")
        report.append(f"需要迁移: {self.results['need_migration']}")
        report.append(f"本次迁移: {self.results['migrated']}")

        if self.results["migration_list"]:
            report.append("\n## 迁移详情")
            for item in self.results["migration_list"]:
                report.append(f"\n✅ {item['source']}")
                report.append(f"   目标: {item['target']}")
                report.append(f"   原因: {item['reason']}")
                report.append(f"   图片: {item['images']} 个")
                if item['attachments'] > 0:
                    report.append(f"   附件: {item['attachments']} 个")

        if self.results["errors"]:
            report.append("\n## 错误信息")
            for error in self.results["errors"]:
                report.append(f"\n❌ {error['note']}")
                report.append(f"   {error['error']}")

        report.append("\n" + "=" * 60)
        report.append("迁移完成！")
        report.append("=" * 60)
        report.append("\n💡 提示：源文件已保留在原位置，可进行人工校验")

        print("\n".join(report))

        # 保存报告
        report_file = self.source_dir / f"obsidian_migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(report))

        print(f"\n📄 报告已保存: {report_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='智能笔记迁移工具')
    parser.add_argument('--source-dir', required=True, help='为知笔记源目录路径')
    parser.add_argument('--vault-dir', required=True, help='Obsidian vault 目录路径')
    args = parser.parse_args()

    # 执行迁移
    migrator = SmartNoteMigrator(args.source_dir, args.vault_dir)
    migrator.run()


if __name__ == "__main__":
    main()
