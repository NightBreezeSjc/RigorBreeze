# RigorBreeze 长期自主开发系统方案

> 状态：战略方案 v0.1  
> 适用对象：使用 Codex 独立维护长期生产级项目的个人开发者  
> 研究日期：2026-08-06  
> 当前基线：RigorBreeze v0.9.2 Public Preview

## 一、执行摘要

### 1. CTO 结论

未来目标不应再定义为“让 Codex 一次回答更久”，而应定义为：

> 人负责产品目标、关键设计和不可逆决策；系统把已批准目标编译成可验证的任务图，在 Mac mini 上持续调度隔离的 Codex 执行单元，自动完成低风险开发、验证、恢复和交付准备，并在结果型歧义、高风险操作或验证失败时暂停等待人类。

这个目标是合理且可以分阶段实现的，但不能由一个 Skill 单独完成。

- **GSD Core** 是上下文工程、规格驱动和阶段自动推进框架，能够在 Agent 运行环境中连续完成多个阶段；它不是负责进程守护、机器重启恢复、费用治理和生产权限隔离的 7×24 小时运行平台。
- **RigorBreeze** 应继续承担质量治理：需求合同、范围、风险、SDD/TDD、证据、新鲜度、worktree、验收和交付门禁。
- **新的持久化编排器** 应承担长期运行：任务队列、DAG、租约、心跳、超时、重试、上下文轮换、崩溃恢复、预算和通知。
- **Codex** 是执行引擎，通过 `codex exec --json`、Codex MCP/SDK 或 app-server 被编排器调用，而不是充当唯一的状态数据库和系统守护进程。
- **Git、CI 和真实环境** 是独立事实源，不能用 Agent 的“已完成”声明代替。

最终应形成一套工具链，而不是继续向 RigorBreeze 的 `SKILL.md` 填充所有能力。

```text
未来系统 = 人类产品治理
         + 目标与路线图
         + 持久化 DAG/Loop 编排器
         + Codex 执行器
         + RigorBreeze 质量治理
         + 独立验证器
         + Git/CI/交付系统
         + 沙箱、监控、预算和远程接管
```

### 2. 当前不应做的事

- 不把 GSD Core、RigorBreeze 和另一个任务系统同时设为事实源。
- 不在 RigorBreeze 核心中直接建设常驻进程、控制台、模型路由和完整部署平台。
- 不用一个无限循环 Prompt 代替任务图、停止条件和独立验证。
- 不因购买 Mac mini 就默认开放全磁盘、全网络或生产权限。
- 不在真实项目证明单任务“跑一夜”之前建设多项目、多模型和大规模并行平台。

## 二、目标重新定义：从连续 Prompt 到目标驱动开发

### 1. 用户未来只需要提供什么

用户不应继续手工写一段又一段开发 Prompt。一个里程碑开始前，只需要完成以下决策：

| 输入 | 负责人 | 内容 |
|---|---|---|
| 产品目标 | 人 | 用户最终得到什么结果，为什么重要 |
| 产品边界 | 人 | 不做什么、禁止改变什么、关键兼容要求 |
| 事实源 | 人与系统 | 需求、原型、接口、数据、权限和现有代码以什么为准 |
| 验收标准 | 人批准，系统补齐 | 可观察行为、关键状态、失败兜底和真实环境要求 |
| 风险授权 | 人 | 哪些动作可自动执行，哪些必须暂停 |
| 时间与费用预算 | 人 | 最大运行时间、Token/API 成本、并行数和重试次数 |

系统负责从代码、测试、Git、原型和接口恢复可以恢复的事实，提出路线图与任务图。人只批准会改变产品结果或权限边界的内容。

### 2. 理想的人机交互频率

```text
定义项目/里程碑目标
→ 系统研究并提出任务图
→ 人一次批准任务图与权限
→ 系统连续执行低风险节点
→ 只在歧义、高风险或失败预算耗尽时通知人
→ 人进行里程碑真实验收
→ 系统整理下一里程碑候选
```

这不是“完全不要人”，而是把人的工作从反复催促 Agent，提升为产品、架构、风险和验收治理。

## 三、GSD Core 到底是什么

### 1. 它具备真正的连续推进能力

GSD Core 将自身定义为位于用户与编码 Agent 之间的元提示、上下文工程和规格驱动框架。每个里程碑按 Discuss → Plan → Execute → Verify → Ship 推进，重型研究、规划和执行交给新鲜上下文的专用 Agent。[GSD Core README](https://github.com/open-gsd/gsd-core)、[GSD Core Architecture](https://github.com/open-gsd/gsd-core/blob/next/docs/ARCHITECTURE.md)

它当前提供两条重要自动链路：

- `gsd:autonomous`：按阶段连续执行 discuss → plan → execute，只在用户决策、阻断和验证请求时暂停。[Autonomous command](https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/autonomous.md)
- `gsd:progress --next --auto`：根据 `STATE.md`、`ROADMAP.md` 和阶段目录判断下一动作，完成后继续调用自身，直到完成或出现阻断决策。[Progress command](https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/progress.md)

所以，GSD Core 的确可以让一个清晰里程碑连续运行数小时并跨越多个阶段，它不是普通的“写计划 Skill”。

### 2. 它还不是 Mac mini 的完整自治平台

GSD Core 的主要状态位于 `.planning/` 文件中，重点解决上下文退化、阶段交接、规划、执行和验证。它并不等同于：

- macOS 开机自启和进程守护；
- 任务租约、心跳、僵尸进程识别；
- 断电、重启、网络故障后的可靠恢复；
- 多项目队列与全局资源调度；
- Token、API 费用、磁盘和并发预算；
- 凭证隔离、生产权限和审计；
- 手机告警、暂停、批准和恢复入口；
- 跨机器的耐久执行保证。

因此应把它评价为“优秀的 Agent 工作流与上下文编排框架”，而不是完整的 7×24 小时 Agent 操作系统。

## 四、GSD Core 对 RigorBreeze 的启发

### 1. 应吸收的设计

| GSD Core 设计 | 对 RigorBreeze 未来系统的价值 | 推荐落点 |
|---|---|---|
| Discuss → Plan → Execute → Verify → Ship | 把目标推进变成稳定阶段协议 | 外层里程碑编排器 |
| 重型工作使用新鲜上下文 | 防止长对话上下文退化和提前收尾 | 每个节点/失败轮次的新 Codex 执行单元 |
| 文件化持久状态 | Session 结束后仍能恢复位置与决策 | Git 中合同/证据，SQLite 中运行状态 |
| 薄编排器调用专用 Agent | 避免调度器既规划又实现又自评 | Planner、Builder、Evaluator 分离 |
| 依赖波次执行 | 独立节点并行，有依赖节点顺序执行 | RigorBreeze `Depends-On` 推导 DAG |
| Plan checker 和 post-execution verifier | 防止错误计划直接扩大为错误代码 | 批准前语义检查与独立验证节点 |
| 自动 next action | 减少用户反复输入“继续” | 消费 RigorBreeze `nextAction` |
| 有界检查循环 | 防止无限重试和 Token 失控 | 节点 retry/repair budget |
| UAT 仍为最终门禁 | AI 不批准自己的真实产品结果 | 保留 RigorBreeze 真实验收边界 |

### 2. 不应直接复制的设计

| 不直接复制 | 原因 |
|---|---|
| 大量命令、Agent 类型和规划文件 | 对个人项目会提高认知、维护和上下文成本 |
| GSD 与 RigorBreeze 两套活动任务状态 | 会产生阶段、完成结论和下一动作冲突 |
| 默认给所有任务建立完整研究和多 Agent 流程 | L0/L1 小任务会被流程成本吞没 |
| 用自动提交代替范围、证据和交付门禁 | 原子提交不等于需求正确和可发布 |
| 让规划 Agent 自动回答结果型歧义 | 可能连续数小时沿错误产品方向开发 |
| 把 Agent verifier 当作最终真实验收 | 自评偏乐观，尤其是视觉、权限和外部系统 |

### 3. 正确的集成关系

不建议在一个项目里直接让 GSD Core 和 RigorBreeze同时管理执行状态。更安全的方式是吸收架构思想；未来若做兼容适配器，应遵守：

```text
GSD 风格的里程碑规划结果
→ 转换为用户一次批准的 RigorBreeze 任务合同与 Depends-On
→ 此后 RigorBreeze 是交付事实源
→ 外部编排器只消费状态并调度，不另写需求结论
```

外部编排器的数据库只保存运行事实，例如 PID、租约、心跳、尝试次数、费用、暂停原因和恢复位置。业务合同、验收和质量证据仍属于 RigorBreeze、Git、CI 和真实环境。

## 五、外部高质量实践得出的共同结论

### 1. 官方研究

Anthropic 对跨多上下文长时间开发的研究发现，简单循环和自动压缩仍容易出现两个问题：试图一次完成过大范围，以及看到已有进度后过早宣布完成。有效做法是初始化环境、建立完整功能列表、每轮只推进一个功能、使用 Git 和进度文件交接，并让每轮结束时仓库保持干净。[Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

后续研究进一步证明：

- 上下文重置和结构化交接比只依赖 compaction 更适合长任务；
- 生成者与评估者分离，通常比让实现 Agent 自评更可靠；
- Planner 和 Evaluator 有明确价值，但每一层都要通过删减实验确认是否必要；
- 一个多小时系统即使有效，也可能昂贵、缓慢，必须测量收益。[Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)

OpenAI 当前提供适合编排的基础表面：`codex exec` 可以在脚本或 CI 中非交互运行，输出 JSONL、接受输出 Schema、设置沙箱并恢复指定 Session；Codex 也可以作为 MCP Server，被 Agents SDK 编排成可审查的单 Agent 或多 Agent 工作流。[Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)、[Codex with Agents SDK](https://learn.chatgpt.com/docs/mcp-server)

### 2. X 与 Reddit 实践信号

这些内容不是正式标准，但不同实践者反复遇到相同问题：

- Ralph 社区强调每轮新上下文、沙箱、计划/活动文件、Git、最大迭代数和浏览器反馈；没有这些条件，无限循环只会放大成本和错误。[Reddit: Most people are running Ralph wrong](https://www.reddit.com/r/ClaudeCode/comments/1qc4vg0/trust_me_bro_most_people_are_running_ralph_wiggum/)
- 实践者报告，即使循环能完成几十个任务，仍会把损坏结果自信地标为完成；确定性脚本应作为沙箱内 Agent 与外部世界之间的桥梁。[Reddit: The Ralph-Wiggum Loop](https://www.reddit.com/r/ClaudeCode/comments/1q9qjk4/the_ralphwiggum_loop/)
- X 上关于长期自主工程的讨论把问题归结为上下文退化、规划黏性和完成判断，需要契约监控与新鲜上下文的独立评估者。[systematicls](https://x.com/systematicls/status/2038241033755168959)、[Mihail Eric](https://x.com/mihail_eric/status/2032145866614849665)
- Mac mini 作为常开 Codex 主机已经有真实使用者，但实践建议仍然把 Git 设为事实源、主机视为可替换执行环境，并保留远程查看和接管能力。[Reddit: Remote Mac mini](https://www.reddit.com/r/codex/comments/1uylse8/dose_anyone_run_codex_in_a_desktop_and_remote_it/)、[Reddit: One project on multiple computers](https://www.reddit.com/r/codex/comments/1ulgmgj/best_way_to_work_on_1_project_on_multiple/)

这些信号支持同一个结论：真正的能力来自模型外部的 harness，而不是更强硬的一段“不要停止”提示词。

## 六、目标系统架构

```text
┌─────────────────────────────────────────────────────────────┐
│  1. Human Product Authority                                 │
│  产品目标、原型、不可变约束、预算、风险授权、最终验收       │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Goal Compiler / Planner                                 │
│  研究项目 → 补齐语义 → 里程碑 → 垂直切片 → 任务 DAG         │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Durable Orchestrator                                    │
│  队列、租约、心跳、调度、重试、预算、暂停、恢复、通知       │
└──────────────┬───────────────────────────────┬──────────────┘
               ▼                               ▼
┌──────────────────────────┐      ┌───────────────────────────┐
│ 4. Codex Workers         │      │ 5. Independent Evaluator │
│ 新鲜上下文、独立worktree │      │ 测试、浏览器、审查、探针  │
└──────────────┬───────────┘      └─────────────┬─────────────┘
               └──────────────────┬──────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  6. RigorBreeze Quality Control Plane                       │
│  合同、范围、风险、SDD/TDD、证据、新鲜度、验收和交付门禁   │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  7. Git / CI / Delivery                                    │
│  分支保护、Required Checks、制品摘要、灰度、监控、回滚     │
└─────────────────────────────────────────────────────────────┘
```

### 1. Human Product Authority

人是以下结论的唯一批准者：

- 产品目标和原型取舍；
- 业务事实源冲突；
- 视觉基线；
- 安全、隐私、法务例外；
- 破坏性迁移；
- 生产发布和不可逆操作；
- 超出已批准预算或范围的继续执行。

“以 CTO 标准执行”只能定义审查视角，不能替代事实或批准。

### 2. Goal Compiler / Planner

规划器把一个里程碑编译为可运行图。每个节点至少包含：

```text
taskId
observableOutcome
dependsOn
allowedScope
acceptanceIds
riskLane
verificationProfile
runtimeClaims
time/token/retry budget
humanGate
```

图只描述真正的依赖。普通独立任务不制造 DAG；复杂任务才建立分叉、汇合和集成节点。

### 3. Durable Orchestrator

编排器是未来新增的核心系统，但应与 RigorBreeze 分仓或至少分包。它负责：

- 从 RigorBreeze `status --all --json` 读取 ready/blocked/nextAction；
- 为 ready 节点建立 worktree、运行资源租约和执行预算；
- 启动 `codex exec --json` 或 Codex MCP/SDK Worker；
- 保存每轮事件、输出摘要、退出状态和资源消耗；
- 在进程异常、机器重启或网络中断后从最后安全检查点恢复；
- 识别无进展、重复失败、范围漂移和成本失控；
- 把需要人的问题转换成一个明确选择和唯一恢复入口；
- 绝不自行修改验收结论或放宽 RigorBreeze 门禁。

### 4. Codex Worker

一个 Worker 只处理一个可在单个上下文内完成的节点或一次修复假设：

```text
读取任务合同和必要上下文
→ 检查当前真实状态
→ 实现最小变化
→ 运行紧反馈验证
→ 留下结构化交接
→ 结束当前上下文
```

长时间运行不等于让一个 Session 无限增长。新鲜上下文应是默认边界；同一节点内需要连续诊断时，才使用 Session resume。

### 5. Independent Evaluator

验证顺序应遵循“确定性优先，模型判断在后”：

1. 格式、Lint、类型、单元、集成、契约和构建；
2. 安全、依赖、许可证、SBOM 和迁移检查；
3. Playwright、API 探针、截图、开发者工具和真机；
4. 独立新上下文 Agent 的标准审查与规格审查；
5. 人类对视觉、高风险业务和真实环境的最终验收。

实现 Agent 不得直接把自己的“看起来没问题”写成完成证据。

### 6. RigorBreeze Quality Control Plane

RigorBreeze 是系统中最重要的“不可欺骗合同层”：

- 一个节点一个任务合同和证据；
- 需求、范围和验收摘要改变后旧证据失效；
- 每个写任务独立 worktree；
- 风险决定验证深度和人工门禁；
- `Depends-On` 是项目内 DAG 事实；
- `Runtime-Claims` 防止端口、watcher 和开发者工具冲突；
- `nextAction` 是外部编排器的只读调度接口；
- commit、push、merge 和 release 权限继续分级。

RigorBreeze 不负责保持进程存活，也不保存模型聊天全文。

### 7. Git / CI / Delivery

Git 与远程 CI 提供外部不可变事实：

- 每次可接受增量对应明确 SHA；
- 任务分支禁止 force push；
- main 使用 Required Checks 和分支保护；
- Agent 先生成补丁或 PR，不直接获得生产凭证；
- 构建、测试、验收和发布引用同一 SHA/制品摘要；
- L2 发布保留功能开关、灰度、观察、告警和回滚。

OpenAI 官方的 CI 示例同样建议把 Codex 生成补丁与拥有仓库写权限的 PR Job 分开，减少密钥暴露和权限耦合。[Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)

## 七、Graph 与 Loop 的组合

### 1. Graph 负责全局正确顺序

```text
里程碑
├── A 数据和接口合同
├── B 后端实现（依赖 A）
├── C 管理端（依赖 A）
├── D 小程序（依赖 A）
└── E 集成验收（依赖 B、C、D）
```

Graph 决定：什么可以并行、什么必须等待、失败影响哪些节点、哪个集成节点负责共享文件。

### 2. Loop 负责单节点收敛

```text
观察状态
→ 提出一个可证伪假设或最小实现
→ 执行
→ 独立验证
→ 通过：关闭节点
→ 可恢复失败：带证据重试
→ 连续失败/预算耗尽：暂停并通知人
```

只有 Loop 会产生无限补丁；只有 Graph 又无法处理节点内部调试。因此目标系统必须是“Graph 管全局，Loop 管局部”。

### 3. 节点状态机

建议保持小而确定：

```text
proposed → approved → ready → leased → running
→ verifying → awaiting-human | passed | failed | blocked
→ integrated → closed
```

每次外部动作使用幂等键；恢复时先读取当前 Git、CI、进程和远端状态，再决定是否重放，禁止根据旧计划重复执行已经成功的动作。

## 八、Mac mini 运行架构

### 1. Mac mini 的正确定位

Mac mini 是常开执行主机和控制节点，不是生产服务器，也不应成为所有秘密的集中存储器。

它适合：

- 保持项目仓库、依赖缓存和本地构建环境；
- 运行编排器、Codex Worker 和本地验证；
- 承载必须使用 macOS 的构建或开发者工具；
- 通过 Codex Remote、SSH 或安全远程桌面接收人工批准。

Codex 官方 Remote 支持从移动设备或另一台桌面设备访问连接主机上的项目、聊天、文件、权限和工具，但远程访问是接管表面，不是耐久编排器。[Codex Remote connections](https://learn.chatgpt.com/docs/remote-connections)

### 2. 最小主机组件

| 组件 | 第一阶段选择 | 作用 |
|---|---|---|
| 开机与守护 | macOS `launchd` | 自动启动编排器、异常重启 |
| 运行数据库 | SQLite | 队列、租约、心跳、尝试和预算 |
| 执行接口 | `codex exec --json` | 简单、可解析、可设置沙箱和 Schema |
| 任务隔离 | Git worktree＋权限 Profile | 防止多个任务互相覆盖 |
| 质量治理 | RigorBreeze | 任务与交付事实源 |
| 外部验证 | GitHub Actions | 与本机结果相互独立 |
| 通知与接管 | Codex Remote＋消息通知 | 手机上查看、批准、暂停 |
| 秘密 | Keychain/专用秘密存储 | 不写入仓库、Prompt 和普通日志 |
| 日志 | JSONL＋轮转 | 运行轨迹、费用、错误和恢复依据 |

### 3. 沙箱与权限

- Worker 默认只有对应 worktree 的写权限。
- 网络使用 allowlist，不默认开放整个互联网和内网。
- 依赖安装与构建阶段不能继承长期 API 密钥。
- 项目代码、测试和依赖生命周期脚本均视为潜在不可信输入。
- 公共仓库 PR 不应直接运行在保存私人凭证的自托管主机。GitHub 同样警告，自托管 Runner 会扩大主机秘密和网络暴露面。[GitHub self-hosted runner security](https://docs.github.com/en/actions/reference/security/secure-use#hardening-for-self-hosted-runners)
- 微信开发者工具、真机、支付和真实厂商环境单独进入交互验收 Lane，不伪装成完全 headless。

## 九、技术选型：什么时候需要其他工具

### 1. 第一阶段不要上重型工作流引擎

单人、单项目、一次一个节点时，推荐：

```text
Python 控制器 + SQLite + launchd
+ codex exec --json
+ Git worktree
+ RigorBreeze
+ GitHub Actions
```

理由是状态规模小、可本地调试、没有集群运维成本，也不会过早建设平台。

### 2. 何时选择 LangGraph

当出现以下需求时再评估 LangGraph：

- 节点需要动态分支；
- 大量 Human-in-the-loop 中断与恢复；
- 需要每节点 checkpoint、回放和状态可视化；
- Planner、Builder、Evaluator 形成稳定图结构。

LangGraph 官方定位正是长时间、有状态 Agent 的低层编排运行时，提供 checkpoint、故障恢复和 Human-in-the-loop。[LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)、[LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)

### 3. 何时选择 Temporal

只有当工作流开始跨天、跨机器、并发多个项目，且必须保证活动重试、信号、定时器和崩溃恢复时，再评估 Temporal。它的 Durable Execution 能保存工作流状态，让天、周、月级流程从故障位置恢复，但对个人第一版明显偏重。[Temporal Durable Execution](https://temporal.io/)

### 4. 何时使用 Codex MCP/Agents SDK

第一版用 `codex exec --json`。当需要稳定的多 Agent handoff、统一 trace、线程继续和程序化审批时，再切换或补充：

```text
OpenAI Agents SDK
→ Codex MCP Server / app-server
→ Planner、Builder、Evaluator 专用 Agent
```

这属于执行与编排接口升级，不应改变 RigorBreeze 合同和门禁。

## 十、自动化权限模型

### 1. 自治等级

| 等级 | 能力 | 人类门禁 |
|---|---|---|
| A0 交互开发 | 每个任务人工发起 | 全程 |
| A1 单节点自治 | 自动实现、测试、修复 | 任务合同和验收 |
| A2 隔夜顺序执行 | 连续完成多个低风险节点 | 里程碑计划、异常和验收 |
| A3 DAG 并行 | 隔离 worktree 中并行节点 | 冲突、范围和集成 |
| A4 低风险连续交付 | 自动 commit、push、PR、Required Checks | merge策略和发布环境 |
| A5 受控生产操作 | 灰度、观察、可恢复步骤 | 生产发布、迁移和回滚仍需显式批准 |

目标应先达到稳定 A2，再考虑 A3/A4。不要从当前交互开发直接跳到生产无人值守。

### 2. 必须暂停的条件

- 需求或原型存在会改变结果的歧义；
- 需要扩大 Allowed Scope 或新增产品结果；
- 同一问题三个修复假设失败；
- 测试无法形成独立 Oracle；
- 任务超过时间、Token、费用或重试预算；
- 范围漂移、秘密、权限、依赖、迁移或安全门禁失败；
- 远端状态与本地计划不一致；
- worktree、端口、服务或开发者工具资源冲突；
- 需要视觉、安全、法务、生产或破坏性结论；
- 运行状态无法证明上一个外部动作成功还是失败。

暂停不是失败。对长时间自治系统而言，“停在安全位置并给出唯一恢复动作”本身就是成功能力。

## 十一、可靠性与观测指标

### 1. 第一版硬指标

| 指标 | 初始目标 |
|---|---|
| 越权写入 | 0 次 |
| 未经批准的生产/迁移/发布 | 0 次 |
| 崩溃或重启后的任务丢失 | 0 次 |
| 重复 commit/push/外部写 | 0 次 |
| 秘密写入日志或仓库 | 0 次 |
| 完成声明无新鲜验证 | 0 次 |
| 无限循环 | 0 次；所有节点必须有预算 |
| 状态无法解释 | 每个暂停都有原因、当前状态和唯一恢复入口 |

### 2. 效率指标

- 单节点无人干预完成率；
- 首次验收率；
- 每个成功节点的时间和费用；
- 无进展迭代数；
- 人工介入次数及原因；
- 误阻断与人工绕过；
- 修复后再次回归率；
- 并行带来的净节省与冲突成本；
- 相比人工分段 Prompt，是否真正降低返工和等待。

### 3. Harness 自身演进

每次运行产生两类循环：

```text
产品循环：目标 → 实现 → 验证 → 交付
Harness循环：运行轨迹 → 失败分类 → 回归场景 → 最小规则修改 → 再验证
```

只有误阻断、错误放行、错误 nextAction、人工绕过或显著伤害效率的事件进入演进候选。正确阻断只做统计，不能因为 Agent 不喜欢门禁就自动放宽。

## 十二、分阶段建设路线

### Phase 0：稳定当前 RigorBreeze

目标：继续用 v0.9.2 完成真实 L1/L2 切片，不新增长期编排代码。

完成条件：

- `status --all --json` 能准确支持跨 Session 接续；
- 任务合同、worktree、证据、归档和清理能够完整收口；
- 项目级 CI 和验证适配器可稳定运行。

### Phase 1：单节点隔夜 Runner

目标：在现有电脑上证明“一项已批准 L1 任务可以安全跑数小时”。

范围：

- Python＋SQLite＋`codex exec --json`；
- 一次只允许一个写节点；
- 新鲜上下文轮次；
- 最大轮次、时间和费用；
- crash resume、心跳、通知、停止；
- 不自动 merge、release 或生产操作。

验收：连续重放至少 10 个真实任务，零越权和零重复外部写。

### Phase 2：里程碑 Goal Compiler

目标：用户输入一次里程碑目标，系统研究项目并提出紧凑任务图。

范围：

- 从需求、原型和代码补齐可恢复事实；
- 生成垂直切片、依赖、范围、验收和预算；
- 人一次确认后转为 RigorBreeze 合同；
- 不保留第二套活动需求状态。

### Phase 3：DAG 与独立评估

目标：支持 2～3 个互不冲突 worktree 并行，并由独立 Evaluator 收口。

范围：

- ready 节点波次调度；
- 运行资源租约；
- 独立标准/规格评审；
- Playwright/API/设备适配器；
- 集成节点和基线失效传播。

### Phase 4：低风险连续交付

目标：L0/L1 节点通过门禁后自动 commit、push、创建 PR，并等待 Required Checks。

边界：

- main 保护；
- 禁止 force push；
- CI 与 Agent 凭证隔离；
- L2、迁移和生产发布仍暂停等待人。

### Phase 5：耐久运行平台

只有 Phase 1～4 的真实数据证明值得时才建设：

- 多项目队列；
- 跨机器 Worker；
- LangGraph 或 Temporal；
- Web/移动状态页；
- 更精细的模型、费用和并发路由；
- 受保护环境中的灰度和回滚演练。

## 十三、项目边界与仓库建议

未来建议保持三个清晰组件：

```text
rigorbreeze
└── 质量合同、状态投影、证据和交付门禁

rigorbreeze-runner（暂定名）
└── Mac mini 常驻编排、DAG/Loop、恢复、预算、通知

project repositories
└── 业务代码、测试、项目配置和真实 CI
```

若未来需要控制台，应是 Runner 的可选投影，不成为新的状态源。GSD Core 先作为设计来源；只有出现明确兼容需求时才做单向导入适配器。

## 十四、最终决策

### 1. 是否更多参考 GSD Core

**是，但参考其架构原则，不是把整个 GSD Core 塞进 RigorBreeze。**

优先吸收：新鲜上下文、阶段循环、薄编排器、文件化交接、依赖波次、plan checker、独立 verifier、自动 next action 和有界修复。

### 2. RigorBreeze 未来是否只是一环

**是，而且是最关键的一环之一。**

RigorBreeze 的职责不是让进程运行更久，而是确保运行越久也不能逐步偏离需求、范围、证据和权限。它应成为个人 AI 开发系统的质量控制平面。

### 3. 是否需要一套工具

**需要。** 目标系统至少包含：

```text
目标与计划
+ 持久化编排
+ Agent执行
+ RigorBreeze治理
+ 独立验证
+ Git/CI交付
+ 沙箱与权限
+ 监控、预算、通知和恢复
```

### 4. 现在最正确的下一步

不是继续修改 RigorBreeze，也不是立即购买硬件后开放无人值守权限。

最正确的顺序是：

1. 继续用当前 RigorBreeze 完成真实项目；
2. 在现有设备上做一个“单任务、单 worktree、有限预算、不碰生产”的隔夜 Runner 原型；
3. 用十个真实任务验证恢复、成本、质量和人工介入；
4. 证明有效后再将 Mac mini 作为常驻主机；
5. 稳定 A2 后再建设 DAG、并行和低风险自动交付。

这条路线既保留长期自主开发的目标，也避免为尚未被证明的问题建设一套臃肿平台。

## 十五、参考资料

### 官方与一手资料

- [GSD Core](https://github.com/open-gsd/gsd-core)
- [GSD Core Architecture](https://github.com/open-gsd/gsd-core/blob/next/docs/ARCHITECTURE.md)
- [GSD autonomous command](https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/autonomous.md)
- [GSD progress command](https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/progress.md)
- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Anthropic: Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- [OpenAI: Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
- [OpenAI: Use Codex with the Agents SDK](https://learn.chatgpt.com/docs/mcp-server)
- [OpenAI: Codex Remote connections](https://learn.chatgpt.com/docs/remote-connections)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Temporal Durable Execution](https://temporal.io/)
- [GitHub: Secure use of self-hosted runners](https://docs.github.com/en/actions/reference/security/secure-use#hardening-for-self-hosted-runners)
- [snarktank/Ralph](https://github.com/snarktank/ralph)

### 实践者信号

- [Reddit: Most people are running Ralph wrong](https://www.reddit.com/r/ClaudeCode/comments/1qc4vg0/trust_me_bro_most_people_are_running_ralph_wiggum/)
- [Reddit: The Ralph-Wiggum Loop](https://www.reddit.com/r/ClaudeCode/comments/1q9qjk4/the_ralphwiggum_loop/)
- [Reddit: Long-running Codex workflow](https://www.reddit.com/r/codex/comments/1ti1bdj/how_do_codex_users_make_longrunning_coding_work/)
- [Reddit: Remote Mac mini](https://www.reddit.com/r/codex/comments/1uylse8/dose_anyone_run_codex_in_a_desktop_and_remote_it/)
- [X: Long-running autonomous workflow contract stickiness](https://x.com/systematicls/status/2038241033755168959)
- [X: Takeaways on long-running autonomous coding agents](https://x.com/mihail_eric/status/2032145866614849665)

> 说明：实践者内容用于发现共性风险和候选模式，不作为产品能力、安全保证或架构正确性的唯一依据。
