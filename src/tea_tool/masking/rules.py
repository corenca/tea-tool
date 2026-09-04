"""文本发现层：规则在自由文本中定位敏感片段。

MaskRule 将"识别（正则）"与"处理（策略）"绑定为一条完整规则：发现敏感
片段的同时决定其脱敏方式。MaskMatch 是规则的一次命中结果，平铺携带处理
所需信息（策略与优先级），供编排层做重叠消解后替换。两者为单向依赖
（MaskRule → MaskMatch），因此本模块无需延迟注解求值。

模型直接继承 pydantic.BaseModel（不经过 tea_tool.schema.BaseModel）：规则
值对象需要的是"不可变 + 拒绝未声明字段"而非 ORM 数据模型的宽松配置——
规则字段拼错应显式报错，避免脱敏静默失效。
"""

import re
from re import Pattern

from pydantic import BaseModel, ConfigDict, field_validator

from .strategies import MaskStrategy


class _MaskModel(BaseModel):
    """masking 包内模型的公共配置：不可变、拒绝未声明字段、允许非 pydantic 字段。"""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )


class MaskMatch(_MaskModel):
    """规则在文本中的一次命中结果。

    Attributes:
        strategy: 命中所属规则的脱敏策略。
        priority: 命中所属规则的优先级，供重叠消解排序。
        start: 命中区间起点（含）。
        end: 命中区间终点（不含）。
        value: 命中的原始文本。
    """

    strategy: MaskStrategy
    priority: int
    start: int
    end: int
    value: str

    @property
    def length(self) -> int:
        """命中区间长度（end - start）。"""
        return self.end - self.start


class MaskRule(_MaskModel):
    """文本脱敏规则：正则定位 + 策略处理。

    Attributes:
        pattern: 定位敏感片段的匹配模式，可为正则字符串或预编译 Pattern。
        strategy: 命中片段采用的脱敏策略。
        priority: 与其他规则区间重叠时的优先级，数值大者优先，默认 0。
    """

    pattern: str | Pattern[str]
    strategy: MaskStrategy
    priority: int = 0

    @field_validator("pattern")
    @classmethod
    def _pattern_not_empty(
        cls,
        pattern: str | Pattern[str],
    ) -> str | Pattern[str]:
        """拒绝空正则：其只能零宽命中（会被 find 忽略），属配置错误，构造期尽早暴露。

        Args:
            pattern: 构造传入的匹配模式。

        Returns:
            原样返回非空模式。

        Raises:
            ValueError: pattern 为空字符串。
        """
        if isinstance(pattern, str) and not pattern:
            raise ValueError("pattern 不能为空字符串")
        return pattern

    def find(self, text: str) -> list[MaskMatch]:
        """在文本中查找本规则的全部命中。

        零宽命中（start == end，如可空匹配的正则产生）不构成可替换片段，
        一律忽略。

        Args:
            text: 待扫描文本。

        Returns:
            按出现顺序排列的非零宽命中列表；无命中时为空列表。
        """
        return [
            MaskMatch(
                strategy=self.strategy,
                priority=self.priority,
                start=m.start(),
                end=m.end(),
                value=m.group(),
            )
            for m in re.compile(self.pattern).finditer(text)
            if m.end() > m.start()
        ]

    def with_strategy(
        self,
        strategy: MaskStrategy,
        *,
        priority: int | None = None,
    ) -> "MaskRule":
        # 返回注解字符串化：类体执行期类名尚未绑定（未启用注解延迟求值）
        """派生新规则：替换脱敏策略，可一并显式指定新优先级。

        原规则不可变且不受影响，已注入 Masker 的规则不会被派生改写；
        派生结果通常用于替换原规则（如定制预置规则为保留位格式）。
        需要让派生规则与原规则共存并胜出时，显式传入更高的 priority，
        如 ID_CARD_RULE.with_strategy(mask, priority=210)。

        Args:
            strategy: 新规则的脱敏策略。
            priority: 新规则的优先级；None（默认）时沿用原规则的值。

        Returns:
            携带新策略、其余字段与原规则一致的新规则实例。
        """
        update: dict[str, object] = {"strategy": strategy}
        if priority is not None:
            update["priority"] = priority
        return self.model_copy(update=update)
