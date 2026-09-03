"""tea_tool.util.excel 读写 .xlsx 与 polars DataFrame 互转的单元测试。"""

from datetime import date, datetime
from pathlib import Path

import polars as pl
import pytest
import xlsxwriter

from tea_tool.util.excel import df_to_excel, excel_to_df


def _make_xlsx(path: Path, sheet_rows: dict[str, list[list]]) -> None:
    """用 xlsxwriter 手工生成 xlsx 文件，作为独立于被测函数的测试数据来源。

    Args:
        path: 输出文件路径。
        sheet_rows: 工作表名到行列表的映射；单元格值支持 str/int/float/
            bool/None/date，首行不做特殊处理（由调用方决定是否为表头）。
    """
    wb = xlsxwriter.Workbook(path)
    date_fmt = wb.add_format({"num_format": "yyyy-mm-dd"})
    for name, rows in sheet_rows.items():
        ws = wb.add_worksheet(name)
        for row_idx, row in enumerate(rows):
            for col_idx, value in enumerate(row):
                if value is None:
                    ws.write_blank(row_idx, col_idx, None)
                elif isinstance(value, bool):
                    ws.write_boolean(row_idx, col_idx, value)
                elif isinstance(value, (int, float)):
                    ws.write_number(row_idx, col_idx, value)
                elif isinstance(value, datetime):
                    ws.write_datetime(row_idx, col_idx, value, date_fmt)
                else:
                    ws.write(row_idx, col_idx, str(value))
    wb.close()


def _default_frame() -> pl.DataFrame:
    """返回全类型覆盖的 DataFrame，日期/字符串含 null。"""
    return pl.DataFrame(
        {
            "id": [1, 2, None],
            "rate": [1.5, None, 2.5],
            "ok": [True, False, None],
            "day": [date(2024, 1, 2), None, date(2024, 3, 4)],
            "name": ["x", "中文字符", None],
        }
    )


def test_excel_to_df_selects_columns_in_order(tmp_path: Path) -> None:
    """按声明列顺序筛选输出列。"""
    path = tmp_path / "book.xlsx"
    _make_xlsx(path, {"数据": [["id", "name"], [1, "a"], [2, "b"]]})
    df = excel_to_df(path, columns=["name", "id"])
    assert df.columns == ["name", "id"]
    assert df.to_dict(as_series=False) == {
        "name": ["a", "b"],
        "id": [1, 2],
    }


def test_excel_to_df_missing_column_raises(tmp_path: Path) -> None:
    """表头缺少声明列时抛出 ValueError。"""
    path = tmp_path / "book.xlsx"
    _make_xlsx(path, {"数据": [["id", "name"], [1, "a"]]})
    with pytest.raises(ValueError, match="表头缺少声明列"):
        excel_to_df(path, columns=["id", "nope"])


def test_excel_to_df_extra_header_columns_ignored(tmp_path: Path) -> None:
    """表头中的多余列不声明时被忽略。"""
    path = tmp_path / "book.xlsx"
    _make_xlsx(path, {"数据": [["id", "name"], [1, "a"]]})
    df = excel_to_df(path, columns=["name"])
    assert df.columns == ["name"]


def test_excel_to_df_duplicate_columns_raises(tmp_path: Path) -> None:
    """columns 含重复列名时抛出 ValueError。"""
    path = tmp_path / "book.xlsx"
    _make_xlsx(path, {"数据": [["id"], [1]]})
    with pytest.raises(ValueError, match="重复列名"):
        excel_to_df(path, columns=["id", "id"])


def test_excel_to_df_dtypes_override(tmp_path: Path) -> None:
    """dtypes 按声明覆盖列类型，未声明列由引擎推断。"""
    path = tmp_path / "book.xlsx"
    _make_xlsx(path, {"数据": [["id", "name"], [1, "a"]]})
    df = excel_to_df(path, columns=["id", "name"], dtypes={"id": pl.String})
    assert df.schema == {"id": pl.String, "name": pl.String}


def test_excel_to_df_dtypes_undeclared_raises(tmp_path: Path) -> None:
    """dtypes 包含未声明列时抛出 ValueError。"""
    path = tmp_path / "book.xlsx"
    _make_xlsx(path, {"数据": [["id"], [1]]})
    with pytest.raises(ValueError, match="dtypes 包含未声明的列"):
        excel_to_df(path, columns=["id"], dtypes={"id": pl.Int64, "extra": pl.String})


def test_excel_to_df_without_header(tmp_path: Path) -> None:
    """无表头数据按声明列名读取。"""
    path = tmp_path / "book.xlsx"
    _make_xlsx(path, {"数据": [[1, "a"], [2, "b"]]})
    df = excel_to_df(path, columns=["id", "name"], has_header=False)
    assert df.columns == ["id", "name"]
    assert df.to_dict(as_series=False) == {"id": [1, 2], "name": ["a", "b"]}


def test_excel_to_df_width_mismatch_raises(tmp_path: Path) -> None:
    """无表头数据列数与声明列数不一致时抛出 ValueError。"""
    path = tmp_path / "book.xlsx"
    _make_xlsx(path, {"数据": [[1, "a", 3.0]]})
    with pytest.raises(ValueError, match="列数"):
        excel_to_df(path, columns=["id", "name"], has_header=False)


def test_excel_to_df_default_first_sheet(tmp_path: Path) -> None:
    """未指定工作表时默认读取第一个工作表。"""
    path = tmp_path / "book.xlsx"
    _make_xlsx(
        path,
        {"第一个": [["a"], [1]], "第二个": [["x"], [10]]},
    )
    df = excel_to_df(path, columns=["a"])
    assert df.to_dict(as_series=False) == {"a": [1]}


def test_excel_to_df_sheet_name(tmp_path: Path) -> None:
    """按 sheet_name 读取指定工作表。"""
    path = tmp_path / "book.xlsx"
    _make_xlsx(
        path,
        {"第一个": [["a"], [1]], "第二个": [["x"], [10]]},
    )
    df = excel_to_df(path, columns=["x"], sheet_name="第二个")
    assert df.to_dict(as_series=False) == {"x": [10]}


def test_excel_to_df_sheet_name_not_found_raises(tmp_path: Path) -> None:
    """指定不存在的 sheet_name 时抛出异常。"""
    path = tmp_path / "book.xlsx"
    _make_xlsx(path, {"数据": [["id"], [1]]})
    with pytest.raises(Exception, match="nope"):
        excel_to_df(path, columns=["id"], sheet_name="nope")


def test_df_to_excel_invalid_sheet_name_raises(tmp_path: Path) -> None:
    """工作表名含 Excel 非法字符时抛出 ValueError。"""
    df = pl.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="sheet_name"):
        df_to_excel(df, tmp_path / "out.xlsx", sheet_name="a*b")


def test_df_to_excel_roundtrip_all_types(tmp_path: Path) -> None:
    """写出后读回，各列数据与类型保持一致。"""
    df = _default_frame()
    path = tmp_path / "out.xlsx"
    df_to_excel(df, path)
    back = excel_to_df(path, columns=df.columns)
    assert back.to_dict(as_series=False) == df.to_dict(as_series=False)


def test_df_to_excel_sheet_name_roundtrip(tmp_path: Path) -> None:
    """指定中文工作表名写出后按同名读回。"""
    df = pl.DataFrame({"a": [1, 2]})
    path = tmp_path / "out.xlsx"
    df_to_excel(df, path, sheet_name="数据表")
    back = excel_to_df(path, columns=["a"], sheet_name="数据表")
    assert back.to_dict(as_series=False) == {"a": [1, 2]}


def test_df_to_excel_default_sheet_name_roundtrip(tmp_path: Path) -> None:
    """默认工作表名写出后不经 sheet_name 直接读回。"""
    df = pl.DataFrame({"a": [1, 2]})
    path = tmp_path / "out.xlsx"
    df_to_excel(df, path)
    back = excel_to_df(path, columns=["a"])
    assert back.to_dict(as_series=False) == {"a": [1, 2]}


def test_df_to_excel_empty_frame_roundtrip(tmp_path: Path) -> None:
    """空 DataFrame 写出后仅含表头，读回为 0 行。"""
    df = pl.DataFrame({"a": [], "b": []})
    path = tmp_path / "out.xlsx"
    df_to_excel(df, path)
    back = excel_to_df(path, columns=["a", "b"])
    assert back.shape == (0, 2)
    assert back.columns == ["a", "b"]


def test_df_to_excel_datetime_roundtrip(tmp_path: Path) -> None:
    """时间列写出读回后时间点保持一致（单位归一后比较）。"""
    ts = datetime(2024, 1, 2, 3, 4, 5)  # noqa: DTZ001 测试刻意使用 naive 时间
    df = pl.DataFrame({"ts": [ts, None], "id": [1, 2]})
    path = tmp_path / "out.xlsx"
    df_to_excel(df, path)
    back = excel_to_df(path, columns=df.columns).with_columns(
        pl.col("ts").cast(pl.Datetime("us"))
    )
    assert back.equals(df)
