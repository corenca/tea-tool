"""Luhn 校验算法（ISO/IEC 7812 银行卡号校验位算法）。

纯算法实现，与脱敏、卡组织无关：对任意长度不少于 2 位的纯数字串判断
校验位是否成立，供银行卡号等场景识别时过滤伪号。注意 Luhn 只能排除
偶然错误，不能验证号码真实存在或属于某发卡行。
"""


def is_luhn_valid(number: str) -> bool:
    """判断数字串是否通过 Luhn 校验。

    从右起偶数位（从 1 数）的数字翻倍，超过 9 则减 9，累加全部数字后
    校验和为 10 的倍数即为通过。非纯数字输入（含空格、连字符等常见
    卡号书写分隔）一律拒绝，须由调用方预先清洗。

    Args:
        number: 待校验的纯数字串。

    Returns:
        number 通过 Luhn 校验时返回 True；含非数字字符或长度不足 2 位
        时返回 False。
    """
    if not number.isdigit() or len(number) < 2:
        return False

    total = 0
    for index, char in enumerate(reversed(number)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0
