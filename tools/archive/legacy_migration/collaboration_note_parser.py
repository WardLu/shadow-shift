#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
协作笔记解析器 - 将 ShareJS 格式转换为 Markdown
参考实现: https://github.com/awaken233/wiz2obsidian
"""

import json
import datetime


class BaseStrategy:
    """解析策略基类"""

    def __init__(self, data):
        self.data = data

    def to_text(self, block_row):
        """将 block 转换为 Markdown 文本"""
        pass


class TextStrategy(BaseStrategy):
    """文本块解析策略"""

    def to_text(self, block_row):
        text_content = '\n' + self.handle_text_obj_text(block_row) + '\n'
        # 检查是否有评论
        comment_content = self.handle_comments(block_row)
        return text_content + comment_content

    def handle_text_obj_text(self, block_row):
        if block_row.get("quoted"):
            return self.handle_quote(block_row['text'])
        elif block_row.get("heading"):
            return self.handle_header(block_row, block_row['text'])
        else:
            return self.handle_text(block_row['text'])

    def handle_comments(self, block_row):
        """处理评论内容"""
        comments_content = []

        for text_dict in block_row.get('text', []):
            attributes = text_dict.get('attributes', {})
            for attr_key, comment_id in attributes.items():
                if attr_key.startswith('comment-'):
                    comment_data = self.data.get('comments', {}).get(comment_id)
                    if comment_data:
                        comment_text = self.format_comment(comment_data)
                        comments_content.append(comment_text)

                        # 检查子评论
                        group_id = comment_data.get('groupId')
                        if group_id:
                            sub_comments = self.get_sub_comments(group_id, comment_id)
                            comments_content.extend(sub_comments)

        return ''.join(comments_content)

    def format_comment(self, comment_data):
        """格式化单个评论"""
        display_name = comment_data.get('displayName', '未知用户')
        created_timestamp = comment_data.get('created', 0)

        try:
            dt = datetime.datetime.fromtimestamp(created_timestamp / 1000)
            if dt.hour < 12:
                time_period = '上午'
                hour = dt.hour if dt.hour != 0 else 12
            else:
                time_period = '下午'
                hour = dt.hour if dt.hour <= 12 else dt.hour - 12
            formatted_time = f"{dt.year}/{dt.month}/{dt.day} {time_period}{hour}:{dt.minute:02d}:{dt.second:02d}"
        except:
            formatted_time = '时间未知'

        comment_text_parts = []
        for block in comment_data.get('blocks', []):
            for text_dict in block.get('text', []):
                if text_dict.get('attributes', {}).get('type') == 'mention':
                    mention_text = text_dict.get('attributes', {}).get('text', '')
                    comment_text_parts.append(f'@{mention_text}')
                else:
                    comment_text_parts.append(text_dict.get('insert', ''))

        comment_text = ''.join(comment_text_parts)
        return f'\n\n> {display_name} {formatted_time}\n\n{comment_text}\n'

    def get_sub_comments(self, group_id, main_comment_id):
        """获取子评论"""
        sub_comments = []
        all_comments = self.data.get('comments', {})

        for comment_id, comment_data in all_comments.items():
            if (comment_data.get('groupId') == group_id and
                comment_id != main_comment_id):
                sub_comment_text = self.format_comment(comment_data)
                sub_comments.append(sub_comment_text)

        return sub_comments

    @staticmethod
    def handle_text(text_arr):
        if not text_arr:
            return ''

        text = []
        for text_dict in text_arr:
            text.append(BlockTextConverter.to_text(text_dict))
        return ''.join(text)

    @staticmethod
    def handle_header(block_row, text_arr):
        text = []
        heading_level = block_row.get("heading")
        text.append(f'{"#" * heading_level} ')
        for text_dict in text_arr:
            text.append(BlockTextConverter.to_text(text_dict))
        return ''.join(text) + "\n"

    @staticmethod
    def handle_quote(json_data):
        text = []
        text.append("> ")
        for text_dict in json_data:
            text.append(BlockTextConverter.to_text(text_dict))
        join = ''.join(text)
        return join + '\n'


class ListStrategy(BaseStrategy):
    """列表块解析策略"""

    def to_text(self, block_row):
        if block_row.get("ordered"):
            return self.handle_ordered_list(block_row)
        else:
            return self.handle_unordered_list(block_row)

    def handle_unordered_list(self, block_row):
        text = []
        indent = (block_row['level'] - 1) * 2 * ' '
        text.append(f'{indent}- ')

        if block_row.get("checkbox"):
            if block_row["checkbox"] == "checked":
                text.append("[x] ")
            elif block_row["checkbox"] == "unchecked":
                text.append("[ ] ")

        for text_dict in block_row["text"]:
            text.append(BlockTextConverter.to_text(text_dict))
        join = ''.join(text)
        return join+'\n'

    def handle_ordered_list(self, block_row):
        text = []
        indent = (block_row['level'] - 1) * 2 * ' '
        text.append(f'{indent}{block_row["start"]}. ')
        for text_dict in block_row["text"]:
            text.append(BlockTextConverter.to_text(text_dict) + '\n')
        return ''.join(text)


class CodeStrategy(BaseStrategy):
    """代码块解析策略"""

    def __init__(self, data):
        super().__init__(data)

    def to_text(self, row):
        language = row.get("language", "")
        code_id = row["children"][0]
        texts = []
        for text_obj in self.data[code_id]:
            text_ = text_obj['text'][0] if text_obj['text'] else {"insert": ""}
            texts.append(text_["insert"] + "\n")
        return f"```{language}\n{''.join(texts)}```\n\n"


class EmbedStrategy(BaseStrategy):
    """嵌入内容解析策略"""

    def __init__(self, data):
        super().__init__(data)

    def to_text(self, row):
        embed_type = row.get("embedType", "")
        embed_data = row.get("embedData", {})

        if embed_type == "image":
            return self.handle_image(embed_data)
        elif embed_type == "toc":
            return "\n\n[TOC]\n\n"
        elif embed_type == "hr":
            return "\n\n---\n\n"
        elif embed_type == "office":
            file_name = embed_data.get('fileName', '')
            src = embed_data.get('src', '')
            return f'\n\n[{file_name}](wiz-collab-attachment://{src})\n\n'
        elif embed_type == "snapshot":
            return self.handle_snapshot(embed_data)
        elif embed_type == "encrypt-text":
            return ""
        elif embed_type == "webpage":
            return self.handle_webpage(embed_data)
        elif embed_type == "drawio":
            src = embed_data.get("src", "")
            return f'\n\n[流程图](wiz-collab-attachment://{src})\n\n'
        elif embed_type == "mermaid":
            return self.handle_mermaid(embed_data)
        else:
            return ""

    def handle_image(self, embed_data):
        image_url = embed_data.get("src", "")
        file_name = embed_data.get('fileName', '')
        return f"![{file_name}]({image_url})\n\n"

    def handle_snapshot(self, embed_data):
        """处理快照嵌入"""
        try:
            doc_content = embed_data.get("doc", "")
            if doc_content:
                doc_json = json.loads(doc_content)
                nested_blocks = doc_json.get("blocks", [])
                nested_content = []

                for block in nested_blocks:
                    block_content = MarkdownConverter.to_text(doc_json, block)
                    nested_content.append(block_content)

                combined_content = ''.join(nested_content).strip()
                lines = combined_content.split('\n')
                quoted_lines = []

                for line in lines:
                    quoted_lines.append(f"> {line}")

                return "\n\n" + '\n'.join(quoted_lines) + "\n\n"
            else:
                return "\n\n> **嵌入快照**: 无内容\n\n"
        except (json.JSONDecodeError, KeyError):
            return "\n\n> **嵌入快照**: 解析失败\n\n"

    def handle_webpage(self, embed_data):
        src = embed_data.get("src", "")
        return f"\n\n[webpage]({src})\n\n"

    def handle_mermaid(self, embed_data):
        mermaid_text = embed_data.get("mermaidText", "")
        if mermaid_text:
            return f'\n\n```mermaid\n{mermaid_text}\n```\n\n'
        else:
            src = embed_data.get("src", "")
            if src:
                return f'\n\n[Mermaid流程图](wiz-collab-attachment://{src})\n\n'
            else:
                return '\n\n```mermaid\n# Mermaid 图表内容缺失\n```\n\n'


class TableStrategy(BaseStrategy):
    """表格块解析策略"""

    def __init__(self, data):
        super().__init__(data)

    def to_text(self, row):
        cols = row["cols"]
        children = row["children"]

        children_text = []
        for child_id in children:
            text_ = self.data[child_id][0]["text"][0]['insert'] if self.data[child_id][0]["text"] else ''
            children_text.append(text_)
        headers = children_text[:cols]
        body = children_text[cols:]

        markdown_table = "|".join(headers)
        markdown_table = "|" + markdown_table + "|\n"
        markdown_table += "| " + " | ".join(["-----"] * cols) + " |\n"

        body_rows = [body[i:i + cols] for i in range(0, len(body), cols)]

        for body_row in body_rows:
            markdown_table += "|" + "|".join(body_row) + "|\n"
        return '\n' + markdown_table + '\n'


class BlockTextConverter:
    """行内文本转换器"""

    @staticmethod
    def to_text(text_dict):
        if text_dict.get("attributes"):
            attributes = text_dict["attributes"]
            if attributes.get("type") == "wiki-link":
                return BlockTextConverter.handle_wiki_link(text_dict)
            elif attributes.get("type") == "math":
                return BlockTextConverter.handle_math(text_dict)
            elif attributes.get("link"):
                return BlockTextConverter.handle_link(text_dict)
            elif attributes.get("style-code"):
                return BlockTextConverter.handle_code(text_dict)
            elif attributes.get("style-italic"):
                return BlockTextConverter.handle_italic(text_dict)
            elif attributes.get("style-bold"):
                return BlockTextConverter.handle_bold(text_dict)
            elif attributes.get('style-strikethrough'):
                return BlockTextConverter.handle_strikethrough(text_dict)
            elif attributes.get('style-super') or attributes.get('style-sub'):
                return BlockTextConverter.handle_text(text_dict)
            elif any(key.startswith("style-color-") or key.startswith("style-bg-color-") for key in attributes.keys()):
                return BlockTextConverter.handle_highlight(text_dict)
            else:
                return BlockTextConverter.handle_text(text_dict)
        else:
            return BlockTextConverter.handle_text(text_dict)

    @classmethod
    def handle_link(cls, text_dict):
        return f'[{text_dict["insert"]}]({text_dict["attributes"]["link"]})'

    @classmethod
    def handle_code(cls, text_dict):
        return f'`{text_dict["insert"]}`'

    @classmethod
    def handle_italic(cls, text_dict):
        return f'*{text_dict["insert"]}*'

    @classmethod
    def handle_text(cls, text_dict):
        return text_dict["insert"]

    @classmethod
    def handle_bold(cls, text_dict):
        return f'**{text_dict["insert"]}**'

    @classmethod
    def handle_strikethrough(cls, text_dict):
        return f'~~{text_dict["insert"]}~~'

    @classmethod
    def handle_highlight(cls, text_dict):
        return f'=={text_dict["insert"]}=='

    @classmethod
    def handle_wiki_link(cls, text_dict):
        attributes = text_dict["attributes"]
        name = attributes.get("name", "")
        secondary_name = attributes.get("secondaryName", "")

        if name.endswith('.md'):
            name = name[:-3]

        if secondary_name:
            return f'[[{secondary_name}|{name}]]'
        else:
            return f'[[{name}]]'

    @classmethod
    def handle_math(cls, text_dict):
        attributes = text_dict["attributes"]
        tex = attributes.get("tex", "")
        tex_content = tex.strip()
        return f'${tex_content}$'


class MarkdownConverter:
    """Markdown 转换器"""
    STRATEGY_MAP = {
        "text": TextStrategy,
        "list": ListStrategy,
        "code": CodeStrategy,
        "table": TableStrategy,
        "embed": EmbedStrategy
    }

    @staticmethod
    def to_text(data, block_row):
        strategy = MarkdownConverter.create_strategy(data, block_row)
        return strategy.to_text(block_row)

    @staticmethod
    def create_strategy(data, json_data):
        strategy_type = json_data["type"]
        strategy_class = MarkdownConverter.STRATEGY_MAP.get(strategy_type)
        if strategy_class:
            return strategy_class(data)
        else:
            return TextStrategy(data)


def parse_collaboration_note(origin_content):
    """
    解析协作笔记内容
    :param origin_content: WebSocket 返回的原始 JSON 字符串
    :return: Markdown 格式的笔记内容
    """
    try:
        json_content = json.loads(origin_content)
        text = []

        # 提取 blocks 数据
        blocks = json_content.get('data', {}).get('data', {}).get("blocks", [])

        for block_row in blocks:
            text.append(MarkdownConverter.to_text(json_content['data']['data'], block_row))

        content = ''.join(text)
        return content
    except Exception as e:
        print(f"    ⚠️  协作笔记解析失败: {str(e)}")
        return None
