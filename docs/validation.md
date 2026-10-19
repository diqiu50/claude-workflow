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
