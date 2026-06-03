#!/usr/bin/env python3
"""
重新迁移单个笔记到 Obsidian
"""

import os
import re
import shutil
from pathlib import Path

def migrate_single_note(source_note_path, source_images_dir_path, vault_dir_path, target_subdir="02_Areas"):
    """迁移单个笔记"""
    # 源文件路径
    source_note = Path(source_note_path)
    source_images_dir = Path(source_images_dir_path)

    # 目标路径
    vault_dir = Path(vault_dir_path)
    target_note = vault_dir / target_subdir / source_note.name
    target_files_dir = vault_dir / target_subdir / f"{source_note.stem}_files"

    print("=" * 60)
    print("🔄 重新迁移绘制状态图笔记")
    print("=" * 60)
    print(f"源文件: {source_note}")
    print(f"目标文件: {target_note}")
    print()

    # 读取源笔记内容
    with open(source_note, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取图片链接
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = re.findall(pattern, content)

    print(f"📝 找到 {len(matches)} 个图片链接")

    # 确保目标资源目录存在
    if not target_files_dir.exists():
        target_files_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 创建资源目录: {target_files_dir}")

    # 复制图片并更新链接
    new_content = content
    copied_count = 0

    for alt, img_path in matches:
        if img_path.startswith(('http://', 'https://')):
            continue

        # 源图片路径
        img_name = Path(img_path).name
        source_img = source_images_dir / img_name

        if not source_img.exists():
            print(f"  ⚠️  图片不存在: {img_name}")
            continue

        # 目标图片路径
        target_img = target_files_dir / img_name

        # 复制图片
        try:
            shutil.copy2(source_img, target_img)
            copied_count += 1
            print(f"  ✅ 复制图片: {img_name}")

            # 更新链接
            old_link = f"]({img_path})"
            new_link = f"]({target_files_dir.name}/{img_name})"
            new_content = new_content.replace(old_link, new_link)

        except Exception as e:
            print(f"  ❌ 复制失败 {img_name}: {e}")

    print(f"\n✅ 复制图片: {copied_count}/{len(matches)} 张")

    # 写入新内容
    try:
        with open(target_note, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"\n✅ 更新目标笔记: {target_note}")
    except Exception as e:
        print(f"\n❌ 写入失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("🎉 迁移完成！")
    print("=" * 60)
    print(f"目标位置: {target_note}")
    print(f"图片目录: {target_files_dir}")
    print(f"图片数量: {copied_count} 张")

    return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='重新迁移单个笔记到 Obsidian')
    parser.add_argument('--source-note', required=True, help='源笔记文件路径')
    parser.add_argument('--source-images', required=True, help='源图片目录路径')
    parser.add_argument('--vault-dir', required=True, help='Obsidian vault 目录路径')
    parser.add_argument('--target-subdir', default='02_Areas', help='目标子目录（默认: 02_Areas）')
    args = parser.parse_args()

    migrate_single_note(args.source_note, args.source_images, args.vault_dir, args.target_subdir)
