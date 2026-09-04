"""tea_tool.masking.strategies 脱敏策略的单元测试。"""

import pytest

from tea_tool.masking import HashStrategy, KeepStrategy, RemoveStrategy, ReplaceStrategy

# 各测试共用的典型策略：手机号保留 3+4。
PHONE_MASK = KeepStrategy(prefix=3, suffix=4)

MASK_CHAR = "*"


def _stars(text: str) -> str:
    """生成与 text 等长的掩码串。"""
    return MASK_CHAR * len(text)


# ----------------------------------------------------------------------
# 策略层：KeepStrategy
# ----------------------------------------------------------------------


def test_keep_strategy_default_masks_whole_value() -> None:
    """无参构造时整段掩码（不保留首尾）。"""
    assert KeepStrategy().mask("13812345678") == _stars("13812345678")


def test_keep_strategy_keeps_prefix_and_suffix() -> None:
    """保留首尾指定字符数，中间掩码。"""
    assert PHONE_MASK.mask("13812345678") == "138****5678"


def test_keep_strategy_keeps_prefix_only() -> None:
    """suffix 为 0 时只保留前缀，末尾不残留。"""
    assert KeepStrategy(prefix=3).mask("13812345678") == "138" + _stars("12345678")


def test_keep_strategy_suffix_over_length_masks_all() -> None:
    """保留位覆盖全长时退化为整体掩码，不产生保留区重叠。"""
    assert KeepStrategy(prefix=6, suffix=6).mask("12345") == _stars("12345")


def test_keep_strategy_custom_mask_char() -> None:
    """支持自定义掩码字符。"""
    assert KeepStrategy(mask_char="#").mask("abc") == "###"


def test_keep_strategy_empty_value_unchanged() -> None:
    """空字符串原样返回。"""
    assert KeepStrategy().mask("") == ""
    assert KeepStrategy(prefix=1, suffix=1).mask("") == ""


@pytest.mark.parametrize("prefix", [-1, -10])
def test_keep_strategy_negative_prefix_raises(prefix: int) -> None:
    """负数 prefix 构造时抛 ValueError。"""
    with pytest.raises(ValueError, match="非负"):
        KeepStrategy(prefix=prefix)


def test_keep_strategy_negative_suffix_raises() -> None:
    """负数 suffix 构造时抛 ValueError。"""
    with pytest.raises(ValueError, match="非负"):
        KeepStrategy(suffix=-1)


def test_keep_strategy_empty_mask_char_raises() -> None:
    """空掩码字符构造时抛 ValueError。"""
    with pytest.raises(ValueError, match="mask_char"):
        KeepStrategy(mask_char="")


# ----------------------------------------------------------------------
# 策略层：ReplaceStrategy / HashStrategy / RemoveStrategy
# ----------------------------------------------------------------------


def test_replace_strategy_replaces_with_fixed_string() -> None:
    """整体替换为构造时给定的固定字符串。"""
    assert ReplaceStrategy("***").mask("13812345678") == "***"


def test_replace_strategy_empty_replacement_raises() -> None:
    """空替换串构造时抛 ValueError（整体删除应使用 RemoveStrategy）。"""
    with pytest.raises(ValueError, match="replacement"):
        ReplaceStrategy("")


def test_hash_strategy_output_format() -> None:
    """输出为 algorithm:hexdigest 形式，且结果确定可复现。"""
    strategy = HashStrategy()
    first = strategy.mask("13812345678")
    assert first == strategy.mask("13812345678")
    assert first.startswith("sha256:")
    assert len(first) == len("sha256:") + 64


def test_hash_strategy_known_digest() -> None:
    """无盐 sha256 对已知输入输出固定摘要。"""
    assert HashStrategy().mask("abc") == (
        "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_hash_strategy_salt_changes_digest() -> None:
    """不同盐产生不同摘要，同盐结果确定。"""
    strategy = HashStrategy(salt="pepper")
    assert strategy.mask("13812345678") != HashStrategy().mask("13812345678")
    assert strategy.mask("13812345678") == strategy.mask("13812345678")


def test_hash_strategy_unknown_algorithm_raises() -> None:
    """构造时校验算法名，不支持时抛 ValueError。"""
    with pytest.raises(ValueError, match="算法"):
        HashStrategy(algorithm="not-a-real-algo")


def test_hash_strategy_empty_algorithm_raises() -> None:
    """空算法名构造时抛 ValueError。"""
    with pytest.raises(ValueError, match="algorithm"):
        HashStrategy(algorithm="")


def test_remove_strategy_deletes_value() -> None:
    """整体删除：恒返回空字符串。"""
    assert RemoveStrategy().mask("13812345678") == ""
