#!/usr/bin/env python3
"""
将 Markdown 文件中的 Obsidian WikiLinks 格式转换为标准 Markdown 格式
![[attachments/xxx.png]] -> ![](attachments/xxx.png)
"""

from pathlib import Path
import re

def convert_wikilinks_to_markdown():
    """转换 WikiLinks 格式为标准 Markdown 格式"""

    # 源文件目录
    source_dir = Path('/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download/缺失图片及附件笔记')

    # 需要转换的文件（PDF 转换的笔记）
    files_to_convert = [
        '10个做SaaS业务的重要原则.md',
        '结构化思维.md',
        '【建议收藏】5 种基本的产品框架，总有一款适合你.md',
        '「黄金圈法则」的「正+反」用法.md',
        '别再开发了，7招搞定低成本验证.md',
        '应用场景是什么？怎样判断、描述一个产品的应用场景？.md',
        '俞军：适合产品经理的⼗本书.md',
        '2022年下半年小棉猫产品路线图.md',
        '2023年下半年小棉猫产品路线图.md',
        '2024年上半年小棉猫产品路线图.md',
        'ToB老人家 SaaS拆解系列——第二讲：Oracle多组织架构.md',
        '产品年度规划怎么做.md',
        '分析方法&思维模型.md',
        '人人都是开发者——无代码产品轻流CPO严琦东Joseph Yan.md',
        '智能制造MES拆解.md',
    ]

    print("开始转换 Markdown 文件格式...\n")
    print("=" * 60)

    converted_count = 0
    total_images = 0

    for filename in files_to_convert:
        file_path = source_dir / filename

        if not file_path.exists():
            print(f"⚠️  跳过（不存在）: {filename}")
            continue

        # 读取文件内容
        content = file_path.read_text(encoding='utf-8')

        # 查找所有 WikiLinks 格式的图片引用
        wikilinks = re.findall(r'!\[\[attachments/(.*?)\]\]', content)

        if not wikilinks:
            print(f"📄 {filename}")
            print(f"   无图片引用\n")
            continue

        # 转换格式
        # ![[attachments/xxx.png]] -> ![](attachments/xxx.png)
        new_content = re.sub(
            r'!\[\[attachments/(.*?)\]\]',
            r'![](attachments/\1)',
            content
        )

        # 保存修改
        file_path.write_text(new_content, encoding='utf-8')

        print(f"✅ {filename}")
        print(f"   转换图片引用: {len(wikilinks)} 个")

        converted_count += 1
        total_images += len(wikilinks)
        print()

    print("=" * 60)
    print(f"\n转换完成:")
    print(f"  ✅ 转换文件: {converted_count} 个")
    print(f"  🖼️  图片引用: {total_images} 个")
    print(f"\n💡 现在可以在任何 Markdown 编辑器中查看图片了！")

if __name__ == '__main__':
    convert_wikilinks_to_markdown()
