#!/usr/bin/env python3
"""
扫描 Wiznote 文件中的 WikiLink 链接
找出所有使用 [[path]] 或 [[path|text]] 格式的链接
"""

import os
import re
from pathlib import Path
from collections import defaultdict
import json

class WikiLinkScanner:
    def __init__(self, source_dir):
        self.source_dir = Path(source_dir)
        self.results = {
            "total_notes": 0,
            "notes_with_wikilinks": 0,
            "total_wikilinks": 0,
            "by_extension": defaultdict(list),
            "missing_files": [],
            "found_files": [],
            "details": []
        }

    def extract_wikilinks(self, content):
        """提取所有 WikiLink 格式的链接"""
        # 匹配 [[path]] 或 [[path|text]] 格式
        pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
        matches = re.findall(pattern, content)
        return matches

    def scan_note(self, note_path):
        """扫描单个笔记"""
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()

            wikilinks = self.extract_wikilinks(content)

            if wikilinks:
                self.results["notes_with_wikilinks"] += 1
                self.results["total_wikilinks"] += len(wikilinks)

                note_info = {
                    "note": str(note_path.relative_to(self.source_dir)),
                    "wikilinks": []
                }

                for link in wikilinks:
                    # 解析路径
                    link_path = link.strip()

                    # 检查文件是否存在
                    full_path = note_path.parent / link_path
                    exists = full_path.exists()

                    # 获取文件扩展名
                    ext = Path(link_path).suffix.lower()

                    # 记录信息
                    link_info = {
                        "path": link_path,
                        "exists": exists,
                        "extension": ext,
                        "full_path": str(full_path) if exists else None
                    }

                    note_info["wikilinks"].append(link_info)

                    # 按扩展名分类
                    self.results["by_extension"][ext].append({
                        "note": str(note_path.relative_to(self.source_dir)),
                        "link": link_path,
                        "exists": exists
                    })

                    # 记录缺失文件
                    if not exists:
                        self.results["missing_files"].append({
                            "note": str(note_path.relative_to(self.source_dir)),
                            "link": link_path,
                            "extension": ext
                        })
                    else:
                        self.results["found_files"].append({
                            "note": str(note_path.relative_to(self.source_dir)),
                            "link": link_path,
                            "extension": ext,
                            "full_path": str(full_path)
                        })

                self.results["details"].append(note_info)

            return len(wikilinks)

        except Exception as e:
            print(f"❌ 读取文件失败 {note_path}: {e}")
            return 0

    def run(self):
        """执行扫描"""
        print("=" * 60)
        print("🔍 WikiLink 扫描工具")
        print("=" * 60)
        print(f"扫描目录: {self.source_dir}")
        print()

        # 获取所有 Markdown 文件
        md_files = list(self.source_dir.rglob("*.md"))
        self.results["total_notes"] = len(md_files)

        print(f"📊 找到 {len(md_files)} 个笔记文件")
        print("正在扫描...")
        print()

        # 扫描每个文件
        for md_file in md_files:
            self.scan_note(md_file)

        # 生成报告
        self.generate_report()

        return self.results

    def generate_report(self):
        """生成报告"""
        report = []
        report.append("\n" + "=" * 60)
        report.append("📊 扫描报告")
        report.append("=" * 60)

        report.append("\n## 总体统计")
        report.append(f"笔记总数: {self.results['total_notes']}")
        report.append(f"包含 WikiLink 的笔记: {self.results['notes_with_wikilinks']}")
        report.append(f"WikiLink 总数: {self.results['total_wikilinks']}")
        report.append(f"找到的文件: {len(self.results['found_files'])}")
        report.append(f"缺失的文件: {len(self.results['missing_files'])}")

        # 按扩展名统计
        if self.results["by_extension"]:
            report.append("\n## 按文件类型统计")
            for ext, links in sorted(self.results["by_extension"].items()):
                found = sum(1 for link in links if link["exists"])
                missing = sum(1 for link in links if not link["exists"])
                report.append(f"\n{ext if ext else '(无扩展名)'}: {len(links)} 个")
                report.append(f"  ✅ 找到: {found}")
                report.append(f"  ❌ 缺失: {missing}")

        # 缺失文件详情
        if self.results["missing_files"]:
            report.append("\n## ❌ 缺失文件列表")
            for item in self.results["missing_files"]:
                report.append(f"\n笔记: {item['note']}")
                report.append(f"  链接: {item['link']}")

        report.append("\n" + "=" * 60)
        report.append("扫描完成！")
        report.append("=" * 60)

        print("\n".join(report))

        # 保存详细结果到 JSON
        output_file = self.source_dir / "wikilink_scan_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n📄 详细结果已保存: {output_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='扫描 WikiLink 引用工具')
    parser.add_argument('--source-dir', required=True, help='为知笔记源目录路径')
    args = parser.parse_args()

    # 执行扫描
    scanner = WikiLinkScanner(args.source_dir)
    scanner.run()


if __name__ == "__main__":
    main()
