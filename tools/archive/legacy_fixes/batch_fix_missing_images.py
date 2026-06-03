#!/usr/bin/env python3
"""
批量修复 Obsidian 仓库中的图片缺失问题
从 WizNote 源目录复制缺失的图片到 attachments 目录
"""

from pathlib import Path
import re
import shutil
from datetime import datetime

# 配置
OBSIDIAN_DIR = Path("/Users/wardlu/Documents/Ward's Obsidian")
WIZNOTE_DIR = Path('/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian/wiznote_download')

# 需要修复的文件列表
FILES_TO_FIX = [
    '02_Areas/产品思考/产品管理/腾讯产品启示录——薛军.md',
    '02_Areas/产品思考/产品管理/数据驱动型公司的业务指标.md',
    '02_Areas/产品思考/产品管理/增长黑客——范冰.md',
    '02_Areas/产品思考/产品管理/使命、愿景、价值观、口号.md',
    '02_Areas/求职/怎样面试产品经理？.md',
    '02_Areas/求职/面试材料/2025高级产品经理面试.md',
    '02_Areas/学习/Books/小家越住越大.md',
    '02_Areas/学习/Books/产品经理/从点子到产品：产品经理的价值观与方法论 读书笔记.md',
    '02_Areas/学习/Books/产品经理/当产品经理遇到人工智能读书笔记.md',
    '02_Areas/保险/重疾险对比.md',
    '02_Areas/保险/家庭保险配置指南.md',
    '02_Areas/创业/产品技术团队怎样引入 OKR 工作法.md',
    '05_Other/软件激活码/Axure激活码.md',
    '05_Other/账号密码/雷霆vpn.md',
    '05_Other/账号密码/MetaMask 以太币钱包重置口令.md',
    '05_Other/账号密码/智布互联账号.md',
    '05_Other/账号密码/怡和相关账户.md',
]

def find_source_images(md_file):
    """在 WizNote 目录中查找对应的图片目录"""
    # 尝试多种可能的图片目录位置

    # 方式1: 同名 _files 目录
    possible_paths = [
        WIZNOTE_DIR / '缺失图片及附件笔记' / f"{md_file.stem}_files",
        WIZNOTE_DIR / 'images',
    ]

    # 方式2: 搜索整个 WizNote 目录
    for wiz_md in WIZNOTE_DIR.rglob(f"{md_file.stem}*.md"):
        files_dir = wiz_md.parent / f"{wiz_md.stem}_files"
        if files_dir.exists():
            return files_dir

    return None

def main():
    print("=" * 70)
    print("批量修复 Obsidian 图片缺失问题")
    print("=" * 70)
    print()

    total_copied = 0
    total_missing = 0
    results = []

    for rel_path in FILES_TO_FIX:
        md_file = OBSIDIAN_DIR / rel_path

        if not md_file.exists():
            print(f"⚠️  文件不存在: {rel_path}")
            continue

        print(f"\n📄 处理: {Path(rel_path).name}")

        # 读取图片引用
        content = md_file.read_text(encoding='utf-8')
        images = re.findall(r'!\[.*?\]\(attachments/(.*?)\)', content)

        if not images:
            print(f"   无图片引用")
            continue

        print(f"   图片引用: {len(images)} 个")

        # 创建 attachments 目录
        attachments_dir = md_file.parent / 'attachments'
        attachments_dir.mkdir(parents=True, exist_ok=True)

        # 查找源图片目录
        source_images_dir = find_source_images(md_file)

        if not source_images_dir:
            print(f"   ❌ 未找到源图片目录")
            total_missing += len(images)
            continue

        print(f"   源图片目录: {source_images_dir.relative_to(WIZNOTE_DIR)}")

        # 复制图片
        copied = 0
        missing = 0

        for img in images:
            src = source_images_dir / img
            dst = attachments_dir / img

            if src.exists():
                shutil.copy2(src, dst)
                copied += 1
            else:
                # 尝试在 WizNote 的 images 目录中查找
                global_images = WIZNOTE_DIR / 'images' / img
                if global_images.exists():
                    shutil.copy2(global_images, dst)
                    copied += 1
                else:
                    missing += 1

        print(f"   ✅ 复制: {copied} 张")
        if missing:
            print(f"   ❌ 缺失: {missing} 张")

        total_copied += copied
        total_missing += missing

        results.append({
            'file': rel_path,
            'total': len(images),
            'copied': copied,
            'missing': missing
        })

    # 生成报告
    print("\n" + "=" * 70)
    print("\n📊 修复统计:\n")
    print(f"  处理文件: {len(results)} 个")
    print(f"  复制图片: {total_copied} 张")
    print(f"  缺失图片: {total_missing} 张")

    # 保存报告
    report_path = Path('/Users/wardlu/Documents/VibeCoding/Wiznote to Obisidian') / \
                   f'BATCH_IMAGE_FIX_REPORT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'

    report_content = f"""# 批量图片修复报告

**修复时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 修复统计

| 项目 | 数量 |
|------|------|
| 处理文件 | {len(results)} 个 |
| 复制图片 | {total_copied} 张 |
| 缺失图片 | {total_missing} 张 |

---

## 📝 详细结果

"""

    for r in results:
        status = "✅" if r['copied'] == r['total'] else "⚠️"
        report_content += f"\n{status} **{r['file']}**\n"
        report_content += f"  - 总数: {r['total']} 张\n"
        report_content += f"  - 复制: {r['copied']} 张\n"
        report_content += f"  - 缺失: {r['missing']} 张\n"

    report_path.write_text(report_content, encoding='utf-8')
    print(f"\n📄 报告已保存: {report_path.name}")

if __name__ == '__main__':
    main()
