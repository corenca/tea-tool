# tea-tool

Commonly used Python development toolkits in business development.

业务开发常用的 Python 工具集，面向 Python >= 3.12，基于 polars 与 pydantic 构建，覆盖数据读写（CSV / Excel）、时间处理、数据脱敏、数据模型基类等高频场景。

## 特性一览

| 模块 | 定位 | 状态 |
| --- | --- | --- |
| `tea_tool.util.collection` | 列表 / range / 任意可迭代对象的切分（按大小或按份数） | 已实现 |
| `tea_tool.util.csv` | CSV 与 polars DataFrame 互转 | 已实现 |
| `tea_tool.util.excel` | .xlsx 与 polars DataFrame 互转（需安装 `excel` 可选依赖） | 已实现 |
| `tea_tool.util.enum` | 带额外信息 `msg` 的值枚举基类 `ValueMsgEnum` | 已实现 |
| `tea_tool.datetime` | 时间处理：格式常量、时区常量、日历时刻边界与解析函数 | 已实现 |
| `tea_tool.masking` | 通用脱敏：机制（策略 / 规则 / 编排器）与内容（业务规则）分离 | 已实现 |
| `tea_tool.schema` | pydantic 模型统一基类与时间字段 JSON 序列化别名 | 已实现 |
| `tea_tool.django` / `tea_tool.storage` | Django / 对象存储相关工具 | 计划中 |

## 安装

要求 Python >= 3.12，已发布到 PyPI：

```bash
# pip
pip install tea-tool
```

```bash
# uv
uv add tea-tool
```

Excel 读写（`util.excel`）依赖可选的 fastexcel 与 xlsxwriter，按需安装：

```bash
pip install 'tea-tool[excel]'
# 或
uv add 'tea-tool[excel]'
```

未安装可选依赖时，调用对应读写函数会抛出带安装指引的 ImportError，指引信息同时给出 pip 与 uv 两种安装方式。

## 模块速览

各模块的每个函数 / 类的参数说明与用法示例见对应源码 docstring。

- `tea_tool.util.collection` — 按固定大小切分可迭代对象（`chunked`、`chunk_list`），或按指定份数均分列表 / range（`split_list`、`split_range`），以及 range 版本的分块（`chunk_range`）。
- `tea_tool.util.csv` — `csv_to_df` 读取 CSV 为 polars DataFrame、`df_to_csv` 将 DataFrame 写出为 CSV。
- `tea_tool.util.excel` — `excel_to_df` 读取 .xlsx 为 polars DataFrame（支持文件表头到内存列名的映射）、`df_to_excel` 将 DataFrame 写出为 .xlsx。
- `tea_tool.util.enum` — `ValueMsgEnum`：成员以 `(value, msg)` 二元组声明，`value` 为枚举值，`msg` 携带对应额外信息，并提供按值查找的 `get()`。
- `tea_tool.datetime.formatter` — 常用日期时间格式常量：连字符 / 斜杠 / 中文 / ISO 等（如 `DATE_FORMAT`、`DATE_TIME_FORMAT_CN`）。
- `tea_tool.datetime.timezone` — 常用 IANA 时区常量（`UTC`、`SHANGHAI`、`NEW_YORK` 等）与获取本地时区的 `local_tz()`。
- `tea_tool.datetime.util` — 时段边界（`get_month_start` / `get_month_end` / `get_day_start` / `get_day_range`）、当月天数（`get_days_in_month`）、日期序列（`list_days`）、当前时刻（`get_local_time` / `get_utc_time`）、字符串解析（`parse_datetime`）。
- `tea_tool.masking` — 机制与内容分离的脱敏工具：策略定义"如何脱"（`KeepStrategy` / `ReplaceStrategy` / `HashStrategy` / `RemoveStrategy`），规则在自由文本中发现敏感片段，`Masker` 提供 `mask`（单值）、`mask_text`（自由文本自动识别）、`mask_dict`（结构化字段映射）三个入口；`presets` 模块提供中国大陆常见个人信息的预置识别规则（手机号、身份证、邮箱、IP、银行卡号）。
- `tea_tool.schema` — 项目数据模型统一基类 `BaseModel`（预设 `from_attributes`、`validate_assignment`、`populate_by_name`、忽略未声明字段等配置），以及 `DateTimeField` / `DateField` / `LocalDateTimeField` 时间字段标注（json 序列化时输出固定格式字符串）。

## 开发与测试

项目由 uv 管理，采用 src 布局，测试目录镜像源码目录结构：

```bash
uv sync            # 安装依赖（含 dev 组）
uv run pytest      # 运行测试
uv run ruff check  # 静态检查
uv run ruff format # 格式化
uv build           # 构建 wheel / sdist
```

## License

MIT
