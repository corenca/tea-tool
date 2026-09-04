"""脱敏策略层：定义"如何脱敏"的算法。

策略对象为不可变、参数在构造时绑定的规范：一个策略实例即完整的脱敏方式
声明，可安全共享复用。本层不内置任何业务默认格式——保留位、替换串等参数
均由使用方在构造时显式给出。
"""

import hashlib
from abc import ABC, abstractmethod


class MaskStrategy(ABC):
    """脱敏策略基类：对单个字符串输出脱敏结果。"""

    @abstractmethod
    def mask(self, value: str) -> str:
        """对单个值执行脱敏。

        Args:
            value: 待脱敏字符串。

        Returns:
            脱敏后的字符串。
        """
        raise NotImplementedError


class KeepStrategy(MaskStrategy):
    """保留首尾指定字符、中间以掩码字符替换的脱敏策略。

    例：KeepStrategy(prefix=3, suffix=4).mask("13812345678") == "138****5678"。
    """

    prefix: int
    suffix: int
    mask_char: str

    def __init__(
        self,
        prefix: int = 0,
        suffix: int = 0,
        mask_char: str = "*",
    ) -> None:
        """构造保留型策略。

        Args:
            prefix: 开头保留的字符数，默认 0（不保留）。
            suffix: 结尾保留的字符数，默认 0（不保留）。
            mask_char: 掩码字符，默认 "*"。

        Raises:
            ValueError: prefix/suffix 为负数，或 mask_char 为空字符串。
        """
        if prefix < 0 or suffix < 0:
            raise ValueError("prefix 与 suffix 必须为非负整数")
        if not mask_char:
            raise ValueError("mask_char 不能为空字符串")

        self.prefix = prefix
        self.suffix = suffix
        self.mask_char = mask_char

    def mask(self, value: str) -> str:
        """对单个值执行保留首尾的掩码替换。

        Args:
            value: 待脱敏字符串。

        Returns:
            掩码后的字符串；value 为空时原样返回。
        """
        if not value:
            return value

        length = len(value)

        if self.prefix + self.suffix >= length:
            # 保留位覆盖全长时退化为整体掩码，避免保留区重叠
            return self.mask_char * length

        middle = self.mask_char * (length - self.prefix - self.suffix)
        return value[: self.prefix] + middle + value[length - self.suffix :]


class ReplaceStrategy(MaskStrategy):
    """将整个值替换为固定字符串的脱敏策略。"""

    replacement: str

    def __init__(self, replacement: str) -> None:
        """构造整体替换策略。

        Args:
            replacement: 替换后的固定字符串。

        Raises:
            ValueError: replacement 为空字符串（整体删除请使用 RemoveStrategy）。
        """
        if not replacement:
            raise ValueError("replacement 不能为空字符串")

        self.replacement = replacement

    def mask(self, value: str) -> str:
        """对单个值执行整体替换（忽略原值）。

        Args:
            value: 待脱敏字符串。

        Returns:
            构造时给定的 replacement。
        """
        return self.replacement


class HashStrategy(MaskStrategy):
    """以哈希摘要替换原值的脱敏策略，输出形如 ``sha256:<digest>``。

    salt 用于抵御彩虹表与枚举攻击；注意其语义是加盐哈希而非密钥认证
    （HMAC），需要防篡改时应改用带密钥的方案。
    """

    algorithm: str
    salt: str

    def __init__(self, algorithm: str = "sha256", salt: str = "") -> None:
        """构造哈希策略。

        Args:
            algorithm: hashlib 支持的摘要算法名，默认 "sha256"。
            salt: 混入摘要的盐（utf-8 编码后前置拼接），默认空字符串。

        Raises:
            ValueError: algorithm 为空或不是 hashlib 支持的算法名。
        """
        if not algorithm:
            raise ValueError("algorithm 不能为空字符串")

        # 构造期即校验算法可用（fail fast），避免脱敏时才暴露配置错误
        try:
            hashlib.new(algorithm, b"")
        except ValueError as exc:
            raise ValueError(f"不支持的哈希算法: {algorithm}") from exc

        self.algorithm = algorithm
        self.salt = salt

    def mask(self, value: str) -> str:
        """对单个值执行加盐哈希替换。

        Args:
            value: 待脱敏字符串。

        Returns:
            "{algorithm}:{hexdigest}" 形式的摘要串。
        """
        raw = self.salt.encode("utf-8") + value.encode("utf-8")
        digest = hashlib.new(self.algorithm, raw).hexdigest()
        return f"{self.algorithm}:{digest}"


class RemoveStrategy(MaskStrategy):
    """将值整体删除（替换为空字符串）的脱敏策略。"""

    def mask(self, value: str) -> str:
        """对单个值执行整体删除。

        Args:
            value: 待脱敏字符串。

        Returns:
            恒为空字符串。
        """
        return ""
