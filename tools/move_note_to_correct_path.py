#!/usr/bin/env python3
"""
移动绘制状态图笔记到正确的目录结构
"""

import shutil
from pathlib import Path

def move_note(current_note_path, current_files_path, target_dir_path):
    """移动笔记到指定目录"""
    # 当前位置
    current_note = Path(current_note_path)
    current_files = Path(current_files_path)

    # 目标位置
    target_dir = Path(target_dir_path)
    target_note = target_dir / current_note.name
    target_files = target_dir / current_files.name

    print("=" * 60)
    print("📁 移动绘制状态图笔记到正确的目录结构")
    print("=" * 60)
    print(f"当前位置: {current_note}")
    print(f"目标位置: {target_note}")
    print()

    # 检查当前文件是否存在
    if not current_note.exists():
        print(f"❌ 当前笔记不存在: {current_note}")
        return False

    # 创建目标目录
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ 创建目标目录: {target_dir}")

    # 移动笔记文件
    try:
        shutil.move(str(current_note), str(target_note))
        print(f"✅ 移动笔记文件: {target_note}")
    except Exception as e:
        print(f"❌ 移动笔记失败: {e}")
        return False

    # 移动图片目录
    if current_files.exists():
        try:
            shutil.move(str(current_files), str(target_files))
            print(f"✅ 移动图片目录: {target_files}")

            # 统计图片数量
            images = list(target_files.glob("*.png"))
            print(f"   包含图片: {len(images)} 张")
        except Exception as e:
            print(f"❌ 移动图片目录失败: {e}")
            return False

    print("\n" + "=" * 60)
    print("🎉 移动完成！")
    print("=" * 60)
    print(f"笔记位置: {target_note}")
    print(f"图片目录: {target_files}")

    return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='移动笔记到正确的目录结构')
    parser.add_argument('--current-note', required=True, help='当前笔记文件路径')
    parser.add_argument('--current-files', required=True, help='当前附件目录路径')
    parser.add_argument('--target-dir', required=True, help='目标目录路径')
    args = parser.parse_args()

    move_note(args.current_note, args.current_files, args.target_dir)
