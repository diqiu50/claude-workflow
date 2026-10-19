# Claude Workflow v0.1.2

Python 3.9+，Claude Code Plugin。三类 Hook、语义路由提示、开发/Review/调查流程、每会话本地状态、最小日志、六个回归场景、ETCR 评测和 Issue 模板。

## 本地加载

```sh
claude plugin validate /Users/ice/git/claude-workflow
claude --plugin-dir /Users/ice/git/claude-workflow
```

也可持久安装本地 marketplace：

```text
/plugin marketplace add /Users/ice/git/claude-workflow
/plugin install dynamic-workflow@workflow-local
```

开发加载每次启动传入 `--plugin-dir`；尚未发布 marketplace 或 GitHub 远程仓库。无需 pip/npm 依赖。适用于 macOS/Linux（状态锁使用 fcntl）；Windows 请使用 WSL。

Superpowers 为可选独立安装，参考 https://github.com/obra/superpowers 。本插件提示 Agent 复用其可用 skills，未复制源码，也不强制绑定未经验证的 marketplace 标识。

## 验证

```sh
python3 -m unittest discover -s tests -v
python3 tests/evaluator/etcr.py run.json --baseline baseline.json
```

ETCR = 同时满足验收、约束、无重大返工的任务数 / 总任务数。成本按有效观测计算并显示覆盖率。相同测试集、模型、fixture 和权限下比较；不把 Hook 测试通过率当作 Agent ETCR。场景与评测格式见 tests/cases/README.md。

## 状态与边界

项目 `.workflow/` 保存哈希会话 ID 的状态及锁；原子替换和每会话文件锁避免并发覆盖。任务历史保留最近 20 个类型/验证摘要，不保存原始提示或代码。`events.jsonl` 仅含版本、类型、复杂度、时长、验证结果与 unknown 用户反馈。不采集 Token、不自动上传。状态中有最多 2000 字符的 Agent 验证说明，勿填敏感内容。使用前把 `.workflow/` 加入目标项目的 .gitignore；结束会话后可手动删除目录。

路由关键词仅为候选，语义纠正由 Agent 负责；本地状态与 record 是 Agent 声明，不是不可篡改的安全边界。Review/调查阻止直接编辑；Bash、PowerShell、MCP 要求原生权限检查，不尝试用正则证明任意程序只读。开发模式不放宽 Claude Code 原有权限。所有可能有副作用的工具调用保守地使验证失效，包括只读 Bash；实际验证后用 record 登记结果。Stop 最多补充提醒一次，尊重 stop_hook_active；失败或无法验证可交付但必须披露。新用户消息建立新一轮任务并保留摘要。

CLI `python3 scripts/workflow.py --help`；`feedback` 仅输出 Issue 草稿，不提交。GitHub Issue 表单位于 .github/ISSUE_TEMPLATE。

## 规范来源

核对日期：2026-10-19，本机 Claude Code 2.1.303。
- https://code.claude.com/docs/en/plugins-reference
- https://code.claude.com/docs/en/hooks

采用默认 hooks/hooks.json 自动加载，manifest 不重复声明；UserPromptSubmit 输出 additionalContext，PreToolUse 使用 permissionDecision，Stop 使用 decision/reason 并处理 stop_hook_active。

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
