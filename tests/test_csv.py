"""tea_tool.util.csv 读写 CSV 与 polars DataFrame 互转的单元测试。"""

from pathlib import Path

import polars as pl
import pytest

from tea_tool.util.csv import csv_to_df, df_to_csv


def _write_fixture(tmp_path: Path, content: str) -> str:
    """将 CSV 文本写入临时文件，返回文件路径。"""
    path = tmp_path / "data.csv"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_csv_to_df_selects_columns_in_order(tmp_path: Path) -> None:
    """有表头时按声明列名筛选，且输出列顺序与声明一致。"""
    path = _write_fixture(tmp_path, "type,amount,name\nA,1,x\nB,2,y\n")
    df = csv_to_df(path, columns=["name", "type"])
    assert df.columns == ["name", "type"]
    assert df.to_dict(as_series=False) == {
        "name": ["x", "y"],
        "type": ["A", "B"],
    }


def test_csv_to_df_missing_column_raises(tmp_path: Path) -> None:
    """有表头时声明列在表头中缺失抛出 ValueError 并列出缺失列名。"""
    path = _write_fixture(tmp_path, "type,amount\nA,1\n")
    with pytest.raises(ValueError, match="nope"):
        csv_to_df(path, columns=["type", "nope"])


def test_csv_to_df_without_header_assigns_columns(tmp_path: Path) -> None:
    """无表头时首行即数据，声明列名直接赋给数据列。"""
    path = _write_fixture(tmp_path, "1,2,3\n4,5,6\n")
    df = csv_to_df(path, columns=["a", "b", "c"], has_header=False)
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
def test_csv_to_df_without_header_width_mismatch_raises(
    tmp_path: Path, content: str, columns: list[str]
) -> None:
    """无表头时文件列数与声明列数不一致抛出 ValueError。"""
    path = _write_fixture(tmp_path, content)
    with pytest.raises(ValueError, match="不一致"):
        csv_to_df(path, columns=columns, has_header=False)


def test_csv_to_df_dtypes_override(tmp_path: Path) -> None:
    """声明列类型生效，未声明类型的列由 polars 推断。"""
    path = _write_fixture(tmp_path, "id,name,amount\n1,x,1.5\n")
    df = csv_to_df(
        path,
        columns=["id", "name", "amount"],
        dtypes={"id": pl.Utf8, "amount": pl.Float64},
    )
    assert df.schema == {"id": pl.Utf8, "name": pl.String, "amount": pl.Float64}


def test_csv_to_df_dtypes_without_header(tmp_path: Path) -> None:
    """无表头时声明列类型同样生效。"""
    path = _write_fixture(tmp_path, "1,2.5\n")
    df = csv_to_df(
        path,
        columns=["a", "b"],
        has_header=False,
        dtypes={"a": pl.Int64, "b": pl.Utf8},
    )
    assert df.schema == {"a": pl.Int64, "b": pl.Utf8}


def test_csv_to_df_dtypes_unexpected_key_raises(tmp_path: Path) -> None:
    """dtypes 含未声明列时抛出 ValueError。"""
    path = _write_fixture(tmp_path, "a\n1\n")
    with pytest.raises(ValueError, match="zz"):
        csv_to_df(path, columns=["a"], dtypes={"zz": pl.Int64})


def test_csv_to_df_multi_char_separator(tmp_path: Path) -> None:
    """分隔符支持长度大于 1 的多字符串。"""
    path = _write_fixture(tmp_path, "a||b||c\n1||2||3\n")
    df = csv_to_df(path, columns=["a", "b", "c"], sep="||")
    assert df.to_dict(as_series=False) == {"a": [1], "b": [2], "c": [3]}


def test_csv_to_df_multi_char_separator_quoted_field(tmp_path: Path) -> None:
    """引号字段内出现分隔符子串时不损坏内容。"""
    path = _write_fixture(tmp_path, 'a||b\n"x||y"||2\n')
    df = csv_to_df(path, columns=["a", "b"], sep="||")
    assert df.to_dict(as_series=False) == {"a": ["x||y"], "b": [2]}


def test_csv_to_df_trailing_separator_with_header(tmp_path: Path) -> None:
    """每行末尾多余分隔符在声明 trailing_sep 后被剥离。"""
    path = _write_fixture(tmp_path, "a,b,\n1,2,\n")
    df = csv_to_df(path, columns=["a", "b"], trailing_sep=True)
    assert df.columns == ["a", "b"]
    assert df.to_dict(as_series=False) == {"a": [1], "b": [2]}


def test_csv_to_df_trailing_separator_without_header(tmp_path: Path) -> None:
    """无表头且每行末尾带多余分隔符时正确剥离。"""
    path = _write_fixture(tmp_path, "1,2,\n3,4,\n")
    df = csv_to_df(path, columns=["a", "b"], has_header=False, trailing_sep=True)
    assert df.to_dict(as_series=False) == {"a": [1, 3], "b": [2, 4]}


def test_csv_to_df_trailing_separator_quoted_last_field(tmp_path: Path) -> None:
    """行尾剥离不影响作为末字段的引号字段内容。"""
    path = _write_fixture(tmp_path, 'a,b,\n1,"x,y",\n')
    df = csv_to_df(path, columns=["a", "b"], trailing_sep=True)
    assert df.to_dict(as_series=False) == {"a": [1], "b": ["x,y"]}


def test_csv_to_df_multiline_quoted_field(tmp_path: Path) -> None:
    """引号字段可跨物理行（单字符分隔符走 polars 原生解析）。"""
    path = _write_fixture(tmp_path, 'a,b\n"x\ny",2\n')
    df = csv_to_df(path, columns=["a", "b"])
    assert df.to_dict(as_series=False) == {"a": ["x\ny"], "b": [2]}


def test_csv_to_df_multiline_quoted_field_multi_char_sep(tmp_path: Path) -> None:
    """多字符分隔符下引号字段跨物理行且含分隔符子串不损坏。"""
    path = _write_fixture(tmp_path, 'a||b\n"x\n||y"||2\n')
    df = csv_to_df(path, columns=["a", "b"], sep="||")
    assert df.to_dict(as_series=False) == {"a": ["x\n||y"], "b": [2]}


def test_csv_to_df_duplicate_columns_raises(tmp_path: Path) -> None:
    """columns 含重复列名时抛出 ValueError。"""
    path = _write_fixture(tmp_path, "a,b\n1,2\n")
    with pytest.raises(ValueError, match="重复"):
        csv_to_df(path, columns=["a", "a"])


def test_csv_to_df_empty_sep_raises(tmp_path: Path) -> None:
    """分隔符为空字符串时抛出 ValueError。"""
    path = _write_fixture(tmp_path, "a\n1\n")
    with pytest.raises(ValueError, match="sep"):
        csv_to_df(path, columns=["a"], sep="")


def test_csv_to_df_bom_with_preprocess(tmp_path: Path) -> None:
    """带 BOM 表头走预处理路径（多字符分隔符）时列名不被污染。"""
    path = _write_fixture(tmp_path, "\ufeffa||b\n1||2\n")
    df = csv_to_df(path, columns=["a", "b"], sep="||")
    assert df.columns == ["a", "b"]
    assert df.to_dict(as_series=False) == {"a": [1], "b": [2]}


def test_csv_to_df_header_only_returns_empty_frame(tmp_path: Path) -> None:
    """文件仅含表头时返回 0 行的空 DataFrame。"""
    path = _write_fixture(tmp_path, "a,b\n")
    df = csv_to_df(path, columns=["a"])
    assert df.shape == (0, 1)
    assert df.columns == ["a"]


_DF = pl.DataFrame(
    {
        "id": [1, 2, None],
        "rate": [1.5, None, 2.5],
        "ok": [True, False, None],
        "name": ["x,y", 'say "hi"', None],
        "note": ["", "line\nbr", "z"],
    }
)


def test_df_to_csv_roundtrip_native(tmp_path: Path) -> None:
    """单字符分隔符写出后读回，数据与类型保持一致。"""
    path = tmp_path / "out.csv"
    df_to_csv(_DF, path, sep=",")
    back = csv_to_df(path, columns=_DF.columns)
    assert back.equals(_DF)


def test_df_to_csv_roundtrip_multi_char_sep(tmp_path: Path) -> None:
    """多字符分隔符写出后读回一致，含分隔符子串的字段被正确保护。"""
    df = pl.DataFrame({"id": [1, 2], "tags": ["a||b", "c"]})
    path = tmp_path / "out.csv"
    df_to_csv(df, path, sep="||")
    assert path.read_text(encoding="utf-8") == 'id||tags\n1||"a||b"\n2||c\n'
    back = csv_to_df(path, columns=df.columns, sep="||")
    assert back.equals(df)


def test_df_to_csv_roundtrip_trailing_sep(tmp_path: Path) -> None:
    """行尾带分隔符写出后，声明 trailing_sep 读回一致。"""
    path = tmp_path / "out.csv"
    df_to_csv(_DF, path, sep=",", trailing_sep=True)
    assert path.read_text(encoding="utf-8").startswith("id,rate,ok,name,note,\n")
    back = csv_to_df(path, columns=_DF.columns, trailing_sep=True)
    assert back.equals(_DF)


def test_df_to_csv_trailing_sep_text_precise(tmp_path: Path) -> None:
    """表头行与数据行末尾都带尾随分隔符。"""
    df = pl.DataFrame({"a": [1], "b": ["x"]})
    path = tmp_path / "out.csv"
    df_to_csv(df, path, sep=",", trailing_sep=True)
    assert path.read_text(encoding="utf-8") == "a,b,\n1,x,\n"


def test_df_to_csv_roundtrip_multi_char_and_trailing(tmp_path: Path) -> None:
    """多字符分隔符与行尾分隔符组合，写读往返一致。"""
    df = pl.DataFrame({"a": ["x||y", None], "b": [1, 2]})
    path = tmp_path / "out.csv"
    df_to_csv(df, path, sep="||", trailing_sep=True)
    back = csv_to_df(path, columns=df.columns, sep="||", trailing_sep=True)
    assert back.equals(df)


def test_df_to_csv_without_header_roundtrip(tmp_path: Path) -> None:
    """无表头写出后，声明列名读回一致。"""
    df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    path = tmp_path / "out.csv"
    df_to_csv(df, path, sep=",", has_header=False)
    back = csv_to_df(path, columns=df.columns, has_header=False)
    assert back.equals(df)


def test_df_to_csv_special_column_names(tmp_path: Path) -> None:
    """含分隔符的列名写表头时被引号包裹，读回后保持原样。"""
    df = pl.DataFrame({"a,b": [1], "name": [2]})
    path = tmp_path / "out.csv"
    df_to_csv(df, path, sep=",")
    assert path.read_text(encoding="utf-8").startswith('"a,b",name\n')
    back = csv_to_df(path, columns=df.columns)
    assert back.columns == df.columns
    assert back.to_dict(as_series=False) == df.to_dict(as_series=False)


def test_df_to_csv_empty_sep_raises(tmp_path: Path) -> None:
    """分隔符为空字符串时抛出 ValueError。"""
    df = pl.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="sep"):
        df_to_csv(df, tmp_path / "out.csv", sep="")
