from collections.abc import Generator


def yield_lines(lines: list[str]) -> Generator[bytes, None, None]:
    """将日志列表转换为流式字节输出。"""

    for line in lines:
        payload = f"{line}\n"
        yield payload.encode("utf-8")
