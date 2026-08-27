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

验证离线 Agent 行为合同和评分器：

```bash
python3 -B tests/behavior/run.py validate
python3 -B -m unittest discover -s tests/behavior -v
```

发布候选版本前，由维护者使用本机 Codex 将十九个合成场景各运行两次；这一步需要明确手动触发，普通提交、配置化 `full` 和 CI 都不会运行：

```bash
python3 -B tests/behavior/run.py run --version 0.18.0 --repetitions 2
```

任一次违反硬规则都阻断候选版本。只检查 `.git/rigorbreeze/behavior-evals/0.18.0/` 下的脱敏 Git 私有结果；不得提交这些结果，也不得在 fixture 中使用真实凭证或服务。每次结果还记录缓存/非缓存输入、输出与推理 Token、纯流程 Runner 调用数、evidence 字节数及产品/测试行数变化。固定模型的不同 arm 必须比较中位数，不能用一次运行宣传节省比例，也不能为了 Token 目标放宽安全规则。

源码仓库必须保留回归测试和行为合同测试。可分发 Skill ZIP 排除维护者测试、缓存和字节码；应通过合同测试验证该边界，而不是删除测试资产。维护者任务合同、机器 evidence 和 archive 在本源码仓库中只保存在本地并被忽略；提交、变更记录、测试和 CI 才是公开贡献记录。

## 修改规则

1. 增加或定位一个能够代表真实问题的失败回归。
2. 使用最小修改修复该失败。
3. 活动任务以配置的 Git 私有合同/evidence 为唯一事实源；只有策略要求时发布脱敏高风险审计摘要，绝不公开原始维护者记录。
4. 没有真实证据和明确设计审查时，不增加依赖、公共 CLI 命令、Spec 文件类型或默认自动化权限。
5. 保持 `SKILL.md` 紧凑，把详细策略放进现有 reference。
6. 提交前执行完整回归，并在干净临时项目中验证工作流。

任何始终加载的指令都必须写清触发条件、完成条件和行为测试变化。删除一条指令后，如果确定性场景和真实任务行为都不受影响，就应删除它，或把解释性细节下沉到现有 reference。命令语法只属于 `--help`，执行规则属于 `SKILL.md`，详细理由属于 handbook，首次采用说明属于 README；不得建立相互竞争的事实源。

文档修改必须保持中英文引导合同一致。不要把仓库级 README、变更记录、贡献指南、许可证或安全策略复制进可安装 Skill 目录。

## Pull Request

RigorBreeze 只有一个长期分支：`main`。每个无关结果都从最新 `main` 创建一个短期分支：

```bash
git switch main
git pull --ff-only
git switch -c docs/clarify-installation
```

分支使用 `feat/`、`fix/`、`docs/`、`refactor/` 或 `test/` 前缀，后接简短 kebab-case 描述。只有真实发布候选需要稳定时，维护者才创建 `release/vX.Y.Z`。不要创建永久 `develop`、`hotfix` 或空 release 分支。

一个分支和一个 Pull Request 只解决一个可观察结果。推送分支后，向 `main` 发起 Pull Request：

```bash
git push -u origin docs/clarify-installation
gh pr create --base main --head docs/clarify-installation
```

说明问题、证据、选择的边界、拒绝的方案、兼容性影响和实际运行的验证。解决评审讨论并保持 Required CI 通过。检查通过不等于获得合并或发布权限；最终决定由维护者作出。合并后删除任务分支，不要用它继续承载无关修改。

可以提交 AI 生成的修改，但提交者必须亲自审查并测试，并在 PR 描述中注明使用的 Agent 和模型。

提交贡献即表示你同意该贡献按照仓库的 [MIT License](LICENSE) 授权。
