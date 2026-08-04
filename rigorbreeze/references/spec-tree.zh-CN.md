# 最小 Spec Tree 合同

[English](spec-tree.md) · 简体中文

## 目录

1. [目的](#目的)
2. [目录结构](#目录结构)
3. [权威顺序与生命周期](#权威顺序与生命周期)
4. [状态与证据](#状态与证据)
5. [证据失效](#证据失效)
6. [扩展规则](#扩展规则)

## 目的

最小 Spec Tree 在不重复需求的前提下保留跨 Session 状态和可审计性。不会把同一个变更复制成 proposal、design、plan、test-plan 和 verification 多份文档；每个变更只有一份人工任务文件。

## 目录结构

```text
spec/
├── index.md
├── changes/
│   └── TASK-001.md
├── evidence/
│   └── TASK-001.json
└── archive/
    └── TASK-000.md

rigorbreeze.toml
scripts/rigorbreeze.py
scripts/flow_state.py
scripts/flow_policy.py
scripts/flow_parallel.py
scripts/flow_automation.py

.git/rigorbreeze/registry.json                 # Git 公共私有状态，不提交
.git/rigorbreeze/automation.json               # 外部动作日志
.git/worktrees/<name>/rigorbreeze/state.json   # worktree 私有状态
```

- `index.md`：只保存权威顺序和导航。
- Git 私有 `state.json`：schema v4 阶段、活动任务、批准、最新 RED/验证、警告和最后关闭记录。兼容迁移期间仍可读取主 worktree 原有 `spec/state.json`。
- `changes/<TASK-ID>.md`：唯一人工变更合同。
- `evidence/<TASK-ID>.json`：基线、检查、TDD 链、验证、制品摘要、验收、发布和预填实践摘要。
- `archive/<TASK-ID>.md`：完成适用风险门禁后移动的同一任务，不创建副本。
- `rigorbreeze.toml`：标准检查、profile、命令、报告、制品、超时和风险适用性。
- `scripts/rigorbreeze.py`：本地和 CI 使用的稳定项目入口。
- `scripts/flow_state.py`：配置、模板、Schema 升级、state/evidence、摘要和原子读写。
- `scripts/flow_policy.py`：任务合同、范围、TDD、新鲜度、风险和交付门禁。
- Git common `registry.json`：可丢弃的跨 worktree 索引，可以从 worktree 和私有状态重建，不是需求或证据事实源。
- Git common `automation.json`：以不可变输入为键的私有 commit/push/provider 动作日志，记录长期或单次授权，支持恢复和幂等，且不会在外部动作后改写 tracked evidence。

## 权威顺序与生命周期

权威顺序：

```text
批准的业务/设计依据
→ 活动任务合同
→ API/数据/安全/运维合同
→ 测试和运行证据
→ 代码与制品
→ 归档历史
```

生命周期：

```text
draft → approved → red → implementing → verified → accepted
→ archived

accepted → release-ready → protected release gate
```

完成和废弃任务都会把同一合同移动到 `archive/`，由 `closure.outcome` 区分成功和取消，不伪造验证结果。`release-ready` 是可选生产发布分支，不是关闭所有任务的前提。

一个 worktree 只能有一个活动任务，一个项目可以有多个活动 worktree。每个并行写任务使用自己的 `rigorbreeze/<task-id>` 分支和 linked worktree；两个写窗口不能共享同一物理 worktree。

每个任务合同中的 `Depends-On` 是唯一 DAG 表示。独立任务使用 `Depends-On: none`。执行器推导拓扑顺序、环、缺失依赖、ready 和范围冲突，不增加第二份 DAG 文档或任务数据库。

## 状态与证据

私有 `state.json` 和公共注册表是机器缓存和门禁输入，不是产品需求源。不要提交 linked-worktree 状态，也不要手工修改状态绕过门禁。`doctor --all --repair` 只在明确请求时重建注册表。

`status --json` 包含 `installation` 和 `scope` 投影。安装状态对比 bundled Skill 与项目执行器，返回 `current`、`outdated`、`missing` 或 `unmanaged` 以及是否可安全升级。范围状态为 `current`、`violated` 或 `not-applicable`，计算从批准基线到 `HEAD` 的已提交变化和当前工作树变化。

`status --all --json` 还包含运行资源声明/冲突与 `cleanup` 投影，列出可删除的已集成受管 worktree、带安全原因的保留项、未登记 Git worktree，以及按策略保留的本地任务分支。该投影只从 Git 和注册表推导，是提示状态，不是第二套任务或证据事实源。

证据 JSON 可以保存：

- 需求 ID；
- 精确 argv 命令，而不是 shell 字符串；
- 退出码和脱敏输出摘要；
- 任务摘要和项目指纹；
- Git HEAD 和时间；
- 运行、审查、安全、迁移、第二人和事故证据引用。

schema v4 的稳定区段包括 `baseline`、`checkRuns`、`tddChain`、`artifacts`、`acceptance`、`release`、`automation`、`practice`、`red`、`verifications` 和表示完成/废弃结果的 `closure`。`release` 可保存经过校验的 `operation-plan` 与 `operation-result` 快照，`practice` 可保存去重机器事件。历史 evidence 中的 `automation` 记录继续可读，但新的外部动作结果只写入 Git 私有日志。实践确认只为负向流程信号设置 `evolutionCandidate`，直接从证据汇总候选，不建立额外日志。升级 schema v1/v2/v3 时不得删除 RED、验证、验收、发布、自动化或实践历史。

不得保存凭证、生产数据、包含个人信息的完整日志或无法验证的结论。

## 证据失效

修改已批准任务会让批准和全部下游证据失效。修改源码、测试、依赖文件、配置、迁移或 `rigorbreeze.toml` 会让验证、验收、制品和发布证据失效。生成状态、证据、配置报告和制品从源码指纹中排除，避免证明自我失效。证据只有在适用的任务摘要、项目指纹和配置摘要均匹配时才有效。

生产实现变化后，不能通过重新批准合同创建新基线。应恢复已批准合同并完成，或先回退生产变化，再修订并重新批准同一可观察结果；新增用户结果或验收条件才建立依赖任务。merge 或 archive 前，每条当前 RED 链都必须保持测试摘要未变化，并将 GREEN 绑定到当前 full 验证。

范围 glob 具备路径语义：`*` 不跨 `/`，完整的 `**` 路径段匹配零层或多层目录。当前任务合同和对应机器证据属于任务所有；策略、配置、执行器及其他 Spec 文件必须显式进入范围。

批准时的基准分支 SHA 也属于新鲜度。另一个任务推进基准后，受影响的活动任务必须吸收新基准，并重新执行 affected/full 和适用验收。注册表变化本身不会让证据失效，变化的 Git 基准才会。

依赖和迁移批准必须显式记录，因为它们改变供应链和数据风险，但批准不能替代漏洞扫描、许可证检查、迁移演练、备份、恢复或回滚证据。

## 扩展规则

只有真实垂直切片证明存在重复需求时才增加字段或文件。优先使用生成 JSON 或 CI 制品，不增加人工文档。不能为了让目录看起来完整而建立新的事实源。项目 profile 中不存在的检查不需要 `N/A`。
