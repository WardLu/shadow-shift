#!/usr/bin/env python3
"""
WizNote 迁移完整性检查工具
检查笔记中的图片和附件链接是否正常迁移到 Obsidian
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

class MigrationChecker:
    def __init__(self, source_dir):
        self.source_dir = Path(source_dir)
        self.results = {
            "total_notes": 0,
            "notes_with_images": 0,
            "notes_with_attachments": 0,
            "total_image_links": 0,
            "total_attachment_links": 0,
            "missing_images": [],
            "missing_attachments": [],
            "broken_links": [],
            "notes_status": {},
            "resource_dirs": []
        }

    def extract_image_links(self, content):
        """提取 Markdown 中的图片链接"""
        # 匹配 ![alt](path) 格式
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.findall(pattern, content)
        return [(alt, path) for alt, path in matches]

    def extract_attachment_links(self, content):
        """提取 Markdown 中的附件链接（非图片）"""
        # 匹配 [text](path) 格式，排除图片
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(pattern, content)

        attachments = []
        for text, path in matches:
            # 排除图片和 http/https 链接
            if not path.startswith(('http://', 'https://')):
                ext = Path(path).suffix.lower()
                if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']:
                    attachments.append((text, path))
        return attachments

    def check_resource_exists(self, note_path, resource_path):
        """检查资源文件是否存在"""
        note_dir = note_path.parent

        # 尝试多种可能的路径
        possible_paths = [
            note_dir / resource_path,  # 相对于笔记的路径
            self.source_dir / resource_path,  # 相对于源目录的路径
            note_dir / resource_path.replace('%20', ' '),  # URL 编码的空格
        ]

        for path in possible_paths:
            if path.exists():
                return True, str(path)

        return False, None

    def analyze_note(self, note_path):
        """分析单个笔记文件"""
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()

            note_result = {
                "path": str(note_path.relative_to(self.source_dir)),
                "has_images": False,
                "has_attachments": False,
                "image_links": [],
                "attachment_links": [],
                "missing_images": [],
                "missing_attachments": [],
                "status": "complete"
            }

            # 提取图片链接
            image_links = self.extract_image_links(content)
            if image_links:
                note_result["has_images"] = True
                self.results["notes_with_images"] += 1

                for alt, img_path in image_links:
                    self.results["total_image_links"] += 1
                    exists, actual_path = self.check_resource_exists(note_path, img_path)

                    link_info = {
                        "alt": alt,
                        "path": img_path,
                        "exists": exists,
                        "actual_path": actual_path
                    }
                    note_result["image_links"].append(link_info)

                    if not exists:
                        note_result["missing_images"].append(img_path)
                        self.results["missing_images"].append({
                            "note": str(note_path.relative_to(self.source_dir)),
                            "image": img_path
                        })
                        note_result["status"] = "incomplete"

            # 提取附件链接
            attachment_links = self.extract_attachment_links(content)
            if attachment_links:
                note_result["has_attachments"] = True
                self.results["notes_with_attachments"] += 1

                for text, att_path in attachment_links:
                    self.results["total_attachment_links"] += 1
                    exists, actual_path = self.check_resource_exists(note_path, att_path)

                    link_info = {
                        "text": text,
                        "path": att_path,
                        "exists": exists,
                        "actual_path": actual_path
                    }
                    note_result["attachment_links"].append(link_info)

                    if not exists:
                        note_result["missing_attachments"].append(att_path)
                        self.results["missing_attachments"].append({
                            "note": str(note_path.relative_to(self.source_dir)),
                            "attachment": att_path
                        })
                        note_result["status"] = "incomplete"

            self.results["notes_status"][str(note_path.relative_to(self.source_dir))] = note_result
            return note_result

        except Exception as e:
            self.results["broken_links"].append({
                "note": str(note_path.relative_to(self.source_dir)),
                "error": str(e)
            })
            return None

    def scan_directory(self):
        """扫描目录中的所有 Markdown 文件和资源目录"""
        print(f"🔍 扫描目录: {self.source_dir}")
        print("-" * 60)

        # 扫描 Markdown 文件
        md_files = list(self.source_dir.rglob("*.md"))
        self.results["total_notes"] = len(md_files)
        print(f"📝 找到 {len(md_files)} 个 Markdown 文件")

        # 扫描资源目录
        resource_dirs = list(self.source_dir.rglob("*_files"))
        self.results["resource_dirs"] = [str(d.relative_to(self.source_dir)) for d in resource_dirs if d.is_dir()]
        print(f"📁 找到 {len(resource_dirs)} 个资源目录")

        # 分析每个笔记
        print(f"\n📊 分析笔记内容...")
        for md_file in md_files:
            self.analyze_note(md_file)

        return self.results

    def generate_report(self):
        """生成分析报告"""
        report = []
        report.append("=" * 60)
        report.append("📊 WizNote 迁移完整性检查报告")
        report.append("=" * 60)
        report.append(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"源目录: {self.source_dir}")
        report.append("")

        # 总体统计
        report.append("## 📈 总体统计")
        report.append("-" * 60)
        report.append(f"Markdown 文件总数: {self.results['total_notes']}")
        report.append(f"资源目录总数: {len(self.results['resource_dirs'])}")
        report.append(f"包含图片的笔记: {self.results['notes_with_images']}")
        report.append(f"包含附件的笔记: {self.results['notes_with_attachments']}")
        report.append(f"图片链接总数: {self.results['total_image_links']}")
        report.append(f"附件链接总数: {self.results['total_attachment_links']}")
        report.append("")

        # 完整性状态
        complete_notes = sum(1 for n in self.results["notes_status"].values()
                           if n["status"] == "complete")
        incomplete_notes = self.results['total_notes'] - complete_notes

        report.append("## ✅ 迁移状态")
        report.append("-" * 60)
        report.append(f"完整迁移: {complete_notes}/{self.results['total_notes']} "
                     f"({complete_notes/self.results['total_notes']*100:.1f}%)")
        report.append(f"存在问题: {incomplete_notes}/{self.results['total_notes']} "
                     f"({incomplete_notes/self.results['total_notes']*100:.1f}%)")
        report.append("")

        # 缺失资源详情
        if self.results["missing_images"]:
            report.append("## 🖼️ 缺失的图片")
            report.append("-" * 60)
            for item in self.results["missing_images"]:
                report.append(f"❌ {item['note']}")
                report.append(f"   缺失图片: {item['image']}")
            report.append("")

        if self.results["missing_attachments"]:
            report.append("## 📎 缺失的附件")
            report.append("-" * 60)
            for item in self.results["missing_attachments"]:
                report.append(f"❌ {item['note']}")
                report.append(f"   缺失附件: {item['attachment']}")
            report.append("")

        # 有问题的笔记详情
        if incomplete_notes > 0:
            report.append("## ⚠️ 有问题的笔记")
            report.append("-" * 60)
            for note_path, note_info in self.results["notes_status"].items():
                if note_info["status"] == "incomplete":
                    report.append(f"\n📝 {note_path}")
                    if note_info["missing_images"]:
                        report.append(f"   缺失图片: {len(note_info['missing_images'])} 个")
                        for img in note_info["missing_images"]:
                            report.append(f"      - {img}")
                    if note_info["missing_attachments"]:
                        report.append(f"   缺失附件: {len(note_info['missing_attachments'])} 个")
                        for att in note_info["missing_attachments"]:
                            report.append(f"      - {att}")
            report.append("")

        # 资源目录列表
        if self.results["resource_dirs"]:
            report.append("## 📁 资源目录")
            report.append("-" * 60)
            for res_dir in self.results["resource_dirs"]:
                report.append(f"  {res_dir}")
            report.append("")

        # 建议
        report.append("## 💡 建议")
        report.append("-" * 60)
        if incomplete_notes == 0:
            report.append("✅ 所有笔记都已完整迁移，没有发现缺失的图片或附件！")
        else:
            report.append("⚠️ 发现以下问题需要处理：")
            if self.results["missing_images"]:
                report.append(f"1. 有 {len(self.results['missing_images'])} 个图片链接指向的文件不存在")
                report.append("   - 检查图片是否在 WizNote 导出时被遗漏")
                report.append("   - 可能需要重新导出或手动补充图片")
            if self.results["missing_attachments"]:
                report.append(f"2. 有 {len(self.results['missing_attachments'])} 个附件链接指向的文件不存在")
                report.append("   - 检查附件是否在 WizNote 导出时被遗漏")
        report.append("")

        report.append("=" * 60)
        report.append("检查完成！")
        report.append("=" * 60)

        return "\n".join(report)


def main():
    import sys

    # 设置源目录
    source_dir = "/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download/技术笔记/产品经理PM"

    if len(sys.argv) > 1:
        source_dir = sys.argv[1]

    # 执行检查
    checker = MigrationChecker(source_dir)
    checker.scan_directory()
    report = checker.generate_report()

    # 输出报告
    print(report)

    # 保存报告到文件
    report_file = Path(source_dir) / f"migration_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📄 报告已保存到: {report_file}")


if __name__ == "__main__":
    main()
