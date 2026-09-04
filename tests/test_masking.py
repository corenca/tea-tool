"""tea_tool.masking 脱敏机制与预置规则的单元测试。"""

import re
from collections import namedtuple

import pytest
from pydantic import ValidationError

from tea_tool.masking import (
    HashStrategy,
    KeepStrategy,
    Masker,
    MaskMatch,
    MaskRule,
    MaskStrategy,
    RemoveStrategy,
    ReplaceStrategy,
)
from tea_tool.masking.presets import (
    BANK_CARD_RULE,
    CN_PII_RULES,
    EMAIL_RULE,
    ID_CARD_RULE,
    IP_RULE,
    PHONE_RULE,
)

# 各测试共用的典型策略：手机号保留 3+4。
PHONE_MASK = KeepStrategy(prefix=3, suffix=4)

# 具名元组：tuple 子类但构造器不接受序列重建（见 namedtuple 保留测试）。
Row = namedtuple("Row", "phone")

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


# ----------------------------------------------------------------------
# 规则层：MaskRule.find
# ----------------------------------------------------------------------


def test_mask_rule_find_hits() -> None:
    """规则在文本中找出全部命中，携带区间、原文与所属规则的处理信息。"""
    matches = PHONE_RULE.find("手机 13812345678 与 13912345678")
    assert [m.value for m in matches] == ["13812345678", "13912345678"]
    assert matches[0].start == 3
    assert matches[0].end == 3 + 11
    assert matches[0].strategy is PHONE_RULE.strategy
    assert matches[0].priority == PHONE_RULE.priority


def test_mask_rule_find_no_hit() -> None:
    """无命中时返回空列表。"""
    assert PHONE_RULE.find("这里没有手机号") == []


def test_mask_rule_find_accepts_compiled_pattern() -> None:
    """pattern 接受预编译的 re.Pattern。"""
    rule = MaskRule(pattern=re.compile(r"\d+"), strategy=KeepStrategy())
    assert [m.value for m in rule.find("ab12cd34")] == ["12", "34"]


def test_mask_rule_find_ignores_zero_width() -> None:
    """可零宽匹配的正则：零宽命中不构成可替换片段，find 时忽略。"""
    rule = MaskRule(pattern=r"\d*", strategy=KeepStrategy())
    assert [m.value for m in rule.find("ab12cd")] == ["12"]


def test_mask_match_length() -> None:
    """命中长度等于区间长度。"""
    match = MaskMatch(
        strategy=KeepStrategy(),
        priority=1,
        start=3,
        end=14,
        value="13812345678",
    )
    assert match.length == 11


def test_mask_rule_is_immutable() -> None:
    """规则模型为 frozen 配置，字段不可修改。"""
    with pytest.raises(ValidationError):
        PHONE_RULE.priority = 999


def test_mask_rule_empty_pattern_raises() -> None:
    """空正则构造时拒绝，避免零宽命中污染脱敏结果。"""
    with pytest.raises(ValidationError, match="pattern"):
        MaskRule(pattern="", strategy=KeepStrategy())


def test_mask_rule_unknown_field_raises() -> None:
    """拼错字段名时显式报错，配置不静默丢失。"""
    with pytest.raises(ValidationError):
        MaskRule(pattern=r"\d+", strategy=KeepStrategy(), priotiy=1)


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


def test_mask_rule_with_strategy_returns_new_rule() -> None:
    """with_strategy 派生新规则：仅换策略，pattern 与优先级不变。"""
    derived = PHONE_RULE.with_strategy(PHONE_MASK)
    assert isinstance(derived, MaskRule)
    assert derived is not PHONE_RULE
    assert derived.pattern == PHONE_RULE.pattern
    assert derived.priority == PHONE_RULE.priority
    assert derived.strategy is PHONE_MASK


def test_mask_rule_with_strategy_keeps_original_unchanged() -> None:
    """派生不改写原规则：原规则仍是全星策略且可正常使用。"""
    PHONE_RULE.with_strategy(PHONE_MASK)
    assert PHONE_RULE.strategy is not PHONE_MASK
    masker = Masker(rules=[PHONE_RULE])
    assert masker.mask_text("联系 13812345678") == ("联系 " + _stars("13812345678"))


def test_mask_rule_with_strategy_overrides_priority() -> None:
    """显式传入 priority 时派生规则使用新优先级，原规则优先级不变。"""
    derived = ID_CARD_RULE.with_strategy(PHONE_MASK, priority=210)
    assert derived.strategy is PHONE_MASK
    assert derived.priority == 210
    assert derived.pattern == ID_CARD_RULE.pattern
    assert ID_CARD_RULE.priority == 200


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


# ----------------------------------------------------------------------
# 预置规则集
# ----------------------------------------------------------------------


def test_presets_composition() -> None:
    """CN_PII_RULES 包含五条规则，均为识别+全星策略。"""
    assert CN_PII_RULES == [
        ID_CARD_RULE,
        BANK_CARD_RULE,
        PHONE_RULE,
        EMAIL_RULE,
        IP_RULE,
    ]
    for rule in CN_PII_RULES:
        assert isinstance(rule, MaskRule)
        assert isinstance(rule.pattern, str)
        assert isinstance(rule.strategy, KeepStrategy)
        assert rule.strategy.prefix == 0 and rule.strategy.suffix == 0


def test_preset_priorities_ordering() -> None:
    """预置规则优先级与组合顺序一致（身份证 > 银行卡 > 手机 > 邮箱 > IP）。"""
    priorities = [rule.priority for rule in CN_PII_RULES]
    assert priorities == sorted(priorities, reverse=True)
