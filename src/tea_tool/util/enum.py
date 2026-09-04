from enum import Enum
from typing import Self


class ValueMsgEnum(Enum):
    """带额外信息的值枚举基类。

    成员以 (value, msg) 二元组声明：value 作为枚举值（.value）及 get() 的
    查找键，msg 为 value 对应的额外信息（.msg）。例如::

        class Status(ValueMsgEnum):
            PENDING = ("pending", "待处理")
            DONE = ("done", "已完成")

        Status.PENDING.value  # "pending"
        Status.PENDING.msg    # "待处理"
        Status.get("done")    # Status.DONE

    同一枚举内 value 必须唯一，基类在子类定义期自动校验（等效 @unique）：
    重复 value 或显式别名成员会直接抛 ValueError，因此 get() 反查结果确定
    可靠。value 类型固定为 str，需要其他 code 类型时可在子类中重写 __new__
    与 get 放宽。
    """

    msg: str  # 类级纯注解供静态检查器识别 .msg；不带赋值故不会成为枚举成员

    def __init_subclass__(cls, **kwargs: object) -> None:
        """在子类定义期校验枚举值唯一，拦截重复 value 与显式别名。

        复刻标准库 @unique 的别名检测：成员 value 与已定义成员重复时，enum
        会将其作为别名成员挂到先定义者名下（成员名与定义名不一致），据此
        报错。子类若再叠加 @unique，仅做同样的重复校验，互不冲突。

        Raises:
            ValueError: 当子类含重复 value 或显式别名成员时。
        """
        super().__init_subclass__(**kwargs)
        dupes = [
            (name, member.name)
            for name, member in cls.__members__.items()
            if name != member.name
        ]
        if dupes:
            raise ValueError(f"duplicate values found in {cls!r}: {dupes}")

    def __new__(cls, value: str, msg: str) -> Self:
        """创建枚举成员实例，二元组首元素存为枚举值、次元素存为 msg。

        Args:
            value: 枚举值，须在同类内唯一。
            msg: 该值对应的额外信息。
        """
        obj = object.__new__(cls)
        obj._value_ = value
        obj.msg = msg
        return obj

    @classmethod
    def get(cls, value: str) -> Self | None:
        """按枚举值反查成员，未命中时返回 None（语义类似 dict.get）。

        Args:
            value: 待查找的枚举值。

        Returns:
            值匹配的枚举成员；无对应成员时返回 None。
        """
        try:
            return cls(value)
        except ValueError:
            return None
