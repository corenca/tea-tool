"""识别器层：定义"如何在文本中发现候选片段"的机制。

Matcher 是识别器接口：find() 负责定位候选区间（TextMatch），accepts()
负责确认候选是否真实命中——两阶段拆分使"正则粗筛 + 真实验证"成为接口
显式语义，Luhn 校验、身份证校验位等防误报逻辑以覆写 accepts 的方式接入，
而非在规则层旁挂回调。RegexMatcher 是正则实现，作为默认子类使用。

本层不接触脱敏策略（strategies）与规则绑定（rules）：TextMatch 只携带
区间信息，不含策略与优先级；由 MaskRule 组装为命中结果（MaskMatch）。
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from re import Pattern
from typing import Self


@dataclass(frozen=True)
class TextMatch:
    """识别器产出的候选命中区间。

    Attributes:
        start: 候选区间起点（含）。
        end: 候选区间终点（不含）。
        value: 命中的原始文本。
    """

    start: int
    end: int
    value: str


class Matcher(ABC):
    """识别器接口：在自由文本中定位候选区间。

    契约：find 只产出非零宽区间（start < end）——零宽命中不构成可替换
    片段；文本扫描无关的处理信息（策略、优先级）不属于本层。
    """

    @abstractmethod
    def find(self, text: str) -> list[TextMatch]:
        """在文本中定位全部候选区间。

        Args:
            text: 待扫描文本。

        Returns:
            按出现顺序排列的候选列表；无候选时为空列表。
        """
        raise NotImplementedError

    def accepts(self, match: TextMatch) -> bool:
        """确认单个候选是否真实命中。

        基类默认接受全部候选；子类可覆写以执行 Luhn 等真实性校验，
        过滤正则定位到的伪候选。

        Args:
            match: 待确认的候选。

        Returns:
            True 表示接受该候选，False 表示丢弃。
        """
        return True


class RegexMatcher(Matcher):
    """正则识别器：以正则表达式定位候选区间。

    构造时接受正则字符串或预编译 Pattern（字符串立即编译）；构造后
    不可变，可安全共享复用。
    """

    def __init__(self, pattern: str | Pattern[str]) -> None:
        """构造正则识别器。

        Args:
            pattern: 定位候选的匹配模式，可为正则字符串或预编译 Pattern。

        Raises:
            ValueError: pattern 为空字符串（其只能零宽命中，无定位能力）。
        """
        if isinstance(pattern, str) and not pattern:
            raise ValueError("pattern 不能为空字符串")
        self._pattern = re.compile(pattern)

    @classmethod
    def of(cls, pattern: str | Pattern[str]) -> Self:
        """从正则字符串或预编译 Pattern 构造识别器。

        Args:
            pattern: 定位候选的匹配模式。

        Returns:
            新构造的识别器实例。
        """
        return cls(pattern)

    def find(self, text: str) -> list[TextMatch]:
        """以正则定位全部候选区间。

        零宽命中（start == end，如可空匹配的正则产生）不构成可替换
        片段，一律忽略。

        Args:
            text: 待扫描文本。

        Returns:
            按出现顺序排列的候选列表；无候选时为空列表。
        """
        return [
            TextMatch(start=m.start(), end=m.end(), value=m.group())
            for m in self._pattern.finditer(text)
            if m.end() > m.start()
        ]
