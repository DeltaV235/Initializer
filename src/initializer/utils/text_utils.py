"""UI utility functions for text truncation and display."""

import re


def truncate_text_two_lines(text: str, max_line_length: int = 80) -> str:
    """
    将文本截断为最多两行，超出部分用"..."表示。

    Args:
        text: 要截断的文本
        max_line_length: 每行最大字符长度，默认80个字符

    Returns:
        截断后的文本，最多两行，超出部分显示"..."
    """
    if not text:
        return text

    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text.strip())

    # 如果文本本身就很短，直接返回
    if len(text) <= max_line_length:
        return text

    # 尝试在单词边界处分割第一行
    first_line_end = max_line_length
    if len(text) > max_line_length:
        # 寻找最近的空格位置
        space_pos = text.rfind(' ', 0, max_line_length)
        if space_pos > max_line_length * 0.7:  # 至少保留70%的长度
            first_line_end = space_pos

    first_line = text[:first_line_end].strip()
    remaining_text = text[first_line_end:].strip()

    # 如果没有剩余文本，直接返回第一行
    if not remaining_text:
        return first_line

    # 检查是否需要第二行截断
    if len(remaining_text) <= max_line_length - 3:  # 减去"..."的长度
        return f"{first_line}\n{remaining_text}"
    else:
        # 第二行也需要截断
        second_line_end = max_line_length - 3
        if len(remaining_text) > max_line_length - 3:
            # 寻找最近的空格位置
            space_pos = remaining_text.rfind(' ', 0, second_line_end)
            if space_pos > (max_line_length - 3) * 0.7:
                second_line_end = space_pos

        second_line = remaining_text[:second_line_end].strip()
        return f"{first_line}\n{second_line}..."


def truncate_command_for_display(command: str, max_length: int = 120) -> str:
    """
    截断命令行文本用于显示，保留关键信息。

    Args:
        command: 命令行文本
        max_length: 最大显示长度，默认120个字符

    Returns:
        截断后的命令文本
    """
    if not command:
        return command

    # 移除多余的空白字符
    command = re.sub(r'\s+', ' ', command.strip())

    if len(command) <= max_length:
        return command

    # 尝试在逻辑位置分割命令
    # 优先在 && ; || | 等操作符处分割
    separators = [' && ', '; ', ' || ', ' | ']

    for sep in separators:
        if sep in command:
            parts = command.split(sep)
            if len(parts) >= 2:
                # 保留第一部分的主要命令
                first_part = parts[0].strip()
                if len(first_part) <= max_length - 15:  # 留出空间显示分隔符和...
                    return f"{first_part}{sep}..."

    # 如果没有合适的分隔符，直接截断
    return command[:max_length - 3] + "..."


def format_log_output(line: str, max_length: int = 100) -> str:
    """
    格式化日志输出文本，确保合适的显示长度，保留必要的缩进信息。

    Args:
        line: 日志行文本
        max_length: 最大显示长度，默认100个字符

    Returns:
        格式化后的日志文本
    """
    if not line:
        return line

    # 移除行尾的空白字符，但保留行首缩进和内部空白结构
    line = line.rstrip()

    if len(line) <= max_length:
        return line

    # 对于日志，优先在单词边界截断，但保留缩进
    # 检测行首的缩进（空格或制表符）
    leading_whitespace = ''
    if line and (line[0] == ' ' or line[0] == '\t'):
        match = re.match(r'^[ \t]+', line)
        if match:
            leading_whitespace = match.group(0)

    # 如果有缩进，为内容部分计算剩余长度
    if leading_whitespace:
        content_max_length = max_length - len(leading_whitespace)
        if content_max_length <= 10:  # 如果缩进太长，直接截断
            return line[:max_length - 3] + "..."

        content_part = line[len(leading_whitespace):]

        # 对内容部分进行截断
        if len(content_part) <= content_max_length:
            return line

        # 优先在单词边界截断内容
        if ' ' in content_part:
            words = content_part.split(' ')
            result = words[0]

            for word in words[1:]:
                if len(result) + 1 + len(word) <= content_max_length - 3:
                    result += ' ' + word
                else:
                    break

            return leading_whitespace + result + "..."
        else:
            # 没有空格，直接截断
            return leading_whitespace + content_part[:content_max_length - 3] + "..."
    else:
        # 没有缩进，正常截断
        if ' ' in line:
            words = line.split(' ')
            result = words[0]

            for word in words[1:]:
                if len(result) + 1 + len(word) <= max_length - 3:
                    result += ' ' + word
                else:
                    break

            return result + "..."
        else:
            return line[:max_length - 3] + "..."