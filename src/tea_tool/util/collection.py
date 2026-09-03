import logging
from collections.abc import Iterable, Iterator

logger = logging.getLogger(__name__)


def chunked[T](iterable: Iterable[T], size: int) -> Iterator[list[T]]:
    """按固定大小将任意可迭代对象切分为若干连续子块。

    Args:
        iterable: 待切分的可迭代对象。
        size: 每个子块最多包含的元素个数。

    Yields:
        逐个产出子块，最后一个子块可能少于 size 个元素。

    Raises:
        ValueError: 当 size 小于等于 0 时。
    """
    if size <= 0:
        raise ValueError("size must be greater than 0")
    chunk = []
    for item in iterable:
        chunk.append(item)

        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def chunk_list[T](items: list[T], size: int) -> list[list[T]]:
    """按固定大小将 list 切分为若干连续子块。

    行为与 chunked 一致，但直接消费 list 并一次性返回全部子块。

    Args:
        items: 待切分的列表。
        size: 每个子块最多包含的元素个数。

    Returns:
        子块列表，最后一个子块可能少于 size 个元素。

    Raises:
        ValueError: 当 size 小于等于 0 时。
    """
    return list(chunked(items, size))


def split_list[T](items: list[T], n: int) -> list[list[T]]:
    """按固定份数将 list 切分为 n 个子块，余数靠前分配。

    不能整除时，靠前的子块各多一个元素；n 大于元素数时，多出的份以空块
    补齐。例如 list(range(1, 9)) 按 3 份切分为 [1,2,3]、[4,5,6]、[7,8]。

    Args:
        items: 待切分的列表。
        n: 目标份数。

    Returns:
        恰好 n 个子块组成的列表（元素不足时含空块）。

    Raises:
        ValueError: 当 n 小于等于 0 时。
    """
    if n <= 0:
        raise ValueError("n must be greater than 0")
    if not items:
        return []
    base, remainder = divmod(len(items), n)
    result = []
    start = 0
    for index in range(n):
        size = base + (1 if index < remainder else 0)
        result.append(items[start : start + size])
        start += size
    return result


def chunk_range(rng: range, size: int) -> list[range]:
    """按固定大小将 range 切分为若干连续子 range。

    基于索引切片实现，不展开元素，支持任意步长（含负数）；返回的子 range
    保持与源 range 相同的步长。例如 range(10) 按 3 切分为 range(0, 3)、
    range(3, 6)、range(6, 9)、range(9, 10)。

    Args:
        rng: 待切分的 range 对象。
        size: 每个子块最多包含的元素个数。

    Returns:
        子 range 列表，最后一个子块可能少于 size 个元素。

    Raises:
        ValueError: 当 size 小于等于 0 时。
    """
    if size <= 0:
        raise ValueError("size must be greater than 0")
    return [rng[start : start + size] for start in range(0, len(rng), size)]


def split_range(rng: range, n: int) -> list[range]:
    """按固定份数将 range 切分为 n 个子 range，余数靠前分配。

    不能整除时，靠前的子 range 各多一个元素；n 大于元素数时，多出的份以
    空 range 补齐。例如 range(8) 按 3 份切分为 range(0, 3)、range(3, 6)、
    range(6, 8)。

    Args:
        rng: 待切分的 range 对象。
        n: 目标份数。

    Returns:
        恰好 n 个子 range 组成的列表（元素不足时含空 range）。

    Raises:
        ValueError: 当 n 小于等于 0 时。
    """
    if n <= 0:
        raise ValueError("n must be greater than 0")
    if not rng:
        return []
    base, remainder = divmod(len(rng), n)
    result = []
    start = 0
    for index in range(n):
        size = base + (1 if index < remainder else 0)
        result.append(rng[start : start + size])
        start += size
    return result
