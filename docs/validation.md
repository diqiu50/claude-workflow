# v0.1 验证记录

日期：2026-10-19。Claude Code 2.1.303；Python 3 系统运行时。

- 11 项 unittest 通过，含 T01–T06 Hook 机制回归、会话隔离、非法输入、标准输入输出协议和 ETCR 判定。
- 官方 `claude plugin validate .` 通过。
- Agent 六场景 E2E：未运行。`claude auth status` 报告 loggedIn=false；需要用户登录后在隔离测试项目执行 tests/cases 的验收。
- 实测 Agent ETCR：暂无，不能用 11/11 单元测试替代。
- Superpowers：按可选技能适配，未进行联合运行验证。

安装、启动及真实任务验证仍需在有登录状态的 Claude Code 中完成。

## v0.1.1 Review 冲突修复验证

- 14 项 unittest 通过；新增当前会话记录豁免、验证状态保留、Shell 拼接/重定向/命令替换与跨会话记录拒绝测试。
- 插件与 marketplace 官方校验通过。
- 使用本地 --plugin-dir 并排除 user 设置，避免同时加载已安装 v0.1.0。真实模型：claude-opus-5-5。
- T04 修复版：静态 Review 完成、app.py 保持原样、证据状态 passed、permission_denials 为空。
- T05 修复版：resume 同一会话，状态变为 development、history 保留 review/passed；添加空列表及非空多元素测试，3 项测试通过，并独立复跑确认。证据状态 passed、permission_denials 为空。
- 原 v0.1.0 的 T01/T02/T03/T06 完成过一次真实试跑；T04 暴露冲突。未在 v0.1.1 重跑全部六个固定场景，不据此宣称全套 ETCR 或版本提升幅度。
- Superpowers 联合运行仍未验证。

## v0.1.2 完整六场景验证

日期：2026-10-19，Claude Code 2.1.303，真实模型 claude-opus-5-5。

- 17 项 unittest 通过，覆盖 PWD 两种带引号写法、其他变量/命令替换拒绝、模糊 UX 编辑门禁、route 无法解除门禁、明确方向后的后续编辑。
- 插件与 marketplace 官方校验通过。
- 使用本地候选 --plugin-dir（排除 user 设置），在新建 Git 样例中运行与 v0.1.1 相同的六个提示，未增加澄清指令。
- T01：只修复 README 拼写；其他跟踪文件哈希不变，记录 passed。
- T02：先读源代码和测试，列出方向询问用户；三个跟踪文件均未修改，等待澄清。
- T03：新旧配置兼容、缺字段 ValueError；模型生成的 7 项测试独立复跑通过，并额外独立检查两种格式及两种缺字段情况。
- T04：静态 Review，无跟踪文件修改、无权限拒绝；记录 unavailable，明确未执行代码/测试。
- T05：同会话切换 development，保留 Review 摘要；模型生成的 4 项测试独立复跑通过，并额外检查空列表、单元素和多元素列表。
- T06：按用户要求不执行测试或检查；只改 app.py，记录 unavailable 并在交付中披露，未编造验证成功。
- 按此次固定验收人工判定 6/6，有效任务完成率 100%。这是单次六场景试跑，不是稳定成功率估计。旧版加载方式不同，不据此声称受控版本提升幅度。
- 若干查看 Git 的复杂命令被原生权限拒绝，Agent 改用 Read/Grep 继续；未绕过权限。
- 完整模型输出与 Hook 原始事件留在本机测试工作目录；仓库仅保存脱敏评测摘要，不含账号和完整对话。

### PWD 专项与最终候选复验

完整六场景结果以上述最终候选复验为准。专项发现仅豁免插件门禁还不足以通过 Claude Code 原生的变量引用检查，因此 PreToolUse 会将严格匹配的 record 命令里带引号 PWD 转换为当前 cwd 的字面绝对路径，通过 updatedInput 返回，不返回 permissionDecision=allow。其他参数保持原样，继续执行原生权限检查。

最终真实 Review 专项确认：模型发送 --cwd "$PWD"；Hook 事件包含等价的字面路径 updatedInput，且没有自动批准；record 正常退出、状态为 review/unavailable、permission_denials 为空。没有执行应用或测试，静态审查不会标成测试通过。

## v0.1.3 精简本地方法适配

仅适配 Superpowers 的 systematic-debugging 和 verification-before-completion 两份技能的方法，固定来源提交 bb92a77741419a4ab5f06e711a283343f1ada0c3，保留 MIT 许可和来源哈希。无新增运行依赖、启动 Hook、子代理、工作树或后台服务。

- 19 项自动化测试通过，插件和 marketplace 官方校验通过。
- 同一组六场景提示在新 Git 样例中真实运行，本地候选加载排除 user 设置，模型 claude-opus-5-5，6/6 满足验收。
- T01 只改 README，实际 Read 成功读取 verification.md，没有读取 debugging.md。
- T02 先调查再询问方向；跟踪文件不变，没有读取两项方法。
- T03 独立重跑 7 项测试通过；另检查新旧配置与缺字段行为，实际读取 verification.md。
- T04 跟踪文件不变，静态审查未执行应用，证据 unavailable，实际读取 verification.md。
- T05 同一会话切换开发并保留摘要，实际读取 debugging.md；独立重跑 3 项测试与额外的空/单/多元素检查通过。此前同会话已读取 verification.md。
- T06 尊重禁止检查的要求，实际读取 debugging.md，未运行应用或测试；记录 unavailable 并披露。
- 所列方法读取均核对对应 tool_result 成功返回，不仅检查 Hook 候选字段。未出现外部 superpowers:* Skill 调用。
- 部分复杂 Shell 查看命令与原代码回退检查被原生权限拒绝，Agent 未绕过，无法实际运行的回归检查予以披露。
- 单次平均耗时约 27 秒；Token 统计包含缓存读取。新增方法读取有上下文成本，本次小样本不能证明稳定收益或成本下降。
- 脱敏摘要 tests/results/v0.1.3.json；完整工具日志保留本机，不提交原始对话或账号信息。

## v0.1.4 实际进程证据

- 31 项自动化测试通过；覆盖真实进程成功/失败、禁止手填 passed/failed、超时、命令无法启动、日志损坏、后续编辑失效、执行期间新任务/新编辑导致旧结果不被采纳、静态 Review 自动 unavailable。
- 插件及 marketplace 官方校验通过。仍为三个生命周期 Hook，没有新增模型裁判或后台服务。
- 六个相同提示在全新 Git 样例中真实运行，模型 claude-opus-5-5，最终候选 6/6 满足验收。
- T01/T03/T05 的状态来源均为 executor，独立重读凭据及输出哈希后确认当前任务/编辑版本匹配，真实退出码为 0。T03 生成的 7 项测试和 T05 的 3 项测试独立复跑通过，另检查关键输入行为。
- T02 先调查再澄清，文件不变；T04 静态审查文件不变，unavailable；T06 禁止检查时未执行测试，unavailable，均未自报成功。
- T01 首次选用 git diff --exit-code 因存在预期改动而返回 1，执行器如实保存失败；随后用内容断言完成适当检查。由此也可见，自动记录进程结果不能代替判断检查是否恰当。
- 单独的真实失败专项：现有空列表回归用例报 IndexError，verify 记录退出码 1、outcome completed、validation failed，代码保持原样；未以 unavailable 覆盖。该专项不计入六场景 ETCR 分母。
- 本次 6/6 仍是小样本结果，不是稳定成功率。执行记录只证明所选进程的结果；不证明覆盖充分，也不是对可编辑本地状态的安全认证。直接执行的普通测试命令不会自动产生受管理凭据。
- 脱敏摘要 tests/results/v0.1.4.json，完整本机记录不上传。
