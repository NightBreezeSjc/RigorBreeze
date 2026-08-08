# RigorBreeze

**生产级严谨，轻量化执行。**

一套面向个人开发者、证据驱动且风险自适应的 Codex AI 工程工作流。

[![Public Preview](https://img.shields.io/badge/status-Public%20Preview-f59e0b)](#public-preview-与-v10)
[![Skill CI](https://github.com/nightbreezesjc/rigorbreeze/actions/workflows/ci.yml/badge.svg)](https://github.com/nightbreezesjc/rigorbreeze/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)

[English](README.md) · 简体中文

RigorBreeze 把粗略项目想法或边界明确的需求连接成一份经过批准的任务合同、真实观察到的 TDD 证据、项目配置的质量检查、真实环境验收和可恢复的交付记录。它刻意小于完整项目管理系统：一个任务 Markdown、一个机器证据 JSON，不创建文档迷宫。

> **Public Preview：** v0.10.3 当前已经可以使用，并补齐真实交付暴露的项目塑形、工作流基线、已集成旧任务、未批准交付绕过、归档后交付、不完整或复合提示词、重复外部操作、压力下 Agent 行为和可避免的本地验证摩擦；但尚未完成 v1.0 所要求的验证，接口仍可能根据后续真实交付证据调整。

## 为什么需要它

AI 可以很快生成代码，但仍可能做错业务行为、遗漏设计状态，或者让测试通过却没有证明用户结果。对于长期项目和多个 Codex 窗口，聊天历史也不是可靠的事实源。

RigorBreeze 把人的注意力放到最关键的开头和结尾：

```text
先对齐用户结果和验收边界
→ Codex 在可观察反馈循环中实现
→ 人在真实运行环境中验收结果
```

它补充可审计 SDD、真实 RED–GREEN–REFACTOR、项目声明式检查、真实验收、安全并行 worktree 和可选的受保护 Git 自动化，同时保持最小 Spec Tree。

## 它适合谁

适合：

- 使用 Codex App 或 Codex CLI 的个人开发者；
- 需要跨 Session 或多个 Codex 窗口长期维护产品；
- 交付涉及测试、设计还原、权限、迁移或回滚的真实功能；
- 愿意确认一份精简任务合同并亲自查看真实结果。

不适合：

- 出错成本很低的一次性脚本和周末原型；
- 需要团队排期、人员管理、Issue 看板或 Agent 控制台的组织；
- 完全无法配置构建、测试或验收命令的项目；
- 希望 AI 自己批准视觉、安全、法务或生产结论的流程。

当前正式支持 Codex App 和 Codex CLI。其他兼容 Agent Skills 的工具可能能够加载本 Skill，但在完成安装和行为验证前只属于实验性支持。

## 60 秒安装

前置条件：Git、Python 3.11 或更高版本、Codex App 或 Codex CLI。

### 方式 A：Agent Skills 安装器

```bash
npx skills@latest add nightbreezesjc/rigorbreeze --skill rigorbreeze -g -a codex -y
```

`skills` CLI 是第三方安装器，拥有自己的遥测策略。如果不希望安装器发送遥测，可为该命令设置 `DISABLE_TELEMETRY=1`，或者使用下面的手工安装方式。

安装完成后重启或重新加载 Codex。

### 方式 B：Git clone 后复制

在你存放开发工具的目录中执行：

```bash
git clone https://github.com/nightbreezesjc/rigorbreeze.git
mkdir -p ~/.codex/skills
cp -R rigorbreeze/rigorbreeze ~/.codex/skills/rigorbreeze
```

如果要参与本 Skill 开发，可以不执行最后一条复制命令，改为创建软链接：

```bash
ln -s "$(pwd)/rigorbreeze/rigorbreeze" ~/.codex/skills/rigorbreeze
```

外层目录是 GitHub 仓库，内层目录才是可安装 Skill。

### 验证安装

在一个 Git 项目中新建 Codex 任务并输入：

```text
$rigorbreeze 检查这个项目并告诉我工作流是否已经初始化
```

Codex 应当加载 Skill、检查仓库，并报告当前 `nextAction` 或提出初始化项目。

## 在首个任务前塑形项目

当想法属于新产品、新业务域、大范围旧系统迁移，或者仍然包含多个可能结果时，
先让 RigorBreeze 完成产品塑形，再创建交付任务：

```text
$rigorbreeze 在创建任务前先塑形这个项目。先恢复项目事实，区分证据、假设和未知；比较两到三个可行方案；覆盖用户旅程、期望结果、成功指标、四类产品风险、投入边界、风险坑和明确不做；推荐首个纵向切片，并等待我批准。
```

这一步是按需的。边界清楚的普通功能或缺陷仍直接进入任务合同。塑形优先复用
一个有版本的产品/设计来源，必要时只在 Spec Tree 之外建立一份精简简报；不会
制造 PRD 文档树、实施 DAG，也不会从角色提示或参考源码中虚构产品真相。批准后，
只有首个切片进入 RigorBreeze 任务。

## 第一个真实任务

正常使用时，你在 Codex 对话中描述目标，不需要自己操作每一条内部命令：

```text
$rigorbreeze 初始化这个项目，并开发一个允许用户修改显示名称的个人资料页面
```

Codex 会：

1. 读取当前项目，并从权威需求、代码、测试、Git 和运行证据中补全缺失上下文；
2. 提出一份包含范围、验收 ID、风险和测试接缝的可观察任务；
3. 请你一次确认这份精简合同；
4. 为 L1/L2 行为观察 RED，小步实现 GREEN，并执行项目检查；
5. 展示适用的真实页面、接口、真机、迁移或运行证据；
6. 请你验收结果，并在归档前确认一次预填复盘。

你真正需要做的判断只有三类：批准目标、验收真实结果、确认流程是否有帮助。内部命令和证据由 Codex 执行与记录。

你不需要先写出完美提示词，也不必添加“你是互联网独角兽 CTO”之类的人设。RigorBreeze 会自行恢复项目事实、当前行为、架构路径、不变量以及数据新鲜度/兜底语义；只有证据无法确定且会显著改变结果的意图才询问你。执行外部 Git、部署、开发者工具或平台写操作前，它会先说明已经完成什么、当前不可变标识、唯一剩余动作和停止条件，避免重放旧清单。

批准前，RigorBreeze 会检查占位符、内部矛盾、过大切片，以及结果/事实源/兜底语义歧义。复合需求会拆成可观察的 ADD/REMOVE/MOVE/RETAIN/REPLACE 原子，每项映射到验收或明确不做；UI 最终状态清单覆盖必须存在、必须不存在、位置/顺序和保留行为。否定表达会根据证据判断是在描述当前问题还是目标结果，只有方向仍会改变结果时才问一个简短问题。完成声明必须说明本轮新运行的命令、退出状态和覆盖范围；评审建议先与仓库事实和 YAGNI 对照；同一缺陷连续三个假设失败后进入架构停点，不继续堆第四个补丁。维护者使用六个合成 Agent 压力场景验证这些规则；测试资产不会安装到业务项目，CI 也不会调用真实模型。

Allowed Scope 只能填写仓库相对路径、目录前缀或 glob；`*` 只匹配一层路径，`**` 才跨目录。验收条件必须使用唯一且机器可读的 ID。不能在生产代码变化之上重新批准：应恢复已批准合同并完成，或先回退生产变化，再修订同一用户结果。新增用户结果或验收条件才建立依赖切片。

初始化并配置项目检查后，应在首个 enforced L1/L2 批准前由人建立 Git 工作流基线。`status --json` 会在 `workflowBaseline` 中报告真正基准分支的状态。用户明确授权后，Codex 可以执行 `automate commit --once --workflow-baseline --expected-head <SHA>`；它只暂存受管工作流文件，遇到混入产品改动或秘密时阻断，且不会持久化 Git 权限。安装后的 Skill 始终使用自身 v0.10.3 bundled runner 检查项目，分别报告缺失或被修改的组件，活动实施任务存在期间不会静默覆盖。任务尚未批准却已修改交付文件时，status 会报告 `workflowBypass=detected`、记录一条去重演进候选，并要求诚实恢复或 reconciled 收口，不允许补造 RED 或重建基线。

初始化后，项目会包含：

```text
spec/
├── index.md
├── changes/TASK-001.md       # 唯一人工任务合同
├── evidence/TASK-001.json    # 机器证据与新鲜度
└── archive/

rigorbreeze.toml               # 项目检查与策略
scripts/rigorbreeze.py         # 本地和 CI 使用同一个执行器
.git/rigorbreeze/state.json    # 私有状态，永不提交
```

检查下一动作的标准命令是：

```bash
python3 scripts/rigorbreeze.py status --json
```

这条命令主要由 Codex、CI 和故障排查使用。完整 CLI 语法以 `python3 scripts/rigorbreeze.py --help` 为准。

## 工作流如何运行

```text
仅在项目结果尚未稳定时先完成项目塑形
→ 定义一个垂直切片
→ 批准任务摘要
→ 观察 RED
→ 实现 GREEN 并重构
→ 执行 affected/full profile
→ 检查真实运行结果
→ 分别进行规范审查和规格审查
→ 确认预填复盘
→ archive
→ 按需执行受保护的 commit/push/merge
→ reconcile 并清理已集成 worktree
```

门禁成本随风险变化：

| 通道 | 典型变更 | 关闭要求 |
|---|---|---|
| L0 | 文档或孤立的非行为变更 | 配置的 affected 检查 |
| L1 | 普通功能、修复或用户流程 | RED、full、真实验收、审查、复盘 |
| L2 | 权限、敏感数据、迁移、支付、集成、发布 | L1 加适用的安全、迁移和发布控制 |
| Emergency | 最小安全生产热修 | 故障复现、关键回归、回滚和证据修复 |

任务归档不等于生产发布。不可变制品、灰度、SLO、告警和回滚证据只在明确请求生产发布时进入门禁。

对于条件化 L2 外部集成，`Operational-Modes` 将启用、关闭和依赖不可用行为绑定到真实验收 ID。L2 发布执行远程写操作前，机器 JSON 操作计划必须绑定准确 SHA/制品，并列出备份、配置冻结、迁移、部署、验收、切换、观察阶段及其成功条件、停止条件、安全恢复点和回滚限制。暂停或失败时只记录一个当前安全状态和一个恢复入口，避免盲目重跑整套发布。

## 最小 Spec Tree

每个变更只有一份人工 Markdown 合同和一份机器 JSON 证据。需求通过链接引用，不复制成 proposal、design、plan、test-plan 和 report 等多份文档。

任务合同记录当前依据、机器可检查的允许和禁止范围、验收 ID、测试接缝、独占 `Runtime-Claims`、条件化 `Operational-Modes` 和适用风险。证据 JSON 记录批准摘要、RED、检查、报告、验收、制品身份、发布操作快照和复盘事实。相关源码、测试、配置、依赖、迁移或任务摘要变化后，旧证据会自动失效。`status --json` 同时投影安装状态和范围漂移，旧执行器或范围外改动不能被通过的验证掩盖。

回归测试属于长期产品资产。任务正常完成归档时，重复检查明细会压缩为每个 profile/check 的最新记录和最近一次历史失败，并在同一 evidence JSON 中保留汇总次数；abandoned 与 reconciled 历史保持完整。普通审查事实直接进入结构化 evidence，只有确实需要独立核查的发现才建立单独报告；临时完整日志放入忽略目录或有期限的 CI Artifact。

权威顺序和失效规则见安装包内的 [Spec Tree 合同](rigorbreeze/references/spec-tree.zh-CN.md)。

## 安全与隐私默认值

- 本地检查默认 advisory；CI、L2、merge 和 release 使用 enforced。
- Git 自动化默认 `manual`：不允许无人值守的 Git 写操作，但用户对当前任务的明确要求可以单次授权安全 commit 或 push，且不会修改项目长期等级。升级 Skill 不会提高长期权限。
- 不通过 force push 或本地直合绕过受保护分支。
- 受管 worktree 清理必须证明创建来源、准确路径、集成状态和干净状态。未登记 worktree 默认只报告；只有用户一次性明确给出绝对路径、基准分支、expected HEAD 和 `--allow-unmanaged` 时才可按同等标准清理，且始终保留分支。
- 被取消或替代的任务只有在任务范围内工作树干净、外部动作结果明确时，才可按 `abandoned` 归档并释放任务槽和运行资源；分支和 worktree 不会被自动删除。
- 任务修改 `AGENTS.md`、`rigorbreeze.toml` 或执行器等工作流策略文件时，必须把它们显式写入 Allowed Scope。
- 外部动作恢复信息保存在 Git 私有 `.git/rigorbreeze/automation.json`。
- 项目证据留在项目内；Skill 没有遥测，不上传源码、提示词、证据或指标。
- 任务证据不得保存秘密、凭证、生产数据或包含敏感信息的完整日志。
- 临时或合成凭证只能证明“可以构建”，不能满足真实环境验收、部署或发布证据。
- AI 不能批准自己的视觉基线、安全例外、法务结论或生产发布。

Skill 通过项目配置编排真实的安全、迁移、CI、浏览器、真机和监控工具，不会用内部占位检查冒充这些能力。

## 并行开发与可选自动化

一个物理 worktree 只能有一个活动写任务。另一个 Codex 窗口需要并行写入时，Skill 会创建隔离的 `rigorbreeze/<task-id>` 分支和 worktree。文件隔离并不能隔离端口、watcher、本地服务、环境和开发者工具；任务只需通过 `Runtime-Claims` 声明实际占用的独占资源，活动声明冲突会被阻断。`status --all --json` 是统一只读项目视图。

同一状态结果会展示可清理、需保留和未登记的 worktree，并给出是否干净、集成证明、expected HEAD 和是否需要确认。RigorBreeze 同时识别祖先式 merge 与完整补丁等价的 cherry-pick。已登记任务只有在至少一个产品补丁已经等价进入基准分支，且额外提交全部属于严格白名单工作流元数据时才视为已集成；混合或未匹配产品改动仍保持活动。清理通常只删除创建来源完整且干净的 worktree；未登记清理继续使用原有保守证明，本地分支始终保留。

独立任务不创建 DAG。只有真实先后关系存在时，Codex 才一次提出精简依赖图，并只通过每个任务的 `Depends-On` 保存。该字段只表示同仓库依赖；跨仓库任务在 Authoritative inputs 中关联对方任务和 API/数据契约，提供方尚未集成并验证前，消费方不得完成真实验收。环、缺失依赖、Allowed Scope 重叠、过期基线和重复窗口认领都会被阻断。

项目可以显式提高 `[automation].level`：

```text
manual → commit → push → merge → release
```

每一级包含前一级、只作用于当前任务，并要求对应门禁通过。merge 和 release 通过受保护平台适配器执行；生产迁移和回滚始终需要单独权限。

`manual` 不等于禁止用户明确要求交付。用户清楚要求提交或推送当前任务时，Codex 可以在展示准确的仓库、remote、分支和 HEAD 后使用一次性授权。单次推送会先 fetch，要求 HEAD 未变化，只允许 fast-forward，禁止 force push，完成后核对远端 SHA，并且不会保留授权。直接推送集成分支还必须具备当前 full 验证、验收和审查。merge、release、生产迁移和回滚不会继承该权限。

## 配置检查和 CI

从一个内置适配器开始：

- `rigorbreeze/assets/config/generic.toml`；
- `rigorbreeze/assets/config/java-vue-uniapp.toml`。

复制 `rigorbreeze/assets/ci/` 中的 GitHub Actions 或 GitLab CI 模板，再在 `rigorbreeze.toml` 配置项目真实使用的命令。enforced 模式下，profile 中声明的检查必须存在并通过；不相关能力不需要填写 `N/A`。L2 的 `full` 始终推导出 secrets、build、至少一项静态质量检查和至少一项行为检查；修改依赖时额外要求 dependency、license、SBOM 报告，修改迁移时要求 migration 适配器与报告。

远程 Required Pipeline 才是合并权威，本地 Hook 只能提醒。仓库公开并实际运行 GitHub Actions 后，首页 CI 徽章才代表声明的 Python 和操作系统矩阵结果。

## 更新与卸载

安装器管理的 Skill 可以这样更新：

```bash
npx skills@latest update rigorbreeze -g -y
```

手工复制方式需要拉取仓库，然后只替换 `~/.codex/skills/rigorbreeze` 中的内层 Skill。软链接方式会随仓库更新。

卸载安装器管理的 Skill：

```bash
npx skills@latest remove rigorbreeze -g -a codex -y
```

手工安装时，只删除 Codex skills 目录中的 `rigorbreeze` 目录或软链接。业务项目中已有的 `spec/`、执行器、证据和配置不会被自动删除。

## Public Preview 与 v1.0

v0.10.3 保持最小 Spec Tree 和现有命令面，并阻止正常完成任务的重复成功检查明细无限累积。它保留最终结果、最近一次历史失败、汇总次数、全部 profile 级验证历史、TDD、验收、实践和关闭事实；不会删除回归测试或非完成任务历史。更高成熟度仍必须来自反复真实使用，而不是继续增加功能。

达到 v1.0 前至少需要完成：

- 一个普通 L1 垂直切片；
- 一个涉及权限、迁移或发布治理的 L2 高风险切片；
- 一次两个 worktree 的真实并行交付；
- 一次至少三个节点的真实依赖 DAG；
- 远程 Required CI 和受保护自动交付演练；
- 一次适用的灰度、监控和回滚演练。

证据还必须证明 `nextAction`、affected/full 选择、证据失效、门禁和复盘减少了返工与逃逸风险，而不是把开发变成填表。完整方法见 [Skill 演进与实践记录](Skill演进与实践记录.md)。

## 仓库协作方式

RigorBreeze 采用 [GitHub Flow](https://docs.github.com/zh/get-started/using-github/github-flow)，不维护永久性的 Git Flow 分支层级：

```text
从最新 main 开始
→ 一个结果对应一个短期分支
→ 提交范围明确的 commit
→ 向 main 发起 Pull Request
→ Required CI 与维护者决策
→ squash 或 rebase 合并
→ 删除已合并分支
```

分支使用 `feat/`、`fix/`、`docs/`、`refactor/` 或 `test/` 等清晰前缀，例如 `docs/clarify-installation`。只有真实发布候选需要稳定时才临时创建 `release/vX.Y.Z`。项目不保留空的 `develop`、`hotfix` 或 release 分支：`main` 是唯一长期事实源，任务分支只负责隔离一项工作，合并后即可删除。

外部贡献者应 fork 仓库，并向 `main` 提交 Pull Request。是否以及何时合并由维护者决定；CI 通过只是必要条件，不会自行合并或发布。可复制的操作步骤和验证要求见[中文贡献指南](CONTRIBUTING.zh-CN.md)。

## 贡献与安全

提交工作流行为修改前阅读[中文贡献指南](CONTRIBUTING.zh-CN.md)。普通摩擦需要在真实切片中重复发生后才进入核心；错误放过秘密、越权、破坏性迁移、过期证据或错误发布的门禁问题需要立即审查。

漏洞请按[中文安全策略](SECURITY.zh-CN.md)私密报告，不要在公开 Issue 中提交秘密或漏洞利用细节。

变更记录见[中文变更记录](CHANGELOG.zh-CN.md)。项目使用英文 [MIT License](LICENSE)，并提供[中文参考译文](LICENSE.zh-CN.md)。

## 设计来源

RigorBreeze 是独立项目，设计参考了：

- [GitHub Spec Kit](https://github.com/github/spec-kit) 的规格驱动对齐；
- [OpenSpec](https://github.com/Fission-AI/OpenSpec) 的轻量变更式 SDD；
- [Superpowers](https://github.com/obra/superpowers) 的可组合工程纪律和先验证再声明；
- [mattpocock/skills](https://github.com/mattpocock/skills) 的小型可适配 Skill 与显式反馈循环；
- [Wu5 Dev Flow](https://github.com/WenOwen/wu5-dev-flow) 的可审计任务状态、TDD 证据和 Git 门禁。

这些经验被重新设计成适合个人 Codex 开发的最小 Spec Tree、项目声明式门禁、真实运行验收、隔离并行 worktree 和默认手动交付。本项目与上述项目没有隶属关系，也不声称可以直接替代它们。
