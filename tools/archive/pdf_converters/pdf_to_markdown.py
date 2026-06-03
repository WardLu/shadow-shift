#!/usr/bin/env python3
"""
PDF 转 Markdown 工具
将 PDF 文件转换为 Markdown 格式
"""

import sys
import subprocess
from pathlib import Path
import re

# PDF 文件列表
pdf_files = [
    ('10个做SaaS业务的重要原则.pdf', '10个做SaaS业务的重要原则'),
    ('2022年下半年小棉猫产品路线图.pdf', '2022年下半年小棉猫产品路线图'),
    ('2023年下半年小棉猫产品路线图.pdf', '2023年下半年小棉猫产品路线图'),
    ('2024年上半年小棉猫产品路线图.pdf', '2024年上半年小棉猫产品路线图'),
    ('别再开发了，7招搞定低成本验证.pdf', '别再开发了，7招搞定低成本验证'),
    ('「黄金圈法则」的「正+反」用法.pdf', ' '「黄金圈法则」的「正+反」用法'),
    ('【建议收藏】5 种基本的产品框架，总有一款适合你.pdf', '【建议收藏】5 种基本的产品框架'),
    ('结构化思维.pdf', '结构化思维'),
    ('俞军：适合产品经理的⼗本书.pdf', '俞军：适合产品经理的⼗本书')
]

def convert_pdf_to_markdown(pdf_path, output_path, att_dir):
    """将 PDF 转换为 Markdown"""
    try:
        import PyPDF2
        has_pypdf2 = True
    except ImportError:
        print("❌ PyPDF2 未安装")
        return False

    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)

    # 创建图片目录
    images_dir = output_path / 'images'
    images_dir.mkdir(parents=True, exist_ok=True)

    # 打开 PDF
    pdf_reader = PyPDF2.PReader(pdf_path)
    markdown_lines = []
    image_count = 0

    # 提取标题
    title = pdf_path.stem

    # 添加 frontmatter
    markdown_lines.append(f'---')
    markdown_lines.append(f'title: "{title}"')
    markdown_lines.append(f'created: {datetime.now().strftime("%Y-%m-%d")}')
    markdown_lines.append(f'type: pdf-import')
    markdown_lines.append(f'source: "{pdf_path.name}"')
    markdown_lines.append(f'tags: [\'PDF\', \'imported\']')
    markdown_lines.append(f'---')
    markdown_lines.append('')
    markdown_lines.append(f'# {title}')
    markdown_lines.append('')

    # 遍历每一页
    for page_num, range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]

        # 提取文本
        text = page.extract_text()

        if not text.strip():
            continue

        # 处理图片
        images = page.images
        for img_index, img in enumerate(images):
            # 保存图片
            img_filename = f'image_{page_num}_{img_index}.png'
            img_path = images_dir / img_filename

            with open(img_path, 'wb') as img_path.write(img.data)

            # 添加图片链接
            markdown_lines.append(f'\n![Image {page_num + 1}](images/{img_filename})')
            image_count += 1

        # 添加文本
        markdown_lines.append(f'\n{text}\n')

    # 保存 Markdown
    md_path = output_path / f'{title}.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(markdown_lines))

    print(f"✅ 转换完成: {pdf_path.name}")
    print(f"   页数: {len(pdf_reader.pages)}")
    print(f"   图片: {image_count} 张")
    print(f"   输出: {md_path}")

    return True

def process_all_pdfs():
    """批量处理所有 PDF 文件"""
    print("=" * 60)
    print("PDF 转 Markdown 工具")
    print("=" * 60)
    print()

    # 检查 PyPDF2
    try:
        import PyPDF2
    except ImportError:
        print("❌ PyPDF2 未安装")
        print("\n正在安装 PyPDF2...")
        try:
            import subprocess
            result = subprocess.run(['pip3', 'install', 'PyPDF2'],
            print("✅ PyPDF2 安装成功\n")
        except:
            print("❌ 安装失败，            print("请手动安装: pip3 install PyPDF2")
            return

    # PDF 文件目录
    export_dir = Path('/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download/缺失图片及附件笔记')

    # 处理每个 PDF
    for pdf_name, _ title in pdf_files:
        pdf_path = export_dir / pdf_name

        if not pdf_path.exists():
            print(f"❌ 文件不存在: {pdf_name}")
            continue

        output_path = export_dir / f'{title}.md'

        if convert_pdf_to_markdown(pdf_path, output_path):
            print(f"✅ {title}")
        else:
            print(f"❌ 转换失败: {title})

        print()

    print("\n" + "=" * 60)
    print("处理完成")
    print("=" * 60)

if __name__ == '__main__':
    process_all_pdfs()
