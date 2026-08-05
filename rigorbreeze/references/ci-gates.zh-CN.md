# CI 门禁接入

[English](ci-gates.md) · 简体中文

## 原则

策略保存在 `scripts/rigorbreeze.py` 和 `rigorbreeze.toml`，本地和 CI 调用同一个执行器。CI YAML 只编排任务，不能成为第二份工作流规格。

## 最小流水线

```text
doctor
→ `--mode enforced verify --profile full`
  → 项目声明的静态与行为检查
  → 适用的安全与供应链检查
  → 适用的迁移检查
  → 配置的构建与运行检查
→ `check merge` 或受保护的 `check release`
```

enforced profile 包含项目为该 profile 声明的检查，每项都必须配置并通过。L0/L1 继续由项目声明。L2 的 `full` 至少推导 `secret`、`build`、一项静态质量检查和一项行为检查；修改依赖清单时额外要求 `dependency`、`license`、`sbom` 及非空报告，修改迁移时要求 `migration` 及报告。浏览器 UI 等无关能力仍按条件启用，不要求填写 `N/A`。必需检查失败会阻断合并和发布。

## GitLab

把 `assets/ci/gitlab-ci.yml` 调整后接入已有 `.gitlab-ci.yml`。真实项目命令配置在 `rigorbreeze.toml`；YAML 直接调用策略执行器，不保留第二套命令表。保存证据、报告、截图、迁移日志、SBOM 和制品摘要。

使用受保护分支和环境、Required Pipeline、环境级秘密和生产人工批准。凭证不能写入 YAML。

## GitHub Actions

把 `assets/ci/github-actions.yml` 调整为 `.github/workflows/production-flow.yml`。把 full-profile Job 设为 Required Check，禁止直接推送 main，并通过环境保护要求生产人工批准。使用 OIDC 或仓库/环境 Secrets，不嵌入 Token。

## 制品身份

构建一次并提升同一不可变制品。结构化验收和发布记录自动绑定当前制品 SHA-256。记录 Git SHA、依赖锁摘要、配置版本、迁移集合、镜像/包摘要、CI Run 和发布观察。为生产重新构建另一份制品会破坏证据链。

L2 远程交付的 `check release` 还要求当前机器 JSON `operation-plan`，其中绑定目标环境、Git SHA、制品摘要、有序的备份/配置冻结/迁移/部署/验收/切换/观察阶段、每步成功条件、停止条件、安全恢复点和回滚限制。执行后保存 `operation-result`；暂停或失败时只有一个安全状态描述和一个恢复入口。CI 仍是门禁与制品载体，不是常驻部署状态机。

## 强制边界

本地默认 advisory。本地 Hook 可以提醒但不是权威；远程 Required Checks 和受保护环境才是不可绕过的合并/发布边界。

首个 enforced L1/L2 批准前，配置的真正基准分支必须满足 `workflowBaseline.status=current`；任务分支中的 runner 提交不能替代项目基线。用户一次性明确授权后，`automate commit --once --workflow-baseline --expected-head <sha>` 只能在基准 worktree 无活动任务、无无关改动、无缓存和秘密材料时建立或更新该基线。

`[automation].level` 是显式项目授权边界：

- `manual`：不授予无人值守 Git 写权限；用户当前消息明确要求时可单次授权受保护的 commit 或 push，且不修改长期等级；
- `commit` 和 `push`：限制在任务范围与 `rigorbreeze/<task-id>`；
- `merge`：必须调用配置的 provider Required Check 和 auto-merge 适配器；
- `release`：必须调用配置的 provider/environment 检查和 release 适配器。

核心不会通过本地合并绕过分支保护，不会 force push，不保存 provider 凭证，也不会把 commit/push 权限当作生产迁移或回滚权限。Provider 和 release 适配器使用 argv 数组，并从 Git、CI、OIDC 或平台环境继承凭证。

单次 push 必须明确 remote、当前分支和准确的 expected HEAD。它先 fetch 目标，远端领先或历史分叉时阻断，并在完成后核对远端 SHA。直推集成分支还必须具备当前 full 验证、结构化验收和审查。单次授权不延伸到 merge、release、迁移或回滚。

可选 advisory Hook 位于 `assets/hooks/`。把它们复制到项目自己的 Hook 目录，并显式启用该目录；初始化不会修改 Git 配置。
