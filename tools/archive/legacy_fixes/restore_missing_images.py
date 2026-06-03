#!/usr/bin/env python3
"""
智能修复 WizNote 迁移后丢失的图片链接
根据 WizNote 原始文件的内容结构，恢复图片到 Obsidian
"""

from pathlib import Path
import re

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

def extract_wiznote_images_with_context(content):
    """提取 WizNote 图片及其上下文段落"""
    # 分割成段落
    paragraphs = content.split('\n\n')

    image_paragraphs = []
    current_para = []

    for para in paragraphs:
        # 检查是否包含图片
        images = re.findall(r'!\[.*?\]\((.*?)\)', para)

        if images:
            # 这是一个包含图片的段落
            image_paragraphs.append({
                'paragraph': para,
                'images': images,
                'type': 'image_para'
            })
        else:
            # 这是普通文本段落
            # 提取关键词（用于匹配）
            keywords = re.findall(r'[\u4e00-\u9fa5A-Za-z0-9]+', para)
            if keywords:
                image_paragraphs.append({
                    'paragraph': para,
                    'keywords': [kw for kw in keywords if len(kw) > 3][:5],
                    'type': 'text_para'
                })

    return image_paragraphs

def fix_note(wiznote_file, obsidian_file, dry_run=True):
    """修复单个笔记"""
    print(f'\n处理: {obsidian_file.name}')
    print(f'  WizNote: {wiznote_file.name}')
    print(f'  Obsidian: {obsidian_file.name}')

    # 读取内容
    wiznote_content = wiznote_file.read_text(encoding='utf-8')
    obsidian_content = obsidian_file.read_text(encoding='utf-8')

    # 统计
    wiznote_images = re.findall(r'!\[.*?\]\(.*?\)', wiznote_content)
    obsidian_images = re.findall(r'!\[.*?\]\(.*?\)', obsidian_content)

    print(f'  WizNote 图片: {len(wiznote_images)} 个')
    print(f'  Obsidian 图片: {len(obsidian_images)} 个')
    print(f'  需要修复: {len(wiznote_images) - len(obsidian_images)} 个')

    if len(wiznote_images) == len(obsidian_images):
        print('  ✅ 图片数量一致，无需修复')
        return

    # 检查附件目录
    att_dir = obsidian_file.parent / 'attachments'
    if not att_dir.exists():
        print('  ❌ 附件目录不存在')
        return

    # 获取附件列表
    attachments = {f.name: f for f in att_dir.glob('*')}
    print(f'  附件目录: {len(attachments)} 个文件')

    # 提取 WizNote 的图片段落
    wiznote_paras = extract_wiznote_images_with_context(wiznote_content)

    # 找出包含图片的段落
    image_paras = [p for p in wiznote_paras if p['type'] == 'image_para']
    print(f'  WizNote 图片段落: {len(image_paras)} 个')

    # 修复策略：直接在文件末尾添加缺失的图片
    # （更智能的方法需要复杂的文本匹配）

    fixed_count = 0
    new_content = obsidian_content

    # 添加图片恢复区
    image_section = '\n\n---\n\n## 📷 图片（从 WizNote 恢复）\n\n'

    for img_para in image_paras:
        for img_name in img_para['images']:
            # 检查附件是否存在
            if img_name in attachments:
                # 转换为 Obsidian 格式
                obsidian_link = f'![[attachments/{img_name}]]\n\n'
                image_section += obsidian_link
                fixed_count += 1

    if fixed_count > 0:
        if dry_run:
            print(f'  [DRY RUN] 将添加 {fixed_count} 个图片链接')
            print(f'\n  预览新增内容:')
            print('  ' + '\n  '.join(image_section.split('\n')[:20]))
        else:
            new_content += image_section
            obsidian_file.write_text(new_content, encoding='utf-8')
            print(f'  ✅ 添加了 {fixed_count} 个图片链接')
    else:
        print('  ⚠️ 没有找到可恢复的图片')

def main():
    print("=" * 60)
    print("WizNote 图片链接智能修复工具")
    print("=" * 60)
    print()

    wiznote_path, obsidian_path = find_vaults()

    # 查找要修复的笔记
    target_notes = [
        ('严琦东', '人人都是开发者'),
    ]

    print(f'计划处理 {len(target_notes)} 个笔记\n')

    # 查找文件
    for pattern, _ in target_notes:
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

        if wiznote_file and obsidian_file:
            print("=" * 60)
            print("第一步：预览修复（DRY RUN）")
            print("=" * 60)
            fix_note(wiznote_file, obsidian_file, dry_run=True)

    print("\n" + "=" * 60)
    print("预览完成")
    print("=" * 60)
    print("\n如需执行实际修复，请设置 dry_run=False")
    print()

if __name__ == '__main__':
    main()
