#!/usr/bin/env python3
"""
修复 WizNote 迁移后丢失的图片链接
直接从 WizNote 复制带图片的内容段落到 Obsidian
"""

from pathlib import Path
import re
from datetime import datetime

def find_vaults():
    """查找仓库路径"""
    docs_path = Path('/Users/wardlu/Documents')
    wiznote_path = Path('/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download')

    obsidian_vault = None
    for item in docs_path.iterdir():
        if item.is_dir() and 'obsidian' in item.name.lower() and '副本' not in item.name:
            obsidian_vault = item
            break

    return wiznote_path, obsidian_vault

def analyze_image_loss(wiznote_path, obsidian_path, pattern):
    """分析图片丢失情况"""
    # 查找文件
    wiznote_file = None
    obsidian_file = None

    for md in wiznote_path.rglob('*.md'):
        if pattern in md.name:
            wiznote_file = md
            break

    for md in obsidian_path.rglob('*.md'):
        if pattern in md.name:
            obsidian_file = md
            break

    if not wiznote_file or not obsidian_file:
        return None

    # 读取内容
    wiznote_content = wiznote_file.read_text(encoding='utf-8')
    obsidian_content = obsidian_file.read_text(encoding='utf-8')

    # 统计图片
    wiznote_images = re.findall(r'!\[.*?\]\(.*?\)', wiznote_content)
    obsidian_images = re.findall(r'!\[.*?\]\(.*?\)', obsidian_content)

    return {
        'wiznote_file': wiznote_file,
        'obsidian_file': obsidian_file,
        'wiznote_content': wiznote_content,
        'obsidian_content': obsidian_content,
        'wiznote_images': wiznote_images,
        'obsidian_images': obsidian_images,
        'wiznote_count': len(wiznote_images),
        'obsidian_count': len(obsidian_images)
    }

def generate_fix_report(analysis):
    """生成修复报告"""
    print("\n" + "=" * 60)
    print(f"笔记: {analysis['obsidian_file'].name}")
    print("=" * 60)
    print(f"WizNote 图片数: {analysis['wiznote_count']}")
    print(f"Obsidian 图片数: {analysis['obsidian_count']}")
    print(f"丢失图片数: {analysis['wiznote_count'] - analysis['obsidian_count']}")
    print()

    if analysis['wiznote_count'] == 0:
        print("✅ 没有图片丢失")
        return

    # 显示 WizNote 图片示例
    print("WizNote 图片链接示例:")
    for idx, img in enumerate(analysis['wiznote_images'][:10], 1):
        print(f"  {idx}. {img[:60]}...")

    # 检查附件目录
    att_dir = analysis['obsidian_file'].parent / 'attachments'
    if att_dir.exists():
        att_files = list(att_dir.glob('*'))
        print(f"\n附件目录文件数: {len(att_files)}")
        print("文件列表:")
        for f in sorted(att_files)[:10]:
            print(f"  - {f.name}")
    else:
        print("\n⚠️ 附件目录不存在")

    # 建议修复方法
    print("\n" + "=" * 60)
    print("修复建议:")
    print("=" * 60)
    print("1. 手动修复方法:")
    print("   - 打开 WizNote 原始文件查看图片上下文")
    print("   - 在 Obsidian 对应位置插入图片")
    print("   - 图片路径格式: ![[attachments/文件名]]")
    print()
    print("2. 或使用 Obsidian 插件:")
    print("   - Image Auto Upload: 从剪贴板粘贴图片")
    print("   - File Cleaner: 清理和修复附件")
    print()

def main():
    print("=" * 60)
    print("WizNote 图片丢失诊断工具")
    print("=" * 60)
    print()

    wiznote_path, obsidian_path = find_vaults()

    # 查找有问题的笔记
    problem_notes = [
        '严琦东',
        # 添加其他有问题的笔记关键词
    ]

    for pattern in problem_notes:
        analysis = analyze_image_loss(wiznote_path, obsidian_path, pattern)
        if analysis:
            generate_fix_report(analysis)
        else:
            print(f"\n❌ 未找到笔记: {pattern}")

    print("\n" + "=" * 60)
    print("下一步操作:")
    print("=" * 60)
    print("1. 手动修复图片链接")
    print("2. 或提供更多信息以便自动修复")
    print()

if __name__ == '__main__':
    main()
