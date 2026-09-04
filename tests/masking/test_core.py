"""tea_tool.masking.core Masker 脱敏入口的单元测试。"""

from collections import namedtuple

import pytest

from tea_tool.masking import (
    KeepStrategy,
    Masker,
    MaskRule,
    MaskStrategy,
    RemoveStrategy,
    ReplaceStrategy,
)
from tea_tool.masking.presets import CN_PII_RULES, PHONE_RULE

# 各测试共用的典型策略：手机号保留 3+4。
PHONE_MASK = KeepStrategy(prefix=3, suffix=4)

# 具名元组：tuple 子类但构造器不接受序列重建（见 namedtuple 保留测试）。
Row = namedtuple("Row", "phone")

MASK_CHAR = "*"


def _stars(text: str) -> str:
    """生成与 text 等长的掩码串。"""
    return MASK_CHAR * len(text)


# ----------------------------------------------------------------------
# Masker.mask：单值脱敏
# ----------------------------------------------------------------------


def test_mask_single_value_with_strategy() -> None:
    """单值按传入策略脱敏。"""
    masker = Masker()
    assert masker.mask("13812345678", PHONE_MASK) == "138****5678"


def test_mask_none_returns_none() -> None:
    """None 原样返回，不进入脱敏。"""
    assert Masker().mask(None, PHONE_MASK) is None


def test_mask_non_string_converted() -> None:
    """非字符串值先转字符串再脱敏。"""
    assert Masker().mask(13812345678, PHONE_MASK) == "138****5678"


# ----------------------------------------------------------------------
# Masker.mask_text：文本自动识别
# ----------------------------------------------------------------------


@pytest.fixture()
def cn_masker() -> Masker:
    """注入 CN_PII_RULES 的脱敏器。"""
    return Masker(rules=CN_PII_RULES)


def test_mask_text_masks_phone(cn_masker: Masker) -> None:
    """预置手机号规则命中并整段掩码。"""
    assert cn_masker.mask_text("联系 13812345678 即可") == (
        "联系 " + _stars("13812345678") + " 即可"
    )


def test_mask_text_masks_email(cn_masker: Masker) -> None:
    """预置邮箱规则命中并整段掩码。"""
    assert cn_masker.mask_text("邮箱 a@b.cn 收件") == (
        "邮箱 " + _stars("a@b.cn") + " 收件"
    )


def test_mask_text_masks_bank_card(cn_masker: Masker) -> None:
    """16 位纯数字被银行卡规则整段掩码。"""
    card = "6222020200112233"
    assert cn_masker.mask_text("卡号 " + card) == "卡号 " + _stars(card)


def test_mask_text_masks_ip(cn_masker: Masker) -> None:
    """预置 IPv4 规则命中并整段掩码。"""
    assert cn_masker.mask_text("地址 192.168.1.10 在线") == (
        "地址 " + _stars("192.168.1.10") + " 在线"
    )


def test_mask_text_id_card_wins_over_bank_card(cn_masker: Masker) -> None:
    """纯数字 18 位身份证同时命中银行规则，优先级使身份证整段掩码。"""
    id_card = "110105194912310021"
    assert cn_masker.mask_text("证件 " + id_card) == "证件 " + _stars(id_card)


def test_mask_text_id_card_with_x_fully_masked(cn_masker: Masker) -> None:
    """末位 X 的身份证：银行卡仅命中前 17 位子串，被重叠消解剔除。"""
    id_card = "11010519491231002X"
    assert cn_masker.mask_text("证件 " + id_card) == "证件 " + _stars(id_card)


def test_mask_text_id_card_swallows_inner_phone(cn_masker: Masker) -> None:
    """身份证内嵌手机号形态子串时，整个身份证按高优先级整段掩码。"""
    id_card = "11010513123456789X"
    assert cn_masker.mask_text("证件 " + id_card) == "证件 " + _stars(id_card)


def test_mask_text_multiple_hits_same_text(cn_masker: Masker) -> None:
    """同一文本多处命中时各自替换、互不错位。"""
    assert cn_masker.mask_text("13812345678 与 13912345678") == (
        _stars("13812345678") + " 与 " + _stars("13912345678")
    )


def test_mask_text_shrinking_replacement_keeps_positions() -> None:
    """替换串短于原文（Remove）时，其余命中位置不受位移影响。"""
    phone_rule = MaskRule(
        pattern=r"1[3-9]\d{9}",
        strategy=RemoveStrategy(),
        priority=100,
    )
    masker = Masker(rules=[phone_rule])
    assert masker.mask_text("号码 13812345678 已删，号码 13912345678 也删") == (
        "号码  已删，号码  也删"
    )


def test_mask_text_growing_replacement_keeps_positions() -> None:
    """替换串长于原文（Replace 定长串）时，其余命中位置不受位移影响。"""
    phone_rule = MaskRule(
        pattern=r"1[3-9]\d{9}",
        strategy=ReplaceStrategy("[号码]"),
        priority=100,
    )
    masker = Masker(rules=[phone_rule])
    assert masker.mask_text("号码 13812345678 与 13912345678") == (
        "号码 [号码] 与 [号码]"
    )


def test_mask_text_many_non_overlapping_hits(cn_masker: Masker) -> None:
    """大量互不重叠命中逐一脱敏（覆盖重叠消解粗筛路径）。"""
    text = "13812345678 " * 200
    assert cn_masker.mask_text(text) == (_stars("13812345678") + " ") * 200


def test_mask_text_phone_not_matched_when_embedded_in_digits(
    cn_masker: Masker,
) -> None:
    """前后仍是数字时不构成独立手机号，不命中。"""
    assert cn_masker.mask_text("号码段 213812345678") == "号码段 213812345678"


def test_mask_text_empty_text(cn_masker: Masker) -> None:
    """空文本原样返回。"""
    assert cn_masker.mask_text("") == ""


def test_mask_text_without_rules_returns_unchanged() -> None:
    """未注入规则时文本原样返回。"""
    assert Masker().mask_text("联系 13812345678") == "联系 13812345678"


def test_mask_text_rules_argument_overrides(cn_masker: Masker) -> None:
    """调用处 rules 参数临时覆盖实例规则，空列表可禁用识别。"""
    assert cn_masker.mask_text("联系 13812345678", rules=[]) == "联系 13812345678"


def test_mask_text_custom_formatted_rule() -> None:
    """规则携带自定义保留位策略时按该格式输出。"""
    phone_rule = PHONE_RULE.with_strategy(PHONE_MASK)
    masker = Masker(rules=[phone_rule])
    assert masker.mask_text("联系 13812345678") == "联系 138****5678"


def test_mask_text_register_rule_applies_later() -> None:
    """register_rule 追加的规则在后续调用生效。"""
    masker = Masker()
    masker.register_rule(PHONE_RULE)
    assert masker.mask_text("联系 13812345678") == ("联系 " + _stars("13812345678"))


def test_mask_text_custom_strategy_applies() -> None:
    """自定义策略类注入规则后按自定义逻辑脱敏（扩展点）。"""

    class UpperStrategy(MaskStrategy):
        """测试用：以全大写替换原文。"""

        def mask(self, value: str) -> str:
            return value.upper()

    rule = MaskRule(pattern=r"[a-z]{3}", strategy=UpperStrategy())
    assert Masker(rules=[rule]).mask_text("编码 abc 结尾") == "编码 ABC 结尾"


# ----------------------------------------------------------------------
# Masker.mask_dict：结构化数据
# ----------------------------------------------------------------------


def test_mask_dict_declared_fields_only() -> None:
    """只有 fields 声明的字段被脱敏，其余原样保留。"""
    masker = Masker()
    data = {"phone": "13812345678", "name": "张三", "remark": "无"}
    result = masker.mask_dict(data, fields={"phone": PHONE_MASK})
    assert result == {"phone": "138****5678", "name": "张三", "remark": "无"}


def test_mask_dict_nested_dict_recursive() -> None:
    """嵌套 dict 递归应用同一字段映射，外层对象不被修改。"""
    masker = Masker()
    data = {"user": {"phone": "13812345678", "age": 30}}
    result = masker.mask_dict(data, fields={"phone": PHONE_MASK})
    assert result == {"user": {"phone": "138****5678", "age": 30}}
    assert data["user"]["phone"] == "13812345678"


def test_mask_dict_list_of_dicts() -> None:
    """list 中嵌套 dict 逐项递归脱敏。"""
    masker = Masker()
    data = {"items": [{"phone": "13812345678"}, {"phone": "13912345678"}]}
    result = masker.mask_dict(data, fields={"phone": PHONE_MASK})
    assert result == {
        "items": [{"phone": "138****5678"}, {"phone": "139****5678"}],
    }


def test_mask_dict_tuple_keeps_container_type() -> None:
    """元组容器脱敏后仍保持元组类型。"""
    masker = Masker()
    data = {"rows": ({"phone": "13812345678"}, {"phone": "13912345678"})}
    result = masker.mask_dict(data, fields={"phone": PHONE_MASK})
    assert isinstance(result["rows"], tuple)
    assert result["rows"][0]["phone"] == "138****5678"


def test_mask_dict_namedtuple_kept_unchanged() -> None:
    """具名元组不是可序列重建的普通容器，原样保留、不递归重建。"""
    masker = Masker()
    row = Row(phone="13812345678")
    result = masker.mask_dict({"rows": (row,)}, fields={"phone": PHONE_MASK})
    assert result["rows"] == (row,)
    assert result["rows"][0] is row


def test_mask_dict_deep_nesting() -> None:
    """深层 dict 套 list 再套 dict 时逐层递归。"""
    masker = Masker()
    data = {"outer": [{"inner": [{"phone": "13812345678"}]}]}
    result = masker.mask_dict(data, fields={"phone": PHONE_MASK})
    assert result["outer"][0]["inner"][0]["phone"] == "138****5678"


def test_mask_dict_recursive_false_keeps_nested() -> None:
    """recursive=False 时嵌套结构不深入，仅顶层命名字段脱敏。"""
    masker = Masker()
    data = {"phone": "13812345678", "user": {"phone": "13912345678"}}
    result = masker.mask_dict(
        data,
        fields={"phone": PHONE_MASK},
        recursive=False,
    )
    assert result == {"phone": "138****5678", "user": {"phone": "13912345678"}}


def test_mask_dict_none_value_kept() -> None:
    """字段值为 None 时原样保留。"""
    masker = Masker()
    assert masker.mask_dict(
        {"phone": None},
        fields={"phone": PHONE_MASK},
    ) == {"phone": None}
