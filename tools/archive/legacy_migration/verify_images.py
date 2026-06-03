#!/usr/bin/env python3
"""
验证绘制状态图笔记的图片链接
"""

from pathlib import Path
import re

def verify_images():
    """验证图片链接和文件是否匹配"""
    note_path = Path("/Users/wardlu/Documents/Ward's Obsidian/02_Areas/产品思考/产品管理/绘制状态图.md")
    files_path = Path("/Users/wardlu/Documents/Ward's Obsidian/02_Areas/产品思考/产品管理/绘制状态图_files")

    print("=" * 60)
    print("🔍 验证绘制状态图图片")
    print("=" * 60)
    print(f"笔记路径: {note_path}")
    print(f"图片目录: {files_path}")
    print()

    # 读取笔记
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取图片链接
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = re.findall(pattern, content)

    print(f"📝 笔记中的图片链接: {len(matches)} 个\n")

    # 获取实际图片文件
    actual_images = list(files_path.glob("*.png"))
    print(f"📁 图片目录中的文件: {len(actual_images)} 个\n")

    # 验证每个链接
    print("链接验证:")
    for i, (alt, link) in enumerate(matches, 1):
        filename = Path(link).name
        full_path = note_path.parent / link
        exists = full_path.exists()

        print(f"{i}. {filename}")
        print(f"   链接: {link}")
        print(f"   存在: {'✅' if exists else '❌'}")

        if exists:
            size = full_path.stat().st_size
            print(f"   大小: {size:,} bytes")
        print()

    # 检查多余的图片文件
    linked_files = {Path(link).name for _, link in matches}
    actual_files = {img.name for img in actual_images}

    extra_files = actual_files - linked_files
    if extra_files:
        print(f"⚠️  未链接的图片文件: {len(extra_files)} 个")
        for f in extra_files:
            print(f"   - {f}")

    print("\n" + "=" * 60)
    print("✅ 验证完成")
    print("=" * 60)

if __name__ == "__main__":
    verify_images()
