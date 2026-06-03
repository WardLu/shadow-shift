#!/usr/bin/env python3
"""
诊断绘制状态图图片问题
"""

from pathlib import Path

def diagnose():
    """诊断图片问题"""
    note_path = Path("/Users/wardlu/Documents/Ward's Obsidian/02_Areas/产品思考/产品管理/绘制状态图.md")
    files_path = Path("/Users/wardlu/Documents/Ward's Obsidian/02_Areas/产品思考/产品管理/绘制状态图_files")

    print("=" * 60)
    print("🔍 绘制状态图图片问题诊断")
    print("=" * 60)

    # 检查笔记文件
    print(f"\n📝 笔记文件:")
    print(f"   路径: {note_path}")
    print(f"   存在: {'✅' if note_path.exists() else '❌'}")
    print(f"   大小: {note_path.stat().st_size if note_path.exists() else 0} bytes")

    # 检查图片目录
    print(f"\n📁 图片目录:")
    print(f"   路径: {files_path}")
    print(f"   存在: {'✅' if files_path.exists() else '❌'}")

    if files_path.exists():
        images = list(files_path.glob("*.png"))
        print(f"   图片数量: {len(images)}")

        for img in images:
            size = img.stat().st_size
            print(f"   - {img.name}: {size:,} bytes")

    # 检查笔记中的图片链接
    print(f"\n🔗 笔记中的图片链接:")
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    import re
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = re.findall(pattern, content)

    print(f"   找到 {len(matches)} 个图片链接:")
    for alt, path in matches:
        full_path = note_path.parent / path
        exists = full_path.exists()
        print(f"   - {path}")
        print(f"     完整路径: {full_path}")
        print(f"     存在: {'✅' if exists else '❌'}")

    # 测试：创建一个简单的测试文件
    print(f"\n🧪 创建测试文件:")
    test_path = note_path.parent / "测试图片显示.md"
    test_content = f"""# 测试图片显示

测试图片1：
![test](绘制状态图_files/BX42yPsdAKhY_XJ_kGGkr2zF2eAIFE_Hs9vPQW862tU.png)

测试图片2（绝对路径）：
![test](/{files_path}/BX42yPsdAKhY_XJ_kGGkr2zF2eAIFE_Hs9vPQW862tU.png)
"""

    with open(test_path, 'w', encoding='utf-8') as f:
        f.write(test_content)

    print(f"   创建: {test_path}")
    print(f"   请在 Obsidian 中打开这个测试文件，看看图片是否能显示")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    diagnose()
