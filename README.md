# Claude Workflow v0.1.8

Python 3.9+，Claude Code Plugin。三类 Hook、语义路由提示、开发/Review/调查流程、每会话本地状态、最小日志、六个回归场景、ETCR 评测和 Issue 模板。

## 安装与本地开发

```sh
claude plugin marketplace add diqiu50/claude-workflow
claude plugin install dynamic-workflow@workflow-local
```

开发时可从本地仓库单次加载：

```sh
claude plugin validate /path/to/claude-workflow
claude --plugin-dir /path/to/claude-workflow
```

无需 pip/npm 或 Superpowers 插件依赖。适用于 macOS/Linux（状态锁使用 fcntl）；Windows 请使用 WSL。

## 精简的方法复用

只引入两份本地、按需读取的方法文档：

| 场景 | 本地方法 | 主要内容 |
|---|---|---|
| Bug 排查及修复 | skills/workflow-router/references/debugging.md | 先证据与根因，再单一假设、最小修复和回归 |
| 交付或登记验证前 | skills/workflow-router/references/verification.md | 看实际输出，区分通过、失败、未验证；按改动规模选择检查 |

它们是 Superpowers 对应技能的精简适配，不是原版技能完整搬运。Hook 给出候选文档路径，Agent 在需要时读取；拼写修复跳过调试方法，宽泛需求等待澄清时不必加载这两份文档。不新增启动 Hook、Skill 服务、工作树管理、子代理、外部 Memory 或后台上传。用户限制和原有权限门禁仍适用。

来源固定到上游提交，保留原作者版权和 MIT 许可证。见 third_party/superpowers/NOTICE.md、LICENSE 与 upstream.json。后续升级参考方法需显式修改并回归，不会自动跟随上游变化。

## 验证

```sh
python3 -m unittest discover -s tests -v
python3 tests/evaluator/etcr.py run.json --baseline baseline.json
```

ETCR = 同时满足验收、约束、无重大返工的任务数 / 总任务数。成本按有效观测计算并显示覆盖率。相同测试集、模型、fixture 和权限下比较；不把 Hook 测试通过率当作 Agent ETCR。场景与评测格式见 tests/cases/README.md。

## 状态与边界

项目 `.claude/.workflow/` 保存哈希会话 ID 的状态及锁；目录不存在时自动创建，原子替换和每会话文件锁避免并发覆盖。任务历史保留最近 20 个类型/验证摘要，不保存原始提示或代码。`events.jsonl` 仅含版本、类型、复杂度、时长、验证结果与 unknown 用户反馈。不采集 Token、不自动上传。状态中有最多 2000 字符的验证摘要或未验证原因。verify 另外在 `.claude/.workflow/verification/` 保存所选命令、实际退出码、运行时间和每路最多 64 KiB 的 stdout/stderr 尾部，可能包含私有数据；不会自动上传。使用前把 `.claude/.workflow/` 加入目标项目的 .gitignore；结束会话后可手动删除目录。旧的项目根目录 `.workflow/` 不再读写，也不会自动迁移；需要保留已有会话时，可在停止相关会话后将其移至 `.claude/.workflow/`。

路由关键词仅为候选，语义纠正由 Agent 负责。根据任务选择检查方式，不要求每次都运行命令；直接运行的测试结果也可作为交付依据。`verify` 和 `record` 是可选的本地记录工具，缺少记录不会阻止结束，也不需要为了结束而补跑检查或补记 unavailable。未执行检查不能声称检查通过，实际失败和重要限制应如实说明。

选择使用 `verify` 时，插件从实际进程结果登记 passed/failed，Stop 核对凭据、输出哈希与任务/编辑版本后写日志；缺失、过期或损坏的记录记为 unknown，不拦截结束。`record` 仅允许声明 unavailable。可能有副作用的工具调用仍保守地使可选凭据失效，包括只读 Bash，但不要求补跑。本地文件仍不是不可篡改的安全边界。Review/调查阻止直接编辑；Bash、PowerShell、MCP 沿用 Claude Code 原生权限判断，插件不额外要求逐次确认，也不自动批准命令。插件不通过解析任意命令来保证只读，Agent 仍须遵守只读任务范围。新用户消息建立新一轮任务并保留摘要。

CLI `python3 scripts/workflow.py --help`；`feedback` 仅输出 Issue 草稿，不提交。GitHub Issue 表单位于 .github/ISSUE_TEMPLATE。

## 规范来源

核对日期：2026-10-19，本机 Claude Code 2.1.303。
- https://code.claude.com/docs/en/plugins-reference
- https://code.claude.com/docs/en/hooks

采用默认 hooks/hooks.json 自动加载，manifest 不重复声明；UserPromptSubmit 输出 additionalContext，PreToolUse 使用 permissionDecision，Stop 仅核对可选执行记录并保存摘要，不要求继续验证。

## v0.1.1 修复

Review/调查模式下，严格匹配本插件脚本、当前项目和会话的独立 `record` 命令不再触发只读门禁，也不再使已有验证失效。原生 Claude Code 权限仍适用；拼接命令、重定向、命令替换及其他会话的记录不在豁免范围内。Hook 提供实际 CLI 绝对路径，避免依赖模型工具环境中的 CLAUDE_PLUGIN_ROOT。否定表达“不要修改”不再误触发开发候选。

## v0.1.2 修复与回归

- 本地 `record` 支持 `--cwd "$PWD"` 和 `--cwd "${PWD}"`，只匹配当前项目、当前会话和插件脚本。Hook 将这两种当前目录写法转换为字面绝对路径，再交回原生权限检查，不自动批准。其他环境变量、命令替换、拼接及重定向仍不豁免；原生权限保持有效。
- 宽泛的体验优化请求先调查再询问方向；等待用户明确方向时，直接编辑被阻止，Shell/外部工具仍需原生权限检查。具体范围明确的请求不触发这项门禁。该候选规则只覆盖常见中英文 UX 请求，不代替 Agent 对所有歧义的语义判断。

运行六个真实 Claude Code 场景（需要登录，会使用账号额度）：

```sh
python3 tests/e2e/run.py --output /tmp/workflow-e2e-new --plugin-dir "$PWD"
```

输出目录必须是新的。省略 `--plugin-dir` 可检查当前用户已安装的插件；传入时排除 user 设置以避免同时加载旧版。每个样例有独立 Git 基线，T05 续接 T04 会话。脚本保存模型输出、Hook 事件、状态和文件哈希；验收仍需核对语义、文件变化与独立测试，不能仅用进程返回码判定成功。脱敏评测结果见 `tests/results/v0.1.2.json`。

## v0.1.3 验证

19 项自动化测试、官方配置校验和六个真实场景通过。日志确认两份本地方法实际读取成功，未调用外部 Superpowers 技能。结果见 tests/results/v0.1.3.json 和 docs/validation.md。6/6 是单次小样本结果，不能视为所有任务的稳定成功率。

## v0.1.4 实际执行验证（历史行为，v0.1.6 起记录可选）

```sh
python3 /path/to/plugin/scripts/workflow.py verify --cwd /path/to/project --session SESSION -- python3 -m unittest -v test_app
```

使用 Hook 给出的实际脚本路径和会话 ID。CLI 实际启动检查进程，保存退出码与有限输出；Stop Hook 核对该次任务/编辑版本及凭据，成功才登记 passed。非零退出为 failed；超时为 failed；无法启动或被中断为 unavailable。后续可能修改文件的工具调用使结果失效，执行期间发生新修改/新任务的结果不会被采纳。

`record --status passed` 和 `record --status failed` 已移除；`record --status unavailable --evidence "原因"` 用于禁止/无法执行的情况，不能覆盖当前已有的实际失败。未执行受管理检查的静态 Review/调查，在 Stop 自动记 unavailable。普通直接运行的 pytest/unittest 不会自动生成凭据，也不会仅凭文字输出登记成功。

passed 只代表选定命令正常结束，不代表检查选得正确、覆盖充分或所有需求均满足。原生权限仍有效，verify 不自动批准，也不使 Review 获得写入许可。详细接口与证据格式见 docs/verification-executor.md。

## v0.1.5 Stop 提示与恢复（历史行为，v0.1.6 已移除拦截）

Claude Code 可能把 Stop 返回的 `decision: block` 显示为 “Stop hook error”。这不一定是脚本异常：本插件在缺少有效执行凭据时会主动请求继续验证。v0.1.5 的提示明确标识 completion guard，绑定当前脚本路径、项目和会话 ID，不再输出 `<project>`/`<session>` 占位符；提供可追加实际检查命令的 verify 前缀以及完整的 unavailable 记录命令。

同一任务版本只提醒一次，即使客户端再次发送 Stop 且未设置 stop_hook_active 也不会反复拦截。发生新的潜在修改后可再次提醒。提示会说明后续 Bash 等操作使已有凭据失效的情况；这仍是保守策略，查看 git status 也可能使验证失效。直接跑过普通测试但没有受管理凭据时，不要仅为消除提示而重复测试；可以如实披露未登记的结果并记录 unavailable。没有取消真实进程证据要求，也不会自动伪造 passed。

## v0.1.6 移除强制验证

移除缺少验证记录时的 Stop 拦截及恢复命令提示。没有运行检查、直接运行测试、检查记录失效或损坏，都可以正常结束任务；插件不会据此把结果登记为通过。启动提示和本地方法文档同步取消必须使用 `verify` 或补记 `unavailable` 的要求。

`verify` 保留为可选的结果记录工具；`record` 保留为可选的说明记录工具，成功时显示“已记录检查说明”，已有实际结果时说明保留的状态。正常结束不再因缺少记录触发本插件的 “Stop hook error”；真实脚本异常仍会报错。可用 `claude --plugin-dir /path/to/claude-workflow` 在新会话加载本地改动；已安装缓存需更新插件后生效。

## v0.1.7 移除重复权限确认

Review、调查和等待澄清时，不再对每一条 Bash、PowerShell、MCP 调用返回 `permissionDecision: ask`。代码搜索、管道和多条查询命令交给 Claude Code 原生权限系统判断，插件不额外弹窗，也不返回 `allow` 跳过权限检查；原生规则、其他 Hook 或工具自身仍可能要求确认。只读模式下对 Write/Edit 等直接编辑工具的限制保留；Shell/MCP 的只读要求由 Agent 遵守，并受原生权限规则约束。

## v0.1.8 调整状态目录

状态、锁、事件日志和验证产物统一保存到项目 `.claude/.workflow/`，目录不存在时自动创建。测试、端到端脚本和忽略规则同步更新。旧 `.workflow/` 不再读写，也不会自动迁移；如需保留已有会话，请在停止相关会话后将其移至新目录。

更新并重启 Claude Code 后生效：

```sh
claude plugin marketplace update workflow-local
claude plugin update dynamic-workflow@workflow-local
```
