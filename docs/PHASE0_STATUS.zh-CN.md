# RepoGC 当前状态

日期：2026-09-16

## 一句话

RepoGC 帮你找出仓库里值得整理的地方，保留证据，交给你和你的 AI 调查与决定。
默认检查当前状态，不预设新增模块，也不假设所有工作已经完成。
当前 CLI 提供机械观察；完整语义调查仍需要用户的 AI 或人工。

## 用户看到什么

```text
仓库
  -> 最多 5 张不同类型的审查卡
  -> 为什么值得看 / 有什么上下文 / 人该确认什么
```

主入口只有一个：

```sh
repogc review /path/to/repository
```

兼容宿主在打开 RepoGC 源码仓库并发现仓库内 skill 后，可调用 `repogc-review`。
Python 包安装不会将 skill 全局安装。也可以按[首次使用示例](first-review.md)
手工交接材料给已有 AI；RepoGC 不要求独立模型账号。

## 当前完成

- 正式名称 RepoGC；用户批准 Apache-2.0，许可证随源码和安装包分发；
- 确定性扫描：Markdown 断链与未替换的模板占位符（确定事实，全部列出，见[决策 0016](decisions/0016-narrow-first-release.md)）；孤立候选、未完成或过期状态、相似文档、Root 不可达（仅供人判断）；
- 最多五张、按问题类型去重的 review 页面；
- `Why / Context / Check` 三行人审结构；
- Typed Evidence Graph、活性证据、Git 背景、稳定 Finding ID 和正式基线；
- `RELIABLE / PARTIAL / UNRELIABLE` 运行可靠性边界和 17 个安全哨兵；
- Codex 只读取被选中的证据，上下文经独立 sidecar 校验后再显示；
- 本地测试、打包、自扫描和 Best Runtime Box 只读实测。
- [工程与评估路线](ENGINEERING_AND_EVALUATION.md)：可运行开发集、完整运行档案、
  独立 AI 内容评审及人类试验记录模板；模板不代表人类试验已执行。
  [本轮结果](evaluations/evaluation-foundation.md)记录测试、独立审查和未解决问题。

## 它明确不做什么

- 不删除、移动、改写或自动修复目标文件；
- 不把“没有静态引用”说成“没人使用”；
- 不推断运行时、外部系统、人工流程或业务价值；
- 不执行目标仓库的脚本、构建、测试、Hook 或包管理器；
- 不让 AI 改写机械 Finding、可靠性、趋势、Root 或基线。

因此，RepoGC 的结果是“值得确认的问题”，不是删除清单。

## 产品层与引擎层

长期方向见[北极星](NORTH_STAR.md)，规则与 Gate 实现状态见[宪法](CONSTITUTION.md)。
完整决定包、默认三个待回应事项的交互验证与动作授权接口仍需后续实现。
显式本地机械证据留存已可用，默认审查仍不自动归档。
以下描述当前运行行为，不表示 Gate 0–6 已全部通过。

产品层只有 `review`。`scan / explain / diff / annotate / doctor / baseline / verify-bundle`
属于审计和集成引擎，默认不要求普通用户理解。

机械报告仍使用 Schema 0.7。新的 review 页面使用独立 Schema 0.1，只聚合和
解释已有证据，不改变 Finding 语义，因此无需迁移机械报告。

## 真实项目结果

在 Best Runtime Box 的受控只读扫描中，565 条底层信号被压成 3 类审查卡：

1. 可能过期的状态记录；
2. 读者导航不清楚的完成清单或设计文档；
3. 示例中无法按当前基准目录解析的路径。

目标仓库原有工作区状态保持不变；没有执行其代码，也没有给出保留或删除结论。

## 仍欠缺

当前可准备公开实验版，但不是稳定的 v0.1。完整产品仍缺：

Git 读取已增加辅助程序防护；遇到内容过滤器时不读取工作区状态。
这不是通用沙箱；不需要 Git 背景时仍可关闭。见[安全说明](../SECURITY.md)。

1. 本地机械[证据包](evidence-bundle.md)已落地；完整决定包、AI 返回重验、
   独立人类事项与可追溯延后协议仍需完成；
2. 真实维护任务中对调查负担、纠正和重要遗漏的配对评估；
3. 公开实验版已推送至 cooleryu/RepoGc；首次提交的 Linux/macOS CI 与打包均通过，
   见[发布核验记录](evaluations/public-preview-preflight.md)；后续仍需持续验证；
4. 增加不同生态的真实仓库评估，初期优先可调查清楚的中小型仓库；
5. 明确发布与版本策略。

无人值守 AI API、自动修复、GitHub Action、SARIF 和 MCP 都不是当前主线；只有
真实需求出现时再单独决策。

## 事实源

- [名称与 Apache-2.0 决策](decisions/0009-name-and-license.md)
- [Review-first 决策](decisions/0008-review-first-product.md)
- [架构](architecture.md)
- [Finding 语义](findings.md)
- [隐私与本地执行](privacy.md)
- [Best Runtime Box review-first 评估](evaluations/review-first-best-runtime-box.md)
- [历史事故与回归](HISTORICAL_REGRESSIONS.zh-CN.md)

历史 Phase 文档继续保留用于审计，但不再作为新用户入口。
