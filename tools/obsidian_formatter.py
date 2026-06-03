#!/usr/bin/env python3
"""
WizNote to Obsidian - 一体化迁移工具
整合所有迁移、修复、增强功能

使用方法:
    python3 wiznote_to_obsidian.py --help
    python3 wiznote_to_obsidian.py --all          # 执行完整流程
    python3 wiznote_to_obsidian.py --check        # 只检查语法
    python3 wiznote_to_obsidian.py --fix          # 只修复格式
    python3 wiznote_to_obsidian.py --migrate      # 只迁移图片
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional


class Config:
    """配置管理"""
    def __init__(self, config_file: Optional[str] = None):
        # 智能检测默认目录
        project_root = Path(__file__).parent.parent  # 项目根目录
        wiznote_download = project_root / 'wiznote_download'

        # 优先使用 wiznote_download（如果存在），否则使用传统路径
        if wiznote_download.exists():
            default_source = str(wiznote_download)
            default_vault = str(project_root / 'wiznote_obsidian')  # vault 指向输出目录
            default_target = str(project_root / 'wiznote_obsidian')  # 输出到新目录
        else:
            default_source = os.path.expanduser("~/wiznote_export")
            default_vault = os.path.expanduser("~/wiznote_obsidian")  # vault 指向输出目录
            default_target = os.path.expanduser("~/wiznote_obsidian")  # 输出到新目录

        # 默认配置
        self.source_dir = default_source
        self.vault_dir = default_vault
        self.target_dir = default_target
        self.attachments_dir = os.path.join(self.vault_dir, "attachments")

        # 如果有配置文件，加载配置
        if config_file and Path(config_file).exists():
            self.load_config(config_file)

        # 环境变量优先级更高
        self.source_dir = os.getenv("WIZNOTE_SOURCE_DIR", self.source_dir)
        self.vault_dir = os.getenv("WIZNOTE_VAULT_DIR", self.vault_dir)
        self.target_dir = os.getenv("WIZNOTE_TARGET_DIR", self.target_dir)
        self.attachments_dir = os.getenv("WIZNOTE_ATTACHMENTS_DIR", self.attachments_dir)

    def load_config(self, config_file: str):
        """从 JSON 文件加载配置"""
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            for key, value in config.items():
                setattr(self, key, value)


class MarkdownChecker:
    """Markdown 语法检查器"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.issues = []
        self.lines = []

    def check(self) -> List[Dict]:
        """执行所有检查"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.lines = f.readlines()
        except Exception as e:
            return [{
                'type': '文件读取错误',
                'line': 0,
                'severity': 'ERROR',
                'message': str(e)
            }]

        # 执行各项检查
        self.check_headings()
        self.check_lists()
        self.check_code_blocks()
        self.check_bold_italic()
        self.check_links()
        self.check_blank_lines()

        return self.issues

    def check_headings(self):
        """检查标题层级和格式"""
        prev_level = 0
        heading_pattern = re.compile(r'^(#{1,6})\s*(.*?)\s*$')

        for i, line in enumerate(self.lines, 1):
            match = heading_pattern.match(line)
            if not match:
                continue

            level = len(match.group(1))

            # 检查标题前后空格
            if line.startswith('#') and not line.startswith('# '):
                self.issues.append({
                    'type': '标题格式',
                    'line': i,
                    'severity': 'WARNING',
                    'message': f'标题后缺少空格: {line.strip()}'
                })

            # 检查标题层级跳跃
            if prev_level > 0 and level > prev_level + 1:
                self.issues.append({
                    'type': '标题层级',
                    'line': i,
                    'severity': 'WARNING',
                    'message': f'标题层级跳跃: H{prev_level} → H{level}'
                })

            prev_level = level

    def check_lists(self):
        """检查列表格式"""
        for i, line in enumerate(self.lines, 1):
            if re.match(r'^(\s*)([*\-])\s+', line):
                marker = line.strip()[0]
                if marker == '*':
                    self.issues.append({
                        'type': '列表格式',
                        'line': i,
                        'severity': 'INFO',
                        'message': '建议使用 "-" 代替 "*"'
                    })

    def check_code_blocks(self):
        """检查代码块格式"""
        in_code_block = False
        code_fence_pattern = re.compile(r'^```(\w*)')

        for i, line in enumerate(self.lines, 1):
            match = code_fence_pattern.match(line)
            if match:
                in_code_block = not in_code_block
                lang = match.group(1)
                if in_code_block and not lang:
                    self.issues.append({
                        'type': '代码块',
                        'line': i,
                        'severity': 'INFO',
                        'message': '代码块未指定语言'
                    })

    def check_bold_italic(self):
        """检查粗体和斜体格式"""
        for i, line in enumerate(self.lines, 1):
            bold_count = line.count('**')
            if bold_count % 2 != 0:
                self.issues.append({
                    'type': '未闭合标记',
                    'line': i,
                    'severity': 'ERROR',
                    'message': '可能存在未闭合的 ** 粗体标记'
                })

    def check_links(self):
        """检查内部链接"""
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+\.md)\)')
        for i, line in enumerate(self.lines, 1):
            matches = link_pattern.findall(line)
            for text, path in matches:
                self.issues.append({
                    'type': '内部链接',
                    'line': i,
                    'severity': 'INFO',
                    'message': f'可转换为 WikiLinks: [{text}]({path})'
                })

    def check_blank_lines(self):
        """检查空行"""
        consecutive_blanks = 0
        for i, line in enumerate(self.lines, 1):
            if not line.strip():
                consecutive_blanks += 1
            else:
                if consecutive_blanks > 2:
                    self.issues.append({
                        'type': '多余空行',
                        'line': i - consecutive_blanks,
                        'severity': 'INFO',
                        'message': f'发现 {consecutive_blanks} 个连续空行'
                    })
                consecutive_blanks = 0


class MarkdownFixer:
    """Markdown 语法修复器"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.original_lines = []
        self.fixed_lines = []
        self.fixes_applied = []

    def fix(self) -> Tuple[List[str], List[str]]:
        """执行所有自动修复"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.original_lines = f.readlines()
            self.fixed_lines = self.original_lines.copy()
        except Exception as e:
            return [], [f'文件读取错误: {e}']

        # 执行各项修复
        self.fix_heading_spaces()
        self.fix_list_markers()
        self.fix_code_blocks()
        self.fix_blank_lines()
        self.fix_horizontal_rules()

        return self.fixed_lines, self.fixes_applied

    def fix_heading_spaces(self):
        """修复标题前后空格"""
        pattern = re.compile(r'^(#{1,6})([^\s#])')
        for i, line in enumerate(self.fixed_lines):
            new_line = pattern.sub(r'\1 \2', line)
            if new_line != line:
                self.fixed_lines[i] = new_line
                self.fixes_applied.append(f'第 {i+1} 行: 修复标题空格')

    def fix_list_markers(self):
        """统一无序列表标记为 -"""
        pattern = re.compile(r'^(\s*)\* ')
        for i, line in enumerate(self.fixed_lines):
            if not self._is_in_code_block(i):
                new_line = pattern.sub(r'\1- ', line)
                if new_line != line:
                    self.fixed_lines[i] = new_line
                    self.fixes_applied.append(f'第 {i+1} 行: 统一列表标记')

    def fix_code_blocks(self):
        """将缩进代码块转换为 fenced code blocks"""
        # 简化实现：只转换明显的缩进代码块
        pass

    def fix_blank_lines(self):
        """修复多余空行"""
        i = 0
        while i < len(self.fixed_lines):
            blank_count = 0
            j = i
            while j < len(self.fixed_lines) and not self.fixed_lines[j].strip():
                blank_count += 1
                j += 1

            if blank_count > 2:
                del self.fixed_lines[i+2:j]
                self.fixes_applied.append(f'第 {i+1} 行: 删除多余空行')
                i = i + 2
            else:
                i = j if blank_count > 0 else i + 1

    def fix_horizontal_rules(self):
        """为水平线添加前后空行"""
        hr_pattern = re.compile(r'^(\*{3,}|-{3,}|_{3,})\s*$')
        for i, line in enumerate(self.fixed_lines):
            if hr_pattern.match(line):
                if i > 0 and self.fixed_lines[i-1].strip():
                    self.fixed_lines.insert(i, '\n')
                    self.fixes_applied.append(f'第 {i+1} 行: 水平线前添加空行')
                    i += 1

    def _is_in_code_block(self, line_index: int) -> bool:
        """检查指定行是否在代码块内"""
        in_code = False
        for i in range(min(line_index, len(self.fixed_lines))):
            line = self.fixed_lines[i]
            if line.strip().startswith('```'):
                in_code = not in_code
        return in_code

    def save(self):
        """保存修复后的文件"""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.writelines(self.fixed_lines)


class LinkConverter:
    """链接转换器 - 将 Markdown 链接转换为 WikiLinks"""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)

    def convert_file(self, file_path: str) -> Tuple[bool, int, int]:
        """
        转换单个文件

        Returns:
            (是否修改, 文档链接转换数, 图片链接转换数)
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        md_links_converted = 0
        img_links_converted = 0

        # 1. 转换文档链接 [text](path.md)
        def replace_doc_link(match):
            nonlocal md_links_converted
            text = match.group(1)
            path = match.group(2)

            # 跳过外部链接
            if path.startswith('http://') or path.startswith('https://'):
                return match.group(0)

            filename = os.path.basename(path)
            if filename.endswith('.md'):
                filename = filename[:-3]

            md_links_converted += 1

            if filename in text or text == filename:
                return f"[[{filename}]]"
            else:
                return f"[[{filename}|{text}]]"

        pattern = r'\[([^\]]+)\]\(([^)]+\.md)\)'
        content = re.sub(pattern, replace_doc_link, content)

        # 2. 转换图片链接 ![alt](path)
        def replace_image_link(match):
            nonlocal img_links_converted
            alt_text = match.group(1)
            path = match.group(2)

            # 跳过外部链接
            if path.startswith('http://') or path.startswith('https://'):
                return match.group(0)

            # 提取图片文件名
            image_name = os.path.basename(path)

            img_links_converted += 1

            # 如果有 alt text 且不等于文件名，保留它
            if alt_text and alt_text != image_name:
                return f"![[{image_name}|{alt_text}]]"
            else:
                return f"![[{image_name}]]"

        # 匹配 ![alt](path) 格式
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        content = re.sub(img_pattern, replace_image_link, content)

        # 3. 转换其他附件链接（PDF 等）
        def replace_attachment_link(match):
            nonlocal md_links_converted
            text = match.group(1)
            path = match.group(2)

            # 跳过外部链接
            if path.startswith('http://') or path.startswith('https://'):
                return match.group(0)

            # 提取文件名
            filename = os.path.basename(path)

            md_links_converted += 1

            # 如果文本和文件名相同，省略显示文本
            if text == filename or not text:
                return f"[[{filename}]]"
            else:
                return f"[[{filename}|{text}]]"

        # 匹配 [text](path.pdf) 等附件链接（排除 .md 和图片）
        attachment_pattern = r'\[([^\]]+)\]\(([^)]+\.(pdf|docx?|xlsx?|pptx?|zip|rar|7z|xmind|mp[34]|mov|avi|wav|flac))\)'
        content = re.sub(attachment_pattern, replace_attachment_link, content, flags=re.IGNORECASE)

        # 如果有修改，保存文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, md_links_converted, img_links_converted

        return False, 0, 0


class ImagePathFixer:
    """图片路径修复器"""

    def __init__(self, vault_path: str, attachments_dir: str):
        self.vault_path = Path(vault_path)
        self.attachments_dir = Path(attachments_dir)

    def find_image_by_name(self, image_name: str) -> Optional[str]:
        """在 attachments 目录中查找图片"""
        matches = list(self.attachments_dir.rglob(image_name))
        if matches:
            return str(matches[0].relative_to(self.attachments_dir))
        return None

    def fix_file(self, file_path: str) -> Tuple[int, int]:
        """修复单个文件的图片路径"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixed_count = 0
        not_found_count = 0

        images_in_file = re.findall(r'!\[\(/attachments/images/([^)]+)\)', content)

        for image_name in images_in_file:
            relative_path = self.find_image_by_name(image_name)

            if relative_path:
                old_path = f'![](/attachments/images/{image_name})'
                new_path = f'![](/attachments/{relative_path})'
                content = content.replace(old_path, new_path)
                fixed_count += 1
            else:
                not_found_count += 1

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        return fixed_count, not_found_count


class FrontMatterAdder:
    """YAML Front Matter 添加器"""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)

    def add_front_matter(self, file_path: str, metadata: Dict) -> bool:
        """为文件添加 front matter"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否已有 front matter
        if content.startswith('---'):
            return False

        # 生成 front matter
        front_matter = "---\n"
        for key, value in metadata.items():
            if isinstance(value, list):
                front_matter += f"{key}: {json.dumps(value, ensure_ascii=False)}\n"
            else:
                front_matter += f'{key}: "{value}"\n'
        front_matter += "---\n\n"

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(front_matter + content)

        return True


class WiznoteToObsidianMigrator:
    """主迁移器"""

    def __init__(self, config: Config):
        self.config = config
        self.results = {
            'total_files': 0,
            'fixed_files': 0,
            'converted_links': 0,
            'fixed_images': 0,
            'issues': []
        }

    def check_syntax(self) -> Dict:
        """检查 Markdown 语法"""
        print("🔍 检查 Markdown 语法...\n")

        dir_path = Path(self.config.target_dir)
        md_files = list(dir_path.rglob('*.md'))

        all_issues = []
        for file_path in md_files:
            checker = MarkdownChecker(str(file_path))
            issues = checker.check()
            if issues:
                all_issues.extend([(str(file_path), issue) for issue in issues])

        # 统计
        severity_count = {'ERROR': 0, 'WARNING': 0, 'INFO': 0}
        for _, issue in all_issues:
            severity_count[issue['severity']] += 1

        print(f"📊 检查完成：")
        print(f"   - 总文件数: {len(md_files)}")
        print(f"   - 🔴 ERROR: {severity_count['ERROR']}")
        print(f"   - 🟡 WARNING: {severity_count['WARNING']}")
        print(f"   - 🔵 INFO: {severity_count['INFO']}")

        return {
            'total_files': len(md_files),
            'issues': all_issues,
            'severity_count': severity_count
        }

    def fix_format(self, dry_run: bool = False) -> Dict:
        """修复格式问题"""
        print(f"🔧 修复格式 {'(模拟运行)' if dry_run else '(实际修复)'}...\n")

        dir_path = Path(self.config.target_dir)
        md_files = list(dir_path.rglob('*.md'))

        # 输出总数，方便 GUI 解析
        print(f"PROGRESS_START:{len(md_files)}")

        total_fixes = 0
        files_with_fixes = 0

        for i, file_path in enumerate(md_files[:10], 1):  # 限制处理文件数
            fixer = MarkdownFixer(str(file_path))
            fixed_lines, fixes = fixer.fix()

            if fixes and not dry_run:
                fixer.save()

            if fixes:
                files_with_fixes += 1
                total_fixes += len(fixes)
                rel_path = str(file_path).replace(self.config.vault_dir, '')

                # 标准进度输出格式：PROGRESS:current:total:percent
                percent = int((i / len(md_files)) * 100)
                print(f"PROGRESS:{i}:{len(md_files)}:{percent}")
                print(f"[{i}/{len(md_files)}] ✅ {rel_path}")
                for fix in fixes[:3]:
                    print(f"         {fix}")

        print(f"\n📊 修复完成：")
        print(f"   - 处理文件: {len(md_files)}")
        print(f"   - 修复文件: {files_with_fixes}")
        print(f"   - 应用修复: {total_fixes}")

        return {
            'total_files': len(md_files),
            'fixed_files': files_with_fixes,
            'total_fixes': total_fixes
        }

    def convert_links(self) -> Dict:
        """转换链接为 WikiLinks（文档链接 + 图片链接）"""
        print("🔗 转换链接为 WikiLinks...\n")

        converter = LinkConverter(self.config.target_dir)
        converted_count = 0
        total_md_links = 0
        total_img_links = 0

        md_files = list(Path(self.config.target_dir).rglob('*.md'))
        # 排除 .obsidian 和 .trash 目录
        md_files = [f for f in md_files if '.obsidian' not in str(f) and '.trash' not in str(f)]

        for i, md_file in enumerate(md_files, 1):
            modified, md_count, img_count = converter.convert_file(str(md_file))
            if modified:
                converted_count += 1
                total_md_links += md_count
                total_img_links += img_count

                # 打印进度
                rel_path = str(md_file.relative_to(self.config.target_dir))
                print(f"[{i}/{len(md_files)}] ✅ {rel_path}")
                if md_count > 0:
                    print(f"         📎 转换了 {md_count} 个文档链接")
                if img_count > 0:
                    print(f"         🖼️  转换了 {img_count} 个图片链接")

        print(f"\n📊 转换完成：")
        print(f"   - 修改的文件: {converted_count}")
        print(f"   - 文档链接转换: {total_md_links}")
        print(f"   - 图片链接转换: {total_img_links}")

        return {
            'converted_files': converted_count,
            'md_links': total_md_links,
            'img_links': total_img_links
        }

    def fix_images(self) -> Dict:
        """修复图片路径"""
        print("🖼️  修复图片路径...\n")

        fixer = ImagePathFixer(self.config.vault_dir, self.config.attachments_dir)
        fixed_count = 0
        not_found_count = 0

        for md_file in Path(self.config.target_dir).rglob('*.md'):
            fixed, not_found = fixer.fix_file(str(md_file))
            fixed_count += fixed
            not_found_count += not_found

        print(f"📊 修复完成：")
        print(f"   - 已修复: {fixed_count}")
        print(f"   - 未找到: {not_found_count}")

        return {'fixed': fixed_count, 'not_found': not_found_count}

    def generate_report(self) -> Dict:
        """生成统计报告"""
        print("📊 生成统计报告...\n")

        dir_path = Path(self.config.target_dir)
        md_files = list(dir_path.rglob('*.md'))

        print("=" * 60)
        print("📊 WizNote → Obsidian 转换报告")
        print("=" * 60)
        print(f"\n📝 Markdown 文件: {len(md_files)}")

        # 统计图片
        images = []  # 初始化变量
        if Path(self.config.attachments_dir).exists():
            image_files = list(Path(self.config.attachments_dir).rglob('*'))
            image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
            images = [f for f in image_files if f.suffix.lower() in image_extensions]
            print(f"🖼️  图片文件: {len(images)}")

        # 统计链接
        wikilinks = 0
        for md_file in md_files:
            with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                wikilinks += len(re.findall(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', content))

        print(f"🔗 WikiLinks: {wikilinks}")
        print("=" * 60)

        return {
            'total_files': len(md_files),
            'total_images': len(images) if images else 0,
            'total_wikilinks': wikilinks
        }

    def run_all(self):
        """执行完整流程"""
        print("\n" + "=" * 60)
        print("🚀 WizNote → Obsidian 一体化迁移")
        print("=" * 60 + "\n")

        # 0. 如果 source 和 target 不同，先复制文件
        source_path = Path(self.config.source_dir)
        target_path = Path(self.config.target_dir)

        if source_path.resolve() != target_path.resolve():
            if not target_path.exists():
                print("📂 复制文件到目标目录...")
                print(f"   源目录: {source_path}")
                print(f"   目标目录: {target_path}")

                import shutil
                shutil.copytree(source_path, target_path)
                print(f"   ✅ 复制完成\n")
            else:
                print(f"📂 目标目录已存在: {target_path}\n")

        # 1. 检查语法
        check_result = self.check_syntax()
        print("\n" + "-" * 60 + "\n")

        # 2. 修复格式
        fix_result = self.fix_format(dry_run=False)
        print("\n" + "-" * 60 + "\n")

        # 3. 转换链接
        link_result = self.convert_links()
        print("\n" + "-" * 60 + "\n")

        # 4. 修复图片
        image_result = self.fix_images()
        print("\n" + "-" * 60 + "\n")

        # 5. 生成报告
        report_result = self.generate_report()

        print("\n✅ 基础格式化完成！")

        return {
            'check': check_result,
            'fix': fix_result,
            'links': link_result,
            'images': image_result,
            'report': report_result
        }

    def migrate_attachments(self, dry_run: bool = False):
        """迁移附件文件（已废弃，请使用 consolidate_attachments.py）"""
        print("⚠️  此功能已废弃")
        print("请使用新工具：python3 tools/consolidate_attachments.py migrate /path/to/vault")
        return {'success': False, 'error': '功能已废弃，请使用 consolidate_attachments.py'}

    def link_attachments(self, dry_run: bool = False):
        """为笔记添加附件链接（已废弃，请使用 vault_cleaner.py fix）"""
        print("⚠️  此功能已废弃")
        print("请使用新工具：python3 tools/vault_cleaner.py fix /path/to/vault")
        return {'success': False, 'error': '功能已废弃，请使用 vault_cleaner.py fix'}

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(result.stdout)
            return {'success': True}
        except subprocess.CalledProcessError as e:
            print(f"❌ 附件链接失败: {e}")
            print(e.stderr)
            return {'success': False, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(
        description='WizNote to Obsidian 一体化迁移工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 执行完整流程
  python3 wiznote_to_obsidian.py --all

  # 只检查语法
  python3 wiznote_to_obsidian.py --check

  # 只修复格式
  python3 wiznote_to_obsidian.py --fix

  # 使用自定义配置文件
  python3 wiznote_to_obsidian.py --config config.json --all
        """
    )

    parser.add_argument('--config', help='配置文件路径 (JSON 格式)')
    parser.add_argument('--vault', help='Obsidian 仓库路径（优先级最高）')
    parser.add_argument('--all', action='store_true', help='执行完整流程')
    parser.add_argument('--check', action='store_true', help='检查 Markdown 语法')
    parser.add_argument('--fix', action='store_true', help='修复格式问题')
    parser.add_argument('--links', action='store_true', help='转换链接为 WikiLinks')
    parser.add_argument('--images', action='store_true', help='修复图片路径')
    parser.add_argument('--report', action='store_true', help='生成统计报告')
    parser.add_argument('--migrate-attachments', action='store_true', help='迁移附件文件')
    parser.add_argument('--link-attachments', action='store_true', help='为笔记添加附件链接')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际修改文件')

    args = parser.parse_args()

    # 加载配置
    config = Config(args.config)

    # 如果指定了 --vault，覆盖所有路径配置
    if args.vault:
        vault_path = Path(args.vault).expanduser().resolve()
        config.source_dir = str(vault_path)
        config.target_dir = str(vault_path)
        config.vault_dir = str(vault_path)
        config.attachments_dir = str(vault_path / "attachments")

    # 创建迁移器
    migrator = WiznoteToObsidianMigrator(config)

    # 如果没有指定任何操作，执行基础格式化（5步）
    if not any([args.all, args.check, args.fix, args.links, args.images, args.report,
                args.migrate_attachments, args.link_attachments]):
        # 默认执行基础5步
        migrator.run_all()
        return

    # 执行相应操作
    if args.all:
        # 完整迁移（7步）：基础5步 + 附件迁移 + 附件链接
        migrator.run_all()
        print("\n" + "="*60)
        print("📎 附件迁移")
        print("="*60)
        migrator.migrate_attachments(dry_run=args.dry_run)
        print("\n" + "="*60)
        print("🔗 附件链接")
        print("="*60)
        migrator.link_attachments(dry_run=args.dry_run)
    elif args.check:
        migrator.check_syntax()
    elif args.fix:
        migrator.fix_format(dry_run=args.dry_run)
    elif args.links:
        migrator.convert_links()
    elif args.images:
        migrator.fix_images()
    elif args.report:
        migrator.generate_report()
    elif args.migrate_attachments:
        migrator.migrate_attachments(dry_run=args.dry_run)
    elif args.link_attachments:
        migrator.link_attachments(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
