"""Excel 相关的通用工具模块。

当前提供 .xlsx 文件与 polars DataFrame 之间的读写转换（excel_to_df、df_to_excel），
后续其他 Excel 处理方法将持续补充于此。依赖 fastexcel（读取引擎）与
xlsxwriter（写出引擎），随 ``excel`` 可选依赖安装。
"""

from pathlib import Path

import polars as pl
from xlsxwriter.exceptions import InvalidWorksheetName


def _validate_columns_dtypes(
    columns: list[str], dtypes: dict[str, pl.DataType] | None
) -> None:
    """校验 columns 无重复且 dtypes 的键都包含在 columns 中。

    Args:
        columns: 期望输出的列名列表。
        dtypes: 按列声明的类型映射。

    Raises:
        ValueError: columns 含重复列名或 dtypes 含未声明列时。
    """
    if len(set(columns)) != len(columns):
        raise ValueError("columns 不能包含重复列名")
    if dtypes is not None:
        extra = sorted(set(dtypes) - set(columns))
        if extra:
            raise ValueError(f"dtypes 包含未声明的列: {extra}")


def excel_to_df(
    path: str | Path,
    columns: list[str],
    *,
    dtypes: dict[str, pl.DataType] | None = None,
    sheet_name: str | None = None,
    has_header: bool = True,
) -> pl.DataFrame:
    """读取 Excel 文件为 polars DataFrame。

    底层使用 polars 的 calamine 引擎（fastexcel 提供），支持 .xlsx/.xlsb/.xls。

    Args:
        path: Excel 文件路径。
        columns: 期望输出的列名列表，输出列按此顺序排列；has_header 为 False
            时直接作为数据列名。
        dtypes: 可选，按列名声明列类型，未声明的列由引擎推断；键必须都包含
            在 columns 中。
        sheet_name: 可选，工作表名；为 None 时读取第一个工作表。
        has_header: 首行是否为表头。True 时首行作为列名并用于匹配 columns，
            表头中未声明的多余列会被忽略；False 时首行即数据。

    Returns:
        按 columns 顺序包含声明列的 DataFrame。

    Raises:
        ValueError: 表头缺少声明的列、无表头时文件列数与声明列数不一致、columns
            含重复列名、dtypes 包含未声明的列时。
    """
    _validate_columns_dtypes(columns, dtypes)
    kwargs: dict[str, object] = {"has_header": has_header}
    if dtypes is not None:
        kwargs["schema_overrides"] = dtypes
    if sheet_name is not None:
        kwargs["sheet_name"] = sheet_name
    df = pl.read_excel(path, **kwargs)

    if has_header:
        missing = [c for c in columns if c not in df.columns]
        if missing:
            raise ValueError(f"表头缺少声明列: {missing}")
        return df.select(columns)

    # 无表头：确认宽度后赋列名，再按需转换类型。
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
        ValueError: sheet_name 包含 Excel 非法字符（[]:*?/\\）时。
    """
    try:
        df.write_excel(path, worksheet=sheet_name)
    except InvalidWorksheetName as exc:
        # 统一为 ValueError，保持与 csv 模块一致的错误风格。
        raise ValueError(f"sheet_name 不合法: {exc}") from exc
