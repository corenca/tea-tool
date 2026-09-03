"""CSV 相关的通用工具模块。

当前提供 CSV 文件与 polars DataFrame 之间的读写转换（csv_to_df、df_to_csv），
后续其他 CSV 处理方法将持续补充于此。
"""

import io
from pathlib import Path

import polars as pl


def _preprocess(
    text: str, sep: str, replace_sep: str | None, trailing_sep: bool
) -> str:
    """引号感知地处理 CSV 文本：可选替换分隔符、剥离行尾多余分隔符。

    逐字符扫描并维持引号状态（支持 ``""`` 转义与引号字段跨物理行），引号及引号
    字段内容始终原样保留，只对引号外的分隔符做处理：将 ``sep`` 替换为
    ``replace_sep``（多字符分隔符场景替换为单字节哨兵）；当 ``trailing_sep`` 为真
    时，剥离每个记录末尾（引号外）多余的尾随分隔符，避免产生空列。

    Args:
        text: CSV 原始文本。
        sep: 原始分隔符（可为任意长度字符串）。
        replace_sep: 可选，替换目标单字符；为 None 时保留原分隔符不替换。
        trailing_sep: 是否剥离记录末尾多余的尾随分隔符。

    Returns:
        处理后的 CSV 文本，字段结构与引号语义保持不变。
    """
    token = sep if replace_sep is None else replace_sep
    out_lines: list[str] = []
    in_quotes = False
    for line in text.splitlines(keepends=True):
        # 剥离行尾换行符并记住，处理完内容后原样拼回。
        if line.endswith("\r\n"):
            body, eol = line[:-2], "\r\n"
        elif line.endswith(("\n", "\r")):
            body, eol = line[:-1], line[-1]
        else:
            body, eol = line, ""
        buf: list[str] = []
        at_field_start = True
        i, n = 0, len(body)
        while i < n:
            ch = body[i]
            if in_quotes:
                if ch == '"':
                    if i + 1 < n and body[i + 1] == '"':
                        # 引号转义（"" 表示字面引号），原样保留交给解析器。
                        buf.append('""')
                        i += 2
                        continue
                    in_quotes = False
                    at_field_start = False
                    buf.append(ch)
                    i += 1
                    continue
                # 引号内的分隔符子串属于字段内容，原样保留。
                buf.append(ch)
                i += 1
                continue
            if ch == '"' and at_field_start:
                # 仅字段起始处的引号开启引号字段。
                in_quotes = True
                buf.append(ch)
                i += 1
                continue
            if body.startswith(sep, i):
                buf.append(token)
                i += len(sep)
                at_field_start = True
                continue
            buf.append(ch)
            i += 1
            at_field_start = False
        if trailing_sep and not in_quotes and buf and buf[-1] == token:
            # 记录末尾（不在引号字段内）的尾随分隔符。
            buf.pop()
        out_lines.append("".join(buf) + eol)
    return "".join(out_lines)


def _pick_sentinel(text: str) -> str:
    """从 ASCII 控制字符中挑选一个原文未出现的字符作为替换哨兵。"""
    for code in range(1, 32):
        ch = chr(code)
        if ch not in text:
            return ch
    raise ValueError("文本包含全部 ASCII 控制字符，无法确定替换哨兵")


def csv_to_df(
    path: str | Path,
    columns: list[str],
    *,
    dtypes: dict[str, pl.DataType] | None = None,
    sep: str = ",",
    has_header: bool = True,
    trailing_sep: bool = False,
) -> pl.DataFrame:
    """读取 CSV 文件为 polars DataFrame。

    Args:
        path: CSV 文件路径。
        columns: 期望输出的列名列表，输出列按此顺序排列；has_header 为 False
            时直接作为数据列名。
        dtypes: 可选，按列名声明列类型，未声明的列由 polars 自动推断；键必须
            都包含在 columns 中。
        sep: 字段分隔符，支持任意长度字符串。polars 原生仅支持单字节分隔符，
            多字符分隔符会在读取前做引号感知的文本预处理（引号字段内的分隔符
            子串不受影响）。
        has_header: 首行是否为表头。True 时首行作为列名并用于匹配 columns，
            表头中未声明的多余列会被忽略；False 时首行即数据。
        trailing_sep: 每行末尾是否带一个多余分隔符，True 时读取前剥离，避免
            把行尾空字段读成额外空列。

    Returns:
        按 columns 顺序包含声明列的 DataFrame。

    Raises:
        ValueError: 表头缺少声明的列、无表头时文件列数与声明列数不一致、dtypes
            包含未声明的列、sep 为空或无法确定替换哨兵时。
    """
    if not sep:
        raise ValueError("sep 不能为空字符串")
    declared = set(columns)
    if len(declared) != len(columns):
        raise ValueError("columns 不能包含重复列名")
    if dtypes is not None:
        extra = sorted(set(dtypes) - declared)
        if extra:
            raise ValueError(f"dtypes 包含未声明的列: {extra}")

    # 多字符分隔符或行尾带多余分隔符时，需要先做文本预处理。
    source: str | Path = path
    effective_sep = sep
    if len(sep) > 1 or trailing_sep:
        text = Path(path).read_text(encoding="utf-8-sig")
        if len(sep) > 1:
            sentinel = _pick_sentinel(text)
            text = _preprocess(text, sep, sentinel, trailing_sep)
            effective_sep = sentinel
        else:
            text = _preprocess(text, sep, None, trailing_sep)
        source = io.StringIO(text)

    if has_header:
        df = pl.read_csv(
            source,
            separator=effective_sep,
            has_header=True,
            schema_overrides=dtypes,
        )
        missing = [c for c in columns if c not in df.columns]
        if missing:
            raise ValueError(f"表头缺少声明列: {missing}")
        return df.select(columns)

    # 无表头：先读入确认宽度，再赋列名、按需转换类型。
    df = pl.read_csv(source, separator=effective_sep, has_header=False)
    if len(df.columns) != len(columns):
        raise ValueError(f"文件列数({len(df.columns)})与声明列数({len(columns)})不一致")
    df.columns = columns
    if dtypes is not None:
        df = df.with_columns(
            [pl.col(name).cast(dtype) for name, dtype in dtypes.items()]
        )
    return df


def _quote_field(value: str, sep: str) -> str:
    """按 RFC 4180 决定字段是否需要引号包裹并返回序列化结果。

    空字符串或含分隔符、双引号、换行的字段必须用双引号包裹，字段内的双引号
    以 ``""`` 转义；null 不经过本函数，由调用方直接输出为空字段。

    Args:
        value: 字段文本（空字符串表示空串而非 null）。
        sep: 字段分隔符。

    Returns:
        可直接写入 CSV 的字段文本。
    """
    if value == "" or sep in value or '"' in value or "\n" in value or "\r" in value:
        return '"' + value.replace('"', '""') + '"'
    return value


def df_to_csv(
    df: pl.DataFrame,
    path: str | Path,
    sep: str,
    *,
    has_header: bool = True,
    trailing_sep: bool = False,
) -> None:
    """将 polars DataFrame 写出为 CSV 文件。

    单字符分隔符且无行尾分隔符时走 polars 原生写出；多字符分隔符或行尾带
    多余分隔符时改为内部序列化（各列转字符串后按 RFC 4180 包裹需保护的字段），
    保证与 csv_to_df 的读回逻辑对称。null 写为空字段，空字符串写为 ``""``。

    Args:
        df: 待写出的 DataFrame，按现有列顺序写出全部列。
        path: 输出文件路径。
        sep: 字段分隔符，必填，支持任意长度字符串。
        has_header: 是否写表头行，默认 True；表头行同样按字段规则处理列名。
        trailing_sep: 每行末尾（含表头行）是否带一个多余分隔符，默认 False。

    Raises:
        ValueError: sep 为空字符串时。
    """
    if not sep:
        raise ValueError("sep 不能为空字符串")
    if len(sep) == 1 and not trailing_sep:
        df.write_csv(path, separator=sep, include_header=has_header)
        return

    # 各列统一转为字符串，保留 polars 的标准字段表示，再逐行拼接。
    text = df.select([pl.col(col).cast(pl.String) for col in df.columns])
    lines: list[str] = []
    if has_header:
        header = sep.join(_quote_field(col, sep) for col in df.columns)
        lines.append(header + sep if trailing_sep else header)
    for row in text.iter_rows():
        fields = sep.join("" if v is None else _quote_field(v, sep) for v in row)
        lines.append(fields + sep if trailing_sep else fields)
    content = "\n".join(lines)
    if lines:
        content += "\n"
    Path(path).write_text(content, encoding="utf-8", newline="")
