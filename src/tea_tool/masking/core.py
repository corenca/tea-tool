"""脱敏编排层：Masker 门面，提供单值、文本、结构化三种脱敏入口。

Masker 只持有使用方注入的规则列表，不含内置规则与类型注册表——何种文本
是敏感信息、各类数据脱成什么样，均由使用方显式定义：可选用
tea_tool.masking.presets 的预置规则，或在业务侧建立脱敏配置常量后复用
同一实例（如项目配置文件中的模块级 Masker）。
"""

from collections.abc import Mapping
from typing import Any

from .rules import MaskMatch, MaskRule
from .strategies import MaskStrategy


def _is_namedtuple(value: Any) -> bool:
    """判断是否为具名元组（其构造器不接受序列重建）。

    Args:
        value: 待判断对象。

    Returns:
        value 为具名元组（含 _fields 的 tuple 子类）时返回 True。
    """
    return isinstance(value, tuple) and hasattr(type(value), "_fields")


class Masker:
    """通用脱敏编排器。

    用法示例（文本自动识别，规则来自预置集）::

        from tea_tool.masking.presets import CN_PII_RULES

        masker = Masker(rules=CN_PII_RULES)
        masker.mask_text("联系 13812345678")  # 联系 ***********

    规则列表为空时 mask_text 不做自动识别；mask 与 mask_dict 不依赖规则，
    按调用处显式传入的策略工作。
    """

    def __init__(self, *, rules: list[MaskRule] | None = None) -> None:
        """构造脱敏器。

        Args:
            rules: 初始文本识别规则；未传时为空列表（可稍后经
                register_rule 追加）。
        """
        self._rules: list[MaskRule] = list(rules or [])

    # ------------------------------------------------------------------
    # 注册
    # ------------------------------------------------------------------

    def register_rule(self, rule: MaskRule) -> None:
        """追加一条文本识别规则。

        Args:
            rule: 待追加的规则。
        """
        self._rules.append(rule)

    # ------------------------------------------------------------------
    # 单值
    # ------------------------------------------------------------------

    def mask(self, value: Any, strategy: MaskStrategy) -> str | None:
        """对单个值按指定策略脱敏。

        None 原样返回（"无数据"无需脱敏）；非字符串值先转字符串再脱敏，
        因此输出恒为字符串形态（int/float 等原始类型不保留）。

        Args:
            value: 待脱敏值，可为任意类型。
            strategy: 采用的脱敏策略。

        Returns:
            脱敏后的字符串；value 为 None 时返回 None。
        """
        if value is None:
            return None

        return strategy.mask(value if isinstance(value, str) else str(value))

    # ------------------------------------------------------------------
    # 文本
    # ------------------------------------------------------------------

    def mask_text(
        self,
        text: str,
        *,
        rules: list[MaskRule] | None = None,
    ) -> str:
        """对自由文本做自动识别脱敏。

        文本被全部规则扫描，命中区间先按优先级消解重叠，再按起始位置
        单趟线性拼接、原位替换为所属规则的策略输出——命中互不重叠，
        策略输出变长或删除时不影响其他命中的替换。

        Args:
            text: 待脱敏文本。
            rules: 本次调用使用的规则列表；未传时使用构造时注入的规则
                （可传空列表临时禁用识别）。

        Returns:
            脱敏后的文本；text 为空时原样返回。
        """
        if not text:
            return text

        active_rules = self._rules if rules is None else rules

        matches: list[MaskMatch] = []
        for rule in active_rules:
            matches.extend(rule.find(text))

        resolved = self._resolve_overlaps(matches)
        if not resolved:
            return text

        # 命中互不重叠且按起始位置升序：一次遍历拼接新文本，避免逐命中
        # 重建文本的平方级开销（替换串长度变化不影响其他区间）
        parts: list[str] = []
        pos = 0
        for match in resolved:
            parts.append(text[pos : match.start])
            parts.append(match.strategy.mask(match.value))
            pos = match.end
        parts.append(text[pos:])
        return "".join(parts)

    # ------------------------------------------------------------------
    # 结构化数据
    # ------------------------------------------------------------------

    def mask_dict(
        self,
        data: Mapping[str, Any],
        fields: Mapping[str, MaskStrategy],
        *,
        recursive: bool = True,
    ) -> dict[str, Any]:
        """对 dict 按字段映射脱敏，未声明字段原样保留。

        fields 为字段名到脱敏策略的映射，例如::

            masker.mask_dict(
                {"phone": "13812345678", "remark": "无"},
                fields={"phone": KeepStrategy(prefix=3, suffix=4)},
            )

        同一份字段映射会应用到嵌套层级：recursive 为 True 时，嵌套 dict
        与 list/tuple 会被递归处理，嵌套 dict 中同名命中的字段同样脱敏；
        嵌套容器内未命中的字段原样保留。

        Args:
            data: 待脱敏的 dict，仅处理顶层字符串键。
            fields: 字段名到脱敏策略的映射。
            recursive: 是否递归处理嵌套 dict 与 list/tuple，默认 True。

        Returns:
            脱敏后的新 dict；原始 data 不被修改。
        """
        result: dict[str, Any] = {}

        for key, value in data.items():
            if key in fields:
                result[key] = self.mask(value, fields[key])
            elif recursive and isinstance(value, Mapping):
                result[key] = self.mask_dict(value, fields=fields)
            elif recursive and isinstance(value, (list, tuple)):
                if _is_namedtuple(value):
                    # 具名元组按字段结构存在，序列重建会破坏其形状，原样保留
                    result[key] = value
                else:
                    result[key] = self._mask_collection(value, fields=fields)
            else:
                result[key] = value

        return result

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _mask_collection(
        self,
        value: list[Any] | tuple[Any, ...],
        fields: Mapping[str, MaskStrategy],
    ) -> list[Any] | tuple[Any, ...]:
        """递归脱敏集合元素：dict 元素按字段映射，嵌套集合继续深入。

        Args:
            value: 待脱敏的列表或元组。
            fields: 字段名到脱敏策略的映射（与 mask_dict 相同）。

        Returns:
            与原容器同类型的新容器，元素已按字段映射脱敏。
        """
        result: list[Any] = []

        for item in value:
            if isinstance(item, Mapping):
                result.append(self.mask_dict(item, fields=fields))
            elif isinstance(item, (list, tuple)) and not _is_namedtuple(item):
                result.append(self._mask_collection(item, fields=fields))
            else:
                result.append(item)

        return type(value)(result)

    @staticmethod
    def _resolve_overlaps(matches: list[MaskMatch]) -> list[MaskMatch]:
        """消除多规则命中的区间重叠。

        排序键依次为优先级高、起始靠前、区间长，再依序贪心选取不与已选
        命中重叠的区间——重叠时保留排序靠前者，保证身份证等长区间规则
        不被银行卡等子串规则拆分。

        候选起点不小于已选命中最大右端点时，与全部已选必然不重叠（其
        右端点均不超过该最大值），可直接接受：避免大文本大量命中时
        逐个比较的平方级开销。

        Args:
            matches: 全部规则产生的命中列表。

        Returns:
            互不重叠的命中列表，按起始位置升序排列。
        """
        ordered = sorted(
            matches,
            key=lambda item: (-item.priority, item.start, -item.length),
        )

        selected: list[MaskMatch] = []
        max_end = -1
        for match in ordered:
            if match.start >= max_end or not any(
                match.start < current.end and match.end > current.start
                for current in selected
            ):
                selected.append(match)
                max_end = max(max_end, match.end)

        return sorted(selected, key=lambda item: item.start)
