"""tea_tool.util.csv 读取 CSV 为 polars DataFrame 的单元测试。"""

from pathlib import Path

import polars as pl
import pytest

from tea_tool.util.csv import read_csv


def _write_csv(tmp_path: Path, content: str) -> str:
    """将 CSV 文本写入临时文件，返回文件路径。"""
    path = tmp_path / "data.csv"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_read_csv_selects_columns_in_order(tmp_path: Path) -> None:
    """有表头时按声明列名筛选，且输出列顺序与声明一致。"""
    path = _write_csv(tmp_path, "type,amount,name\nA,1,x\nB,2,y\n")
    df = read_csv(path, columns=["name", "type"])
    assert df.columns == ["name", "type"]
    assert df.to_dict(as_series=False) == {
        "name": ["x", "y"],
        "type": ["A", "B"],
    }


def test_read_csv_missing_column_raises(tmp_path: Path) -> None:
    """有表头时声明列在表头中缺失抛出 ValueError 并列出缺失列名。"""
    path = _write_csv(tmp_path, "type,amount\nA,1\n")
    with pytest.raises(ValueError, match="nope"):
        read_csv(path, columns=["type", "nope"])


def test_read_csv_without_header_assigns_columns(tmp_path: Path) -> None:
    """无表头时首行即数据，声明列名直接赋给数据列。"""
    path = _write_csv(tmp_path, "1,2,3\n4,5,6\n")
    df = read_csv(path, columns=["a", "b", "c"], has_header=False)
    assert df.columns == ["a", "b", "c"]
    assert df.to_dict(as_series=False) == {"a": [1, 4], "b": [2, 5], "c": [3, 6]}


@pytest.mark.parametrize(
    ("content", "columns"),
    [
        # 数据列多于声明列。
        ("1,2\n3,4\n", ["a"]),
        # 数据列少于声明列。
        ("1\n3\n", ["a", "b"]),
    ],
)
def test_read_csv_without_header_width_mismatch_raises(
    tmp_path: Path, content: str, columns: list[str]
) -> None:
    """无表头时文件列数与声明列数不一致抛出 ValueError。"""
    path = _write_csv(tmp_path, content)
    with pytest.raises(ValueError, match="不一致"):
        read_csv(path, columns=columns, has_header=False)


def test_read_csv_dtypes_override(tmp_path: Path) -> None:
    """声明列类型生效，未声明类型的列由 polars 推断。"""
    path = _write_csv(tmp_path, "id,name,amount\n1,x,1.5\n")
    df = read_csv(
        path,
        columns=["id", "name", "amount"],
        dtypes={"id": pl.Utf8, "amount": pl.Float64},
    )
    assert df.schema == {"id": pl.Utf8, "name": pl.String, "amount": pl.Float64}


def test_read_csv_dtypes_without_header(tmp_path: Path) -> None:
    """无表头时声明列类型同样生效。"""
    path = _write_csv(tmp_path, "1,2.5\n")
    df = read_csv(
        path,
        columns=["a", "b"],
        has_header=False,
        dtypes={"a": pl.Int64, "b": pl.Utf8},
    )
    assert df.schema == {"a": pl.Int64, "b": pl.Utf8}


def test_read_csv_dtypes_unexpected_key_raises(tmp_path: Path) -> None:
    """dtypes 含未声明列时抛出 ValueError。"""
    path = _write_csv(tmp_path, "a\n1\n")
    with pytest.raises(ValueError, match="zz"):
        read_csv(path, columns=["a"], dtypes={"zz": pl.Int64})


def test_read_csv_multi_char_separator(tmp_path: Path) -> None:
    """分隔符支持长度大于 1 的多字符串。"""
    path = _write_csv(tmp_path, "a||b||c\n1||2||3\n")
    df = read_csv(path, columns=["a", "b", "c"], sep="||")
    assert df.to_dict(as_series=False) == {"a": [1], "b": [2], "c": [3]}


def test_read_csv_multi_char_separator_quoted_field(tmp_path: Path) -> None:
    """引号字段内出现分隔符子串时不损坏内容。"""
    path = _write_csv(tmp_path, 'a||b\n"x||y"||2\n')
    df = read_csv(path, columns=["a", "b"], sep="||")
    assert df.to_dict(as_series=False) == {"a": ["x||y"], "b": [2]}


def test_read_csv_trailing_separator_with_header(tmp_path: Path) -> None:
    """每行末尾多余分隔符在声明 trailing_sep 后被剥离。"""
    path = _write_csv(tmp_path, "a,b,\n1,2,\n")
    df = read_csv(path, columns=["a", "b"], trailing_sep=True)
    assert df.columns == ["a", "b"]
    assert df.to_dict(as_series=False) == {"a": [1], "b": [2]}


def test_read_csv_trailing_separator_without_header(tmp_path: Path) -> None:
    """无表头且每行末尾带多余分隔符时正确剥离。"""
    path = _write_csv(tmp_path, "1,2,\n3,4,\n")
    df = read_csv(path, columns=["a", "b"], has_header=False, trailing_sep=True)
    assert df.to_dict(as_series=False) == {"a": [1, 3], "b": [2, 4]}


def test_read_csv_trailing_separator_quoted_last_field(tmp_path: Path) -> None:
    """行尾剥离不影响作为末字段的引号字段内容。"""
    path = _write_csv(tmp_path, 'a,b,\n1,"x,y",\n')
    df = read_csv(path, columns=["a", "b"], trailing_sep=True)
    assert df.to_dict(as_series=False) == {"a": [1], "b": ["x,y"]}


def test_read_csv_multiline_quoted_field(tmp_path: Path) -> None:
    """引号字段可跨物理行（单字符分隔符走 polars 原生解析）。"""
    path = _write_csv(tmp_path, 'a,b\n"x\ny",2\n')
    df = read_csv(path, columns=["a", "b"])
    assert df.to_dict(as_series=False) == {"a": ["x\ny"], "b": [2]}


def test_read_csv_multiline_quoted_field_multi_char_sep(tmp_path: Path) -> None:
    """多字符分隔符下引号字段跨物理行且含分隔符子串不损坏。"""
    path = _write_csv(tmp_path, 'a||b\n"x\n||y"||2\n')
    df = read_csv(path, columns=["a", "b"], sep="||")
    assert df.to_dict(as_series=False) == {"a": ["x\n||y"], "b": [2]}


def test_read_csv_duplicate_columns_raises(tmp_path: Path) -> None:
    """columns 含重复列名时抛出 ValueError。"""
    path = _write_csv(tmp_path, "a,b\n1,2\n")
    with pytest.raises(ValueError, match="重复"):
        read_csv(path, columns=["a", "a"])


def test_read_csv_empty_sep_raises(tmp_path: Path) -> None:
    """分隔符为空字符串时抛出 ValueError。"""
    path = _write_csv(tmp_path, "a\n1\n")
    with pytest.raises(ValueError, match="sep"):
        read_csv(path, columns=["a"], sep="")


def test_read_csv_bom_with_preprocess(tmp_path: Path) -> None:
    """带 BOM 表头走预处理路径（多字符分隔符）时列名不被污染。"""
    path = _write_csv(tmp_path, "\ufeffa||b\n1||2\n")
    df = read_csv(path, columns=["a", "b"], sep="||")
    assert df.columns == ["a", "b"]
    assert df.to_dict(as_series=False) == {"a": [1], "b": [2]}


def test_read_csv_header_only_returns_empty_frame(tmp_path: Path) -> None:
    """文件仅含表头时返回 0 行的空 DataFrame。"""
    path = _write_csv(tmp_path, "a,b\n")
    df = read_csv(path, columns=["a"])
    assert df.shape == (0, 1)
    assert df.columns == ["a"]
