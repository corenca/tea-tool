"""tea_tool.util.collection 切分工具的单元测试。"""

import pytest

from tea_tool.util.collection import chunk_list, chunk_range, split_list, split_range


@pytest.mark.parametrize(
    ("items", "size", "expected"),
    [
        # 基础场景：每块最多 size 个元素。
        (list(range(1, 11)), 3, [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]]),
        # size 为 1：每块恰好一个元素。
        ([1, 2, 3], 1, [[1], [2], [3]]),
        # size 不小于元素数：整体作为一块。
        ([1, 2, 3], 5, [[1, 2, 3]]),
        # 空输入：不产生任何块。
        ([], 2, []),
        # 元素类型不限。
        (["a", "b", "c", "d"], 3, [["a", "b", "c"], ["d"]]),
    ],
)
def test_chunk_list(
    items: list[object], size: int, expected: list[list[object]]
) -> None:
    """chunk_list 按固定大小切分 list。"""
    assert chunk_list(items, size) == expected


@pytest.mark.parametrize("size", [0, -1])
def test_chunk_list_invalid_size_raises(size: int) -> None:
    """chunk_list 对非正 size 抛出 ValueError。"""
    with pytest.raises(ValueError):
        chunk_list([1, 2], size)


@pytest.mark.parametrize(
    ("items", "n", "expected"),
    [
        # 不能整除：余数靠前分配。
        (list(range(1, 9)), 3, [[1, 2, 3], [4, 5, 6], [7, 8]]),
        # 余数为 1：仅第一份多一个元素。
        (list(range(1, 8)), 3, [[1, 2, 3], [4, 5], [6, 7]]),
        # 恰好整除：每份大小相同。
        (list(range(1, 7)), 3, [[1, 2], [3, 4], [5, 6]]),
        # n 为 1：整体作为一块。
        ([1, 2], 1, [[1, 2]]),
        # n 大于元素数：多出的份以空块补齐。
        ([1, 2], 3, [[1], [2], []]),
        # 空输入：不产生任何块。
        ([], 3, []),
    ],
)
def test_split_list(items: list[object], n: int, expected: list[list[object]]) -> None:
    """split_list 按固定份数切分 list，余数靠前。"""
    assert split_list(items, n) == expected


@pytest.mark.parametrize("n", [0, -1])
def test_split_list_invalid_n_raises(n: int) -> None:
    """split_list 对非正份数抛出 ValueError。"""
    with pytest.raises(ValueError):
        split_list([1, 2], n)


@pytest.mark.parametrize(
    ("rng", "size", "expected"),
    [
        # 基础场景。
        (range(10), 3, [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]),
        # 步长大于 1。
        (range(1, 10, 2), 2, [[1, 3], [5, 7], [9]]),
        # 负步长。
        (range(10, 0, -2), 2, [[10, 8], [6, 4], [2]]),
        # 空 range。
        (range(0), 3, []),
    ],
)
def test_chunk_range(rng: range, size: int, expected: list[list[int]]) -> None:
    """chunk_range 按固定大小切分 range，返回 range 切片且元素顺序不变。"""
    result = chunk_range(rng, size)
    assert all(isinstance(part, range) for part in result)
    assert [list(part) for part in result] == expected


@pytest.mark.parametrize("size", [0, -1])
def test_chunk_range_invalid_size_raises(size: int) -> None:
    """chunk_range 对非正 size 抛出 ValueError。"""
    with pytest.raises(ValueError):
        chunk_range(range(3), size)


@pytest.mark.parametrize(
    ("rng", "n", "expected"),
    [
        # 余数靠前分配。
        (range(8), 3, [[0, 1, 2], [3, 4, 5], [6, 7]]),
        # 负步长。
        (range(8, -1, -2), 2, [[8, 6, 4], [2, 0]]),
        # n 大于元素数：多出的份以空块补齐。
        (range(3), 5, [[0], [1], [2], [], []]),
        # 空 range。
        (range(0), 3, []),
    ],
)
def test_split_range(rng: range, n: int, expected: list[list[int]]) -> None:
    """split_range 按固定份数切分 range，返回 range 切片且元素顺序不变。"""
    result = split_range(rng, n)
    assert all(isinstance(part, range) for part in result)
    assert [list(part) for part in result] == expected


@pytest.mark.parametrize("n", [0, -1])
def test_split_range_invalid_n_raises(n: int) -> None:
    """split_range 对非正份数抛出 ValueError。"""
    with pytest.raises(ValueError):
        split_range(range(3), n)
