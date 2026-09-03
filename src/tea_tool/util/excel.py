"""Excel 相关的通用工具模块。

当前提供 .xlsx 文件与 polars DataFrame 之间的读写转换（excel_to_df、df_to_excel），
后续其他 Excel 处理方法将持续补充于此。

依赖：fastexcel（读取引擎）与 xlsxwriter（写出引擎），需安装 excel 可选依赖：

- pip: pip install 'tea-tool[excel]'
- uv: uv add 'tea-tool[excel]'

缺失依赖时调用对应功能会抛出带安装指引的 ImportError。
"""

import importlib.util
from pathlib import Path

import polars as pl


def _normalize_columns(
    columns: list[str] | dict[str, str], has_header: bool
) -> list[tuple[str, str]]:
    """将 columns 的两种形态统一为 (内存列名, 文件表头名) 有序对。

    list 形态表示内存列名与文件表头同名；dict 形态的键为加载后的内存列名、
    值为文件表头名（仅在有表头文件上可用），输出按字典顺序。

    Args:
        columns: 列名列表，或内存列名到文件表头名的映射。
        has_header: 文件首行是否为表头。

    Returns:
        (内存列名, 文件表头名) 有序对列表。

    Raises:
        ValueError: list 含重复列名、dict 将多个列名映射到同一表头、dict 用于
            无表头文件时。
    """
    if isinstance(columns, dict):
        if not has_header:
            raise ValueError("has_header=False 时 columns 必须为列名列表")
        headers = list(columns.values())
        if len(set(headers)) != len(headers):
            duplicated = sorted({h for h in headers if headers.count(h) > 1})
            raise ValueError(f"columns 不能将多个列名映射到同一文件表头: {duplicated}")
        return list(columns.items())
    if len(set(columns)) != len(columns):
        raise ValueError("columns 不能包含重复列名")
    return [(name, name) for name in columns]


def _ensure_installed(*packages: str) -> None:
    """确认 excel 可选依赖已安装，缺失时抛出带安装指引的 ImportError。

    Args:
        packages: 需要确认已安装的依赖包名。

    Raises:
        ImportError: 任一依赖包缺失时，提示安装 tea-tool[excel]。
    """
    missing = [p for p in packages if importlib.util.find_spec(p) is None]
    if missing:
        raise ImportError(
            f"使用该功能需要安装 excel 可选依赖（缺少 {', '.join(missing)}），"
            "安装方式：pip install 'tea-tool[excel]' 或 uv add 'tea-tool[excel]'"
        )


def excel_to_df(
    path: str | Path,
    columns: list[str] | dict[str, str],
    *,
    dtypes: dict[str, pl.DataType] | None = None,
    sheet_name: str | None = None,
    has_header: bool = True,
) -> pl.DataFrame:
    """读取 Excel 文件为 polars DataFrame。

    底层使用 polars 的 calamine 引擎（fastexcel 提供），支持 .xlsx/.xlsb/.xls。

    Args:
        path: Excel 文件路径。
        columns: 列名列表或映射，输出列按此顺序排列。列表形态要求列名与文件
            表头同名；映射形态的键为加载后的内存列名、值为文件表头名（如
            {"id": "编号"}），仅用于有表头文件。has_header 为 False 时列表形态
            直接作为数据列名。
        dtypes: 可选，按内存列名声明列类型，未声明的列由引擎推断；键必须都
            包含在 columns 中。
        sheet_name: 可选，工作表名；为 None 时读取第一个工作表。
        has_header: 首行是否为表头。True 时首行作为列名并用于匹配 columns，
            表头中未声明的多余列会被忽略；False 时首行即数据。

    Returns:
        按 columns 顺序包含声明列的 DataFrame。

    Raises:
        ImportError: 缺少 fastexcel 依赖时。
        ValueError: 表头缺少声明的列、无表头时文件列数与声明列数不一致、columns
            含重复列名或映射异常、dtypes 包含未声明的列时。
    """
    _ensure_installed("fastexcel")
    pairs = _normalize_columns(columns, has_header)
    names = [memory for memory, _ in pairs]
    if dtypes is not None:
        extra = sorted(set(dtypes) - set(names))
        if extra:
            raise ValueError(f"dtypes 包含未声明的列: {extra}")

    if has_header:
        # 读取时按文件表头名声明类型覆盖，输出时再改为内存列名。
        header_of = dict(pairs)
        kwargs: dict[str, object] = {"has_header": True}
        if dtypes is not None:
            kwargs["schema_overrides"] = {
                header_of[name]: dtype for name, dtype in dtypes.items()
            }
        if sheet_name is not None:
            kwargs["sheet_name"] = sheet_name
        df = pl.read_excel(path, **kwargs)
        missing = [header for _, header in pairs if header not in df.columns]
        if missing:
            raise ValueError(f"表头缺少声明列: {missing}")
        # 按声明顺序选择并按需改名；列表形态改名与原列名相同，结果不变。
        return df.select([pl.col(header).alias(memory) for memory, header in pairs])

    # 无表头：columns 已保证为列表形态，确认宽度后赋列名，再按需转换类型。
    df = pl.read_excel(path, has_header=False, sheet_name=sheet_name)
    if len(df.columns) != len(columns):
        raise ValueError(f"文件列数({len(df.columns)})与声明列数({len(columns)})不一致")
    df.columns = columns
    if dtypes is not None:
        df = df.with_columns(
            [pl.col(name).cast(dtype) for name, dtype in dtypes.items()]
        )
    return df


def df_to_excel(
    df: pl.DataFrame,
    path: str | Path,
    *,
    sheet_name: str = "Sheet1",
) -> None:
    """将 polars DataFrame 写出为 Excel 文件。

    底层使用 polars 的 write_excel（xlsxwriter 提供），按现有列顺序写出全部
    列并带表头行；文件已存在时直接覆盖。数值、日期时间、字符串与布尔列按
    各自语义写入，null 写为空单元格。

    Args:
        df: 待写出的 DataFrame，按现有列顺序写出全部列。
        path: 输出文件路径。
        sheet_name: 工作表名，默认 "Sheet1"。

    Raises:
        ImportError: 缺少 xlsxwriter 依赖时。
        ValueError: sheet_name 包含 Excel 非法字符（[]:*?/\\）时。
    """
    _ensure_installed("xlsxwriter")
    from xlsxwriter.exceptions import InvalidWorksheetName

    try:
        df.write_excel(path, worksheet=sheet_name)
    except InvalidWorksheetName as exc:
        # 统一为 ValueError，保持与 csv 模块一致的错误风格。
        raise ValueError(f"sheet_name 不合法: {exc}") from exc
