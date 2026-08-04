# 参与贡献

[English](CONTRIBUTING.md) · 简体中文

感谢你帮助 RigorBreeze 变得更安全、更精简、更易使用。

## 提交修改前

- 创建一个范围明确的 Issue 或讨论，说明观察到的失败、相关任务和实际用户成本。
- 如果核心工作流行为正确，优先修改项目配置或技术栈适配器。
- 不要因为假设中的使用场景增加永久核心能力。
- 除非安全或摩擦证据足以支持，否则保持公共行为兼容。

普通流程摩擦至少应在两个真实垂直切片中出现，才修改通用核心。若门禁错误放过秘密、越权、破坏性迁移、过期证据、未授权 Git 动作或错误发布，发生一次即可进入核心审查。

## 开发环境

需要 Git 和 Python 3.11 或更高版本。运行时只使用 Python 标准库；仓库质量检查还可以使用 Ruff。

执行完整回归：

```bash
python3 -m unittest discover -s rigorbreeze/scripts/tests -v
```

安装 Ruff 后执行仓库静态检查：

```bash
python3 -m ruff format --check rigorbreeze/scripts
python3 -m ruff check rigorbreeze/scripts
python3 -m py_compile rigorbreeze/scripts/flow.py
```

使用 Codex `skill-creator` 校验器检查可安装 Skill：

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py rigorbreeze
```

## 修改规则

1. 增加或定位一个能够代表真实问题的失败回归。
2. 使用最小修改修复该失败。
3. 保持一个任务 Markdown 加一个证据 JSON 的唯一事实模型。
4. 没有真实证据和明确设计审查时，不增加依赖、公共 CLI 命令、Spec 文件类型或默认自动化权限。
5. 保持 `SKILL.md` 紧凑，把详细策略放进现有 reference。
6. 提交前执行完整回归，并在干净临时项目中验证工作流。

文档修改必须保持中英文引导合同一致。不要把仓库级 README、变更记录、贡献指南、许可证或安全策略复制进可安装 Skill 目录。

## Pull Request

说明问题、证据、选择的边界、拒绝的方案、兼容性影响和实际运行的验证。可以提交 AI 生成的修改，但提交者必须亲自审查并测试，并在 PR 描述中注明使用的 Agent 和模型。

提交贡献即表示你同意该贡献按照仓库的 [MIT License](LICENSE) 授权。
