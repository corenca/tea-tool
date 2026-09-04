"""tea_tool.util.enum 值枚举基类的单元测试。"""

import pytest

from tea_tool.util.enum import ValueMsgEnum


class OrderStatus(ValueMsgEnum):
    """测试用值枚举：订单状态。"""

    PENDING = ("pending", "待处理")
    PAID = ("paid", "已支付")
    DONE = ("done", "已完成")


def test_member_value_and_msg() -> None:
    """成员二元组的首元素为 .value、次元素为 .msg。"""
    assert OrderStatus.PENDING.value == "pending"
    assert OrderStatus.PENDING.msg == "待处理"
    assert OrderStatus.DONE.value == "done"
    assert OrderStatus.DONE.msg == "已完成"
    assert OrderStatus.DONE.name == "DONE"


def test_value_is_str() -> None:
    """.value 保持声明的 str 类型。"""
    assert isinstance(OrderStatus.PAID.value, str)


def test_annotation_msg_is_not_member() -> None:
    """类级纯注解 msg 不会成为枚举成员，遍历仅含声明项。"""
    assert [m.name for m in OrderStatus] == ["PENDING", "PAID", "DONE"]
    assert "msg" not in ValueMsgEnum.__members__


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # 命中返回对应成员实例。
        ("paid", "PAID"),
        ("pending", "PENDING"),
        ("done", "DONE"),
    ],
)
def test_get_hit(value: str, expected: str) -> None:
    """get 命中时返回对应成员。"""
    assert OrderStatus.get(value).name == expected


@pytest.mark.parametrize("value", ["refunded", "", "PENDING"])
def test_get_miss_returns_none(value: str) -> None:
    """get 对未声明的值（含空串与大小写不符）返回 None。"""
    assert OrderStatus.get(value) is None


def test_get_hit_returns_member_identity() -> None:
    """get 命中返回的是成员单例本身。"""
    assert OrderStatus.get("paid") is OrderStatus.PAID


def test_extending_membered_enum_raises() -> None:
    """enum 不允许继承已定义成员的枚举，需要扩展成员时应重新声明。"""

    with pytest.raises(TypeError, match="cannot extend"):

        class ExtendedStatus(OrderStatus):
            REFUNDED = ("refunded", "已退款")


def test_duplicate_value_raises() -> None:
    """重复 value 在子类定义期被自动拦截并抛 ValueError。"""

    with pytest.raises(ValueError, match="duplicate values"):

        class Dup(ValueMsgEnum):
            A = ("x", "甲")
            B = ("x", "乙")


def test_explicit_alias_raises() -> None:
    """显式别名成员（B = A）同样在类定义期被拦截。"""

    with pytest.raises(ValueError, match="duplicate values"):

        class Alias(ValueMsgEnum):
            A = ("a", "甲")
            B = A
