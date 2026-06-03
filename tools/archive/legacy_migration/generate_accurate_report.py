#!/usr/bin/env python3
"""
生成准确的下载报告 - 基于 Markdown 内容中的实际引用统计

功能：
  - 扫描 Markdown 文件中的实际图片和附件引用
  - 检查对应的 _files 文件夹中的实际文件
  - 生成准确的缺失统计报告
  - 对比原始下载报告，显示差异

使用方法：
    python3 tools/generate_accurate_report.py

输出：
  - accurate_download_report.md - 准确的下载报告
"""

import os
import sys
from pathlib import Path
import re
from datetime import datetime


def scan_all_resources(download_dir="wiznote_download"):
    """扫描所有笔记的资源情况"""

    download_path = Path(download_dir)
    if not download_path.exists():
        return None

    stats = {
        'total_notes': 0,
        'notes_with_images': 0,
        'notes_with_attachments': 0,
        'notes_with_issues': 0,
        'total_images_found': 0,
        'total_images_downloaded': 0,
        'total_images_missing': 0,
        'total_attachments_found': 0,
        'total_attachments_downloaded': 0,
        'total_attachments_missing': 0,
        'issues': []
    }

    for md_file in download_path.rglob("*.md"):
        stats['total_notes'] += 1

        files_dir = md_file.parent / f"{md_file.stem}_files"

        # 统计 Markdown 中的引用
        with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 图片引用
        image_refs = re.findall(r'!\[.*?\]\((.*?)\)', content)
        # 附件引用
        attachment_refs = re.findall(r'\[.*?\]\((.*?\.(pdf|docx|xlsx|zip|rar|7z|pptx|doc|xls|ppt))\)', content, re.IGNORECASE)
        attachment_refs = [ref[0] for ref in attachment_refs]

        if image_refs:
            stats['notes_with_images'] += 1
            stats['total_images_found'] += len(image_refs)

        if attachment_refs:
            stats['notes_with_attachments'] += 1
            stats['total_attachments_found'] += len(attachment_refs)

        # 统计实际下载的文件
        if files_dir.exists():
            # 图片
            image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
            downloaded_images = sum(1 for f in files_dir.rglob('*') if f.suffix.lower() in image_exts and f.is_file())
            stats['total_images_downloaded'] += downloaded_images

            # 附件
            attachment_exts = {'.pdf', '.docx', '.xlsx', '.zip', '.rar', '.7z', '.pptx', '.doc', '.xls', '.ppt'}
            downloaded_attachments = sum(1 for f in files_dir.rglob('*') if f.suffix.lower() in attachment_exts and f.is_file())
            stats['total_attachments_downloaded'] += downloaded_attachments
        else:
            downloaded_images = 0
            downloaded_attachments = 0

        # 计算缺失
        image_missing = len(image_refs) - downloaded_images
        attachment_missing = len(attachment_refs) - downloaded_attachments

        stats['total_images_missing'] += image_missing
        stats['total_attachments_missing'] += attachment_missing

        # 记录有问题的笔记
        if image_missing > 0 or attachment_missing > 0:
            stats['notes_with_issues'] += 1
            rel_path = md_file.relative_to(download_path)
            stats['issues'].append({
                'file': str(rel_path),
                'images_found': len(image_refs),
                'images_downloaded': downloaded_images,
                'images_missing': image_missing,
                'attachments_found': len(attachment_refs),
                'attachments_downloaded': downloaded_attachments,
                'attachments_missing': attachment_missing,
                'total_missing': image_missing + attachment_missing
            })

    return stats


def main():
    print("="*70)
    print("📊 生成准确的下载报告")
    print("="*70)
    print()

    download_dir = "wiznote_download"

    print("🔍 正在扫描所有笔记...")
    stats = scan_all_resources(download_dir)

    if not stats:
        print("❌ 下载目录不存在")
        return

    # 计算成功率
    image_success_rate = (stats['total_images_downloaded'] / stats['total_images_found'] * 100) if stats['total_images_found'] > 0 else 0
    attachment_success_rate = (stats['total_attachments_downloaded'] / stats['total_attachments_found'] * 100) if stats['total_attachments_found'] > 0 else 0
    note_success_rate = ((stats['total_notes'] - stats['notes_with_issues']) / stats['total_notes'] * 100) if stats['total_notes'] > 0 else 0

    # 显示统计
    print(f"\n📊 扫描结果：\n")

    print(f"{'笔记统计':<30}")
    print(f"{'─'*70}")
    print(f"  总数: {stats['total_notes']} 个")
    print(f"  包含图片的笔记: {stats['notes_with_images']} 个")
    print(f"  包含附件的笔记: {stats['notes_with_attachments']} 个")
    print(f"  有问题的笔记: {stats['notes_with_issues']} 个")
    print(f"  成功率: {note_success_rate:.1f}%\n")

    print(f"{'图片统计':<30}")
    print(f"{'─'*70}")
    print(f"  总数（Markdown 引用）: {stats['total_images_found']} 张")
    print(f"  实际下载: {stats['total_images_downloaded']} 张")
    print(f"  缺失: {stats['total_images_missing']} 张")
    print(f"  成功率: {image_success_rate:.1f}%\n")

    print(f"{'附件统计':<30}")
    print(f"{'─'*70}")
    print(f"  总数（Markdown 引用）: {stats['total_attachments_found']} 个")
    print(f"  实际下载: {stats['total_attachments_downloaded']} 个")
    print(f"  缺失: {stats['total_attachments_missing']} 个")
    print(f"  成功率: {attachment_success_rate:.1f}%\n")

    # 生成报告
    report_file = Path(download_dir).parent / "accurate_download_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# WizNote 下载报告（准确统计）\n\n")
        f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        f.write("## 📊 统计摘要\n\n")

        f.write("### 笔记统计\n\n")
        f.write(f"- 总数: {stats['total_notes']} 个\n")
        f.write(f"- 包含图片的笔记: {stats['notes_with_images']} 个\n")
        f.write(f"- 包含附件的笔记: {stats['notes_with_attachments']} 个\n")
        f.write(f"- 有问题的笔记: {stats['notes_with_issues']} 个（图片/附件缺失）\n")
        f.write(f"- 成功笔记: {stats['total_notes'] - stats['notes_with_issues']} 个\n")
        f.write(f"- 成功率: {note_success_rate:.1f}%\n\n")

        f.write("### 图片统计\n\n")
        f.write(f"- 总数（Markdown 引用）: {stats['total_images_found']} 张\n")
        f.write(f"- 实际下载: {stats['total_images_downloaded']} 张\n")
        f.write(f"- 缺失: {stats['total_images_missing']} 张\n")
        f.write(f"- 成功率: {image_success_rate:.1f}%\n\n")

        f.write("### 附件统计\n\n")
        f.write(f"- 总数（Markdown 引用）: {stats['total_attachments_found']} 个\n")
        f.write(f"- 实际下载: {stats['total_attachments_downloaded']} 个\n")
        f.write(f"- 缺失: {stats['total_attachments_missing']} 个\n")
        f.write(f"- 成功率: {attachment_success_rate:.1f}%\n\n")

        f.write("---\n\n")

        # 问题笔记列表
        if stats['issues']:
            f.write("## ⚠️ 有问题的笔记\n\n")
            f.write(f"共 {len(stats['issues'])} 个笔记存在图片/附件缺失：\n\n")

            # 按严重程度排序
            stats['issues'].sort(key=lambda x: x['total_missing'], reverse=True)

            f.write(f"{'文件名':<40} {'图片缺失':<10} {'附件缺失':<10} {'总计':<6}\n")
            f.write("-" * 70 + "\n")

            for issue in stats['issues'][:30]:  # 只显示前 30 个
                f.write(f"{issue['file'][:38]:<40} ")
                if issue['images_missing'] > 0:
                    f.write(f"❌{issue['images_missing']:<8} ")
                else:
                    f.write(f"{'✓':<10} ")
                if issue['attachments_missing'] > 0:
                    f.write(f"❌{issue['attachments_missing']:<8} ")
                else:
                    f.write(f"{'✓':<10} ")
                f.write(f"{issue['total_missing']:<6}\n")

            if len(stats['issues']) > 30:
                f.write(f"... 还有 {len(stats['issues']) - 30} 个笔记\n")

            f.write("\n---\n\n")

        # 与原始报告对比
        f.write("## 📋 与原始报告对比\n\n")
        f.write("| 项目 | 原始报告 | 实际情况 | 差异 |\n")
        f.write("|------|---------|---------|------|\n")
        f.write(f"| 图片总数 | 615 张 | {stats['total_images_found']} 张 | ")
        if stats['total_images_found'] != 615:
            f.write(f"⚠️ {stats['total_images_found'] - 615:+d} 张 |\n")
        else:
            f.write("✓ |\n")

        f.write(f"| 图片成功 | 615 张 | {stats['total_images_downloaded']} 张 | ")
        if stats['total_images_downloaded'] != 615:
            f.write(f"⚠️ 实际缺失 {stats['total_images_missing']} 张 |\n")
        else:
            f.write("✓ |\n")

        f.write(f"| 图片成功率 | 100.0% | {image_success_rate:.1f}% | ")
        if image_success_rate < 100:
            f.write(f"⚠️ 差 {100 - image_success_rate:.1f}% |\n")
        else:
            f.write("✓ |\n")

        f.write(f"| 附件总数 | 0 个 | {stats['total_attachments_found']} 个 | ")
        if stats['total_attachments_found'] != 0:
            f.write(f"⚠️ {stats['total_attachments_found']:+d} 个 |\n")
        else:
            f.write("✓ |\n")

        f.write("\n---\n\n")

        f.write("## 💡 问题分析\n\n")
        f.write("**为什么原始报告统计错误？**\n\n")
        f.write("1. **API 缺陷**：`/ks/note/download/` API 在某些笔记上不返回 `resources` 字段\n")
        f.write("2. **统计逻辑错误**：原始报告只统计 API 返回的资源数，未检查 Markdown 中的实际引用\n")
        f.write("3. **误判**：当 API 返回 `resources = []` 时，工具认为笔记没有图片\n")
        f.write("4. **实际情况**：Markdown 中有图片引用，但 API 未返回资源列表\n\n")

        f.write("**建议解决方案**\n\n")
        f.write("1. **使用离线导出**（推荐）：在 WizNote 客户端中导出笔记\n")
        f.write("2. **参考准确报告**：使用本报告（`accurate_download_report.md`）了解真实情况\n")
        f.write("3. **查看缺失详情**：查看 `missing_resources_report.txt` 了解具体缺失的笔记\n\n")

    print(f"{'='*70}")
    print(f"📄 准确报告已生成: {report_file}")
    print(f"{'='*70}\n")

    print(f"💡 与原始报告对比：\n")
    print(f"   原始报告显示：")
    print(f"     - 图片总数: 615 张，成功: 615 张，失败: 0 张，成功率: 100%")
    print(f"     - 附件总数: 0 个\n")

    print(f"   实际情况：")
    print(f"     - 图片总数: {stats['total_images_found']} 张，成功: {stats['total_images_downloaded']} 张，缺失: {stats['total_images_missing']} 张")
    print(f"     - 附件总数: {stats['total_attachments_found']} 个，成功: {stats['total_attachments_downloaded']} 个，缺失: {stats['total_attachments_missing']} 个\n")

    if stats['total_images_missing'] > 0 or stats['total_attachments_missing'] > 0:
        print(f"⚠️  原始报告遗漏了 {stats['total_images_missing']} 张图片和 {stats['total_attachments_missing']} 个附件的缺失！\n")

    print(f"📚 相关文件：")
    print(f"   - accurate_download_report.md（本报告）")
    print(f"   - missing_resources_report.txt（详细缺失列表）")
    print(f"   - redownload_list.txt（重新下载列表）")


if __name__ == "__main__":
    main()
