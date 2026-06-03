#!/usr/bin/env python3
"""
修复 WizNote 迁移后丢失的图片链接
从 WizNote 原始笔记中提取图片链接，并插入到 Obsidian 对应位置
"""

from pathlib import Path
import re
from datetime import datetime

# 配置路径
def find_vaults():
    """查找 WizNote 和 Obsidian 仓库"""
    docs_path = Path('/Users/wardlu/Documents')
    wiznote_path = Path('/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download')

    obsidian_vault = None
    for item in docs_path.iterdir():
        if item.is_dir() and 'obsidian' in item.name.lower() and '副本' not in item.name:
            obsidian_vault = item
            break

    return wiznote_path, obsidian_vault

def extract_image_blocks(content):
    """提取图片块（包含上下文）"""
    # 匹配图片及其前后的上下文
    pattern = r'(.*?)(!\[.*?\]\(.*?\))'
    matches = []

    for match in re.finditer(pattern, content, re.DOTALL):
        before = match.group(1)
        image_link = match.group(2)

        # 提取关键上下文（最后 100 个字符）
        context = before[-100:] if len(before) > 100 else before

        matches.append({
            'link': image_link,
            'context': context.strip()
        })

    return matches

def find_matching_paragraph(obs_content, wiznote_paragraph):
    """在 Obsidian 内容中查找匹配的段落"""
    # 提取段落的关键词
    keywords = re.findall(r'[\u4e00-\u9fa5]+', wiznote_paragraph)
    if not keywords:
        return None

    # 在 Obsidian 中搜索包含这些关键词的段落
    for keyword in keywords[:5]:  # 只取前 5 个关键词
        if len(keyword) > 3:  # 忇略太短的关键词
            pattern = re.escape(keyword)
            matches = list(re.finditer(pattern, obs_content))
            if matches:
                return matches[0].start()

    return None

def fix_note(wiznote_path, obsidian_path, note_name_pattern, dry_run=True):
    """修复单个笔记的图片链接"""
    # 查找 WizNote 源文件
    wiznote_file = None
    for md in wiznote_path.rglob('*.md'):
        if note_name_pattern in md.name:
            wiznote_file = md
            break

    if not wiznote_file:
        print(f'❌ 未找到 WizNote 源文件: {note_name_pattern}')
        return False

    # 查找 Obsidian 目标文件
    obsidian_file = None
    for md in obsidian_path.rglob('*.md'):
        if note_name_pattern in md.name:
            obsidian_file = md
            break

    if not obsidian_file:
        print(f'❌ 未找到 Obsidian 目标文件: {note_name_pattern}')
        return False

    print(f'\n📝 处理笔记: {obsidian_file.name}')
    print(f'   WizNote: {wiznote_file.relative_to(wiznote_path)}')
    print(f'   Obsidian: {obsidian_file.relative_to(obsidian_path)}')

    # 读取内容
    wiznote_content = wiznote_file.read_text(encoding='utf-8')
    obsidian_content = obsidian_file.read_text(encoding='utf-8')

    # 提取 WizNote 图片块
    wiznote_images = extract_image_blocks(wiznote_content)

    print(f'   WizNote 图片数: {len(wiznote_images)}')
    print(f'   Obsidian 图片数: {len(re.findall(r"!\[.*?\]\(.*?\)", obsidian_content))}')

    if not wiznote_images:
        print('   ✅ WizNote 中没有图片')
        return True

    # 统计修复
    fixed_count = 0

    # 对于每个图片，尝试在 Obsidian 中找到对应位置
    for img_block in wiznote_images:
        image_link = img_block['link']
        context = img_block['context']

        # 检查图片链接是否已经存在
        if image_link in obsidian_content:
            continue

        # 提取上下文关键词
        context_keywords = re.findall(r'[\u4e00-\u9fa5A-Za-z0-9]+', context)

        # 在 Obsidian 中查找匹配位置
        for keyword in context_keywords[-3:]:  # 取最后 3 个关键词
            if len(keyword) > 3:
                # 查找关键词位置
                pos = obsidian_content.find(keyword)
                if pos > 0:
                    # 找到关键词后面的换行符
                    newline_pos = obsidian_content.find('\n', pos)
                    if newline_pos > 0:
                        # 在换行符后插入图片
                        insert_pos = newline_pos + 1

                        print(f'   🔧 在 "{keyword}" 后插入图片')

                        if not dry_run:
                            # 插入图片
                            obsidian_content = (
                                obsidian_content[:insert_pos] +
                                '\n' + image_link + '\n\n' +
                                obsidian_content[insert_pos:]
                            fixed_count += 1
                        break

    if fixed_count > 0:
        if not dry_run:
            # 保存修改后的文件
            obsidian_file.write_text(obsidian_content, encoding='utf-8')
            print(f'   ✅ 修复了 {fixed_count} 个图片链接')
        else:
            print(f'   [DRY RUN] 将修复 {fixed_count} 个图片链接')
    else:
        print(f'   ⚠️ 未能自动匹配图片位置')

    return True

def main():
    print("=" * 60)
    print("WizNote 图片链接修复工具")
    print("=" * 60)
    print()

    wiznote_path, obsidian_path = find_vaults()

    print(f'WizNote 目录: {wiznote_path}')
    print(f'Obsidian 仓库: {obsidian_path}')
    print()

    # 要修复的笔记列表
    notes_to_fix = [
        ('严琦东', '人人都是开发者'),
    ]

    print(f'计划修复 {len(notes_to_fix)} 个笔记\n')

    # 先运行 dry run
    print("=" * 60)
    print("第一步：预览修复（DRY RUN）")
    print("=" * 60)

    for pattern, _ in notes_to_fix:
        fix_note(wiznote_path, obsidian_path, pattern, dry_run=True)

    print("\n" + "=" * 60)
    print("预览完成。是否执行实际修复？")
    print("=" * 60)

    # 在实际运行时，    # print('\n执行实际修复...')
    # for pattern, _ in notes_to_fix:
    #     fix_note(wiznote_path, obsidian_path, pattern, dry_run=False)

    print('\n完成！')

if __name__ == '__main__':
    main()
