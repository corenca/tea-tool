"""tea_tool.util.luhn Luhn 校验算法的单元测试。"""

import pytest

from tea_tool.util.luhn import is_luhn_valid


@pytest.mark.parametrize(
    "number",
    [
        # 各卡组织公开的测试卡号。
        "4111111111111111",  # Visa
        "4012888888881881",  # Visa（第二测试号）
        "5555555555554444",  # Mastercard
        "378282246310005",  # American Express（15 位）
    ],
)
def test_is_luhn_valid_accepts_known_test_cards(number: str) -> None:
    """公开测试卡号通过校验。"""
    assert is_luhn_valid(number) is True


@pytest.mark.parametrize(
    "number",
    [
        "4111111111111112",  # 上一用例改末位，校验和破坏
        "6222020200112233",  # 16 位但与卡组织真实号无关的伪号
        "8111111111111111",
        "12",  # 长度 2 的合法输入同样按算法判断（结果为假）
    ],
)
def test_is_luhn_valid_rejects_invalid_digits(number: str) -> None:
    """校验和不匹配的数字串被拒绝。"""
    assert is_luhn_valid(number) is False


@pytest.mark.parametrize(
    "number",
    [
        "",
        "1",
        "4111 1111 1111 1111",  # 含空格
        "411111111111111a",  # 含字母
        "-411111111111111",  # 含符号
    ],
)
def test_is_luhn_valid_rejects_non_digit_input(number: str) -> None:
    """非纯数字输入一律拒绝（含空串与不足两位）。"""
    assert is_luhn_valid(number) is False


def test_is_luhn_valid_algorithmic_not_business() -> None:
    """校验是纯模 10 算法：全零串数学上通过，不代表真实卡号。"""
    assert is_luhn_valid("0000000000000000") is True
