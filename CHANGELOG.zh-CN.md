# 变更记录

[English](CHANGELOG.md) · 简体中文

RigorBreeze 的重要变更都会记录在本文档中。

项目遵循[语义化版本](https://semver.org/lang/zh-CN/)。Public Preview 期间，如果真实项目证据表明现有合同不安全或带来不必要成本，次版本可能调整工作流接口。

## [Unreleased]

### 变更

- 在首次公开发布前，将项目、Skill ID、调用名、执行器、配置、Git 私有状态和任务分支前缀统一从 Codex Production Flow 更名为 RigorBreeze，不保留旧名兼容入口。

### 文档

- 使用双语引导、明确的安全边界和完整首次任务示例，重新组织面向首次使用者的仓库文档。
- 增加精简的贡献指南、安全策略和 MIT 许可证。
- 为全部用户文档和 Skill 参考文档建立中文版本及一致性检查。

## [0.8.0] - 状态收口与低摩擦落地

### 新增

- `workflowBaseline` 在真正基准分支证明受管安装，并提供一条精确、由用户单次授权的基线提交路径。
- `archive --outcome reconciled` 可以诚实关闭已由外部 Git 操作集成的历史任务，不伪造验证或验收。
- 正常 archive 保存不可变 `lastClosed` 交付上下文，使受保护的 commit、push 和 merge 能在任务关闭后完成。
- 未登记 worktree 清理要求绝对路径、基准分支、精确 HEAD、干净无活动状态和完整集成证明，并始终保留分支。

### 变更

- 主 worktree 与 linked worktree 状态统一迁入 Git 私有目录；旧状态只在可证明安全时迁移和删除。
- 安装状态会区分缺失与被修改的 runner 组件；生命周期优先报告已集成未关闭和关闭待提交，不再被过期基线建议覆盖。
- enforced L1/L2 不再接受只提交在任务分支上的工作流基线。
- L2 指南优先采用脱敏真实/厂商沙箱 fixture，并明确验证序列化、编码、数据库方言和业务前置条件。

## [0.7.0] - 真实开发闭环

### 新增

- 项目安装状态会展示 bundled Skill 版本、项目执行器版本、漂移状态和是否可安全升级；活动实施任务会阻止静默替换执行器。
- `archive --outcome abandoned --reason ...` 可以安全关闭被取消或替代的任务，不伪造验证成功，也不删除分支、worktree 或提交。
- 任务通过 `Runtime-Claims` 声明独占端口、进程、服务、应用和环境，并在所有活动 worktree 之间机器阻断冲突。
- L2 条件化集成通过 `Operational-Modes` 将启用、关闭和依赖不可用行为绑定到验收 ID。
- 机器 JSON `operation-plan` 与 `operation-result` 发布证据记录有序阶段、停止条件、当前安全状态和唯一恢复入口。
- 执行器漂移、旧任务占位、运行资源冲突、缺少发布计划和门禁失败会去重写入任务自己的实践事件，并进入现有复盘。

### 变更

- state 与 evidence schema 从 v3 升至 v4，同时保留历史 RED、验证、验收、发布、自动化和实践记录。
- enforced L1/L2 批准要求执行器、配置、辅助模块和 Spec 索引已经进入 Git 基线。
- Skill 协议要求在写产品代码前通过 bundled runner 查询状态、获得已批准任务合同并成功认领当前窗口。

### 安全

- RigorBreeze 不杀进程、不抢端口、不覆盖活动任务执行器、不删除废弃任务的 Git 引用，也不把操作快照扩张成常驻部署引擎。

## [0.6.1] - 受控 Worktree 生命周期

### 变更

- 当任务从已记录基线开始的每个提交都能在基准分支找到补丁等价提交时，将任务识别为已集成，从而安全覆盖 cherry-pick，同时不会把部分集成误判为完成。
- 为 `status --all --json` 增加向后兼容的 `cleanup` 投影，区分可清理、需保留和未登记 worktree，以及默认保留的本地任务分支。
- 在人类可读的项目状态中显示清理数量，让 Codex 能主动协调已完成的受管 worktree，不依赖用户记忆。

### 安全

- 清理仍要求 RigorBreeze 创建来源、准确创建路径、干净且非当前的 worktree，以及已经证明集成。
- 已成功创建或集成的任务分支继续保留，生命周期清理不会删除本地或远程引用；只有 worktree 初始化本身失败时，原子回滚才可能删除刚创建的分支。

## [0.6.0] - 内核边界与按需交付

### 变更

- 将策略执行器拆成一个稳定 CLI 入口，以及 state、policy、parallel 和 automation 职责模块；CLI、schema v3 evidence 模型和 Spec Tree 不变。
- 将 `manual` 重新定义为“没有长期无人值守授权”。用户当前消息明确要求时，可以单次授权受保护的 commit 或 push，且不修改项目配置。
- 在现有 `automate` 命令中增加单次 commit/push 参数。单次 push 必须明确 remote、当前分支和准确的 expected HEAD，要求远端可 fast-forward，并在完成后核对 SHA；不会 rebase 或 force push。
- 单次直推集成分支必须具备当前 full 验证、结构化验收和审查。

### 修复

- 自动 commit 后，如果日志中的 parent、tree、任务、evidence、验证和项目指纹仍表示同一不可变结果，则原验证继续有效。
- 任务在物理基准分支上执行时，允许从已记录 base SHA 向前推进，同时仍由完整变化集和 Allowed Scope 阻断范围外变化。

### 兼容性

- evidence schema 继续为 v3，automation journal 继续为 v1；新日志仅增加向后兼容的 `authorizationMode` 投影。
- 未增加公共命令、Spec 文件类型、状态系统、运行时依赖或长期权限。

## [0.5.2] - 真实使用安全收口

### 变更

- Allowed Scope 强制使用仓库相对路径、目录前缀或 glob，验收条件强制使用唯一且机器可读的 ID。
- 禁止首次批准或重新批准把已修改生产实现吸收到新的 RED 基线。回退生产变化后可以修订同一结果；新增结果或验收条件才建立依赖切片。
- L1/L2 RED 必须引用真实测试文件和合同中已声明的验收 ID，并由当前 full 验证闭合全部有效 TDD 链。
- verify、merge、archive 和可选 Git 自动化都会检查已提交与未提交变化的范围漂移。
- 范围 glob 使用路径语义，Git 状态使用 NUL 安全解析，工作流策略文件要求显式范围，并覆盖全部已提交变化类型。
- L2 full 根据风险以及依赖、迁移实际变化推导必需检查。

### 修复

- 在加载内置模块前禁用 Python bytecode，首次命令不再向业务项目写入 `__pycache__`。
- L1/L2 尚未建立 Git 工作流基线时由 doctor 提示，但不自动提交。

### 兼容性

- evidence schema 继续为 v3；`status --json` 只增加向后兼容的 `scope` 投影。
- 历史 evidence 继续可读，但旧版本执行器产生的验证对于 v0.5.2 门禁视为过期。

## [0.5.1] - Public Preview 基线

### 新增

- 最小 SDD 任务合同，以及与机器绑定的 TDD、验证、验收、制品和复盘证据。
- 项目声明式 advisory/enforced 检查 profile，以及 GitHub/GitLab CI 模板。
- 隔离并行 worktree、可选依赖 DAG、范围冲突检测和跨窗口状态恢复。
- 默认手动的 commit、push、受保护 merge 和 release 适配器，以及 Git 私有幂等记录。
- 具备来源证明的安全 worktree 协调，以及 schema v1/v2 到 v3 的证据迁移。

### 成熟度

- 这是首个 Public Preview 基线，不代表已经达到 production-ready。
- v1.0 仍要求完成真实 L1/L2 切片、并行与 DAG 使用、远程 CI 和受保护交付演练。
