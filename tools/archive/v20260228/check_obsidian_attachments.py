#!/usr/bin/env python3
"""
检查 Wiznote 中 WikiLink 链接的文件在 Obsidian 中是否存在
"""

import os
import json
from pathlib import Path

def check_obsidian_attachments():
    # 读取扫描结果
    scan_file = "/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download/技术笔记/产品经理PM/wikilink_scan_results.json"
    obsidian_dir = Path("/Users/wardlu/Documents/Ward's Obsidian/02_Areas/产品思考/产品管理")

    with open(scan_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    print("=" * 60)
    print("🔍 检查 Obsidian 中的附件")
    print("=" * 60)
    print()

    # 检查每个找到的文件
    issues = []
    for item in results["found_files"]:
        note_name = Path(item["note"]).stem
        link = item["link"]
        ext = item["extension"]

        # 跳过无扩展名的（可能是误识别）
        if not ext:
            continue

        print(f"\n📝 笔记: {note_name}")
        print(f"   附件: {link}")

        # 查找对应的 Obsidian 笔记
        obsidian_note = None
        for md_file in obsidian_dir.rglob("*.md"):
            if md_file.stem == note_name:
                obsidian_note = md_file
                break

        if not obsidian_note:
            print(f"   ❌ Obsidian 中未找到笔记")
            issues.append({
                "note": note_name,
                "link": link,
                "issue": "笔记不存在"
            })
            continue

        # 检查附件是否存在
        attachment_path = obsidian_note.parent / link
        if attachment_path.exists():
            print(f"   ✅ 附件存在: {attachment_path}")
        else:
            print(f"   ❌ 附件不存在: {attachment_path}")
            issues.append({
                "note": note_name,
                "obsidian_note": str(obsidian_note),
                "link": link,
                "source_file": item["full_path"],
                "issue": "附件不存在"
            })

    # 生成报告
    print("\n" + "=" * 60)
    print("📊 检查结果")
    print("=" * 60)

    if issues:
        print(f"\n❌ 发现 {len(issues)} 个问题：")
        for issue in issues:
            print(f"\n笔记: {issue['note']}")
            print(f"  附件: {issue['link']}")
            print(f"  问题: {issue['issue']}")
            if 'source_file' in issue:
                print(f"  源文件: {issue['source_file']}")
    else:
        print("\n✅ 所有附件都存在！")

    # 保存结果
    output_file = Path("/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download/技术笔记/产品经理PM/obsidian_check_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(issues, f, ensure_ascii=False, indent=2)

    print(f"\n📄 详细结果已保存: {output_file}")

    return issues


if __name__ == "__main__":
    check_obsidian_attachments()
