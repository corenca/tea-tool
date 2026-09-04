# tea-tool

Python 工具库（"Python tool box"，v0.1.0）。由 uv 管理，src 布局，Python >= 3.12，作者 Corenca。

## 项目现状

- `src/tea_tool/` — 包根（已含 `py.typed`，属于 PEP 561 类型标注分发库，代码需带完整类型标注）
  - `util/` — 通用工具（当前唯一有内容的模块：`util/collection.py`，含切分函数）
  - `django/`、`storage/` — 空包骨架，计划放置 Django / 对象存储相关工具
- dev 依赖含 ruff 与 pytest（`uv add --dev` 添加）；无 CI、无 typecheck 配置，别假设存在
- 当前无任何第三方运行时依赖（`dependencies = []`），新增依赖请用 `uv add` 而不是手改 pyproject

## 常用命令（uv）

- `uv sync` — 安装依赖到 .venv
- `uv add <pkg>` — 添加运行时依赖；`uv add --dev <pkg>` 添加开发依赖
- `uv run <cmd>` — 在虚拟环境中执行命令（运行脚本、跑测试都用它）
- `uv build` — 构建 wheel/sdist（build-backend 为 `uv_build`）

## 开发约定

1. **方法注释**：所有方法/函数必须编写 Google 风格 docstring（含 Args/Returns/Raises 段落），注释用中文
2. **Git 提交**：遵循 Conventional Commits
   - 格式：`type(scope): description`
   - type：feat/fix/docs/style/refactor/test/chore
   - 简洁明了，不超过 50 字的中文描述
3. **只提交自己的改动**：本仓库工作区常混有他人未提交的修改（依赖升级、脚手架等）。提交前用 `git status`/`git diff` 核对，只 `git add` 白名单自己的文件，勿连带他人改动一起提交
4. **提交前先检查与格式化**：每次 git 提交前必须执行 `uv run ruff check`、`uv run ruff format --check`（若有格式差异先 `ruff format`）与 `uv run pytest`，全部通过后再提交
5. `**/migrations/**` 被 .gitignore 忽略（保留 `__init__.py`）——Django 迁移文件默认不入库，后续添加 Django 应用时注意
6. **检查无用依赖**：提交前留意是否残留或引入不再使用的第三方依赖与无用导入（模块级 import、logger 等），无用者应移除——依赖用 `uv remove` 管理，代码内无用导入直接清理
7. **函数命名动词体系**：公共函数命名带动作提示词，见名知意——`get_` 取单值/时段边界（如 `get_month_start`）、`list_` 取序列（如 `list_days`）、`query` 表示检索，状态变更类用 `add`/`update`/`remove`；`parse` 等动词自足的不加前缀。命名在简洁的同时保证语义可推断
