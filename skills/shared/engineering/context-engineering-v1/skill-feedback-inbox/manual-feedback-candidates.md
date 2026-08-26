# Manual Skill Feedback Candidates

This file records manually selected feedback candidates before human review.

## 2026-07-24

### 事实三分法

来源项目：

- `D:\AIwork\PKPM-Agent`
- Codex 历史任务恢复排查
- Codex 配置路径迁移任务

观察到的问题或改进：

- 复杂项目里，官方说明、本机文件、真实运行结果经常不一致。
- 如果不先分层，AI 容易把“文档说支持”误判为“当前环境已经可用”。

真实证据：

- PKPM-Agent 任务中，官方手册、安装目录、宿主运行行为必须分开判断。
- AutoCAD 与 PKPM 联动中，CAD 链路已验证可用，但 PKPM 官方 Agent 授权和宿主绑定一度成为独立卡点。
- Codex 历史任务恢复排查中，左侧栏不可见不等于本地任务数据丢失，需要先查目录、日志、侧栏状态文件。

建议改动：

- 在 skill 中补一条轻量规则：遇到复杂系统时，先把事实分为“官方说法 / 本机文件 / 真实运行证据”。
- 每次结论都标注证据等级，避免把静态资料当成动态验证。

复用范围：

- skill-core

是否能简化流程：

- yes

是否能防止严重错误：

- yes

推荐结论：

- 修改 skill

### 有副作用必事务化

来源项目：

- `D:\AIwork\PKPM-Agent`
- CAD / PKPM 构件批量修改验证

观察到的问题或改进：

- 工程模型、图纸、配置一旦被写入，局部失败可能留下半修改状态。
- 只看工具返回成功不够，必须复读验证真实状态。

真实证据：

- `UpdateMemberSpecialPropertyBatch()` 在墙、斜杆、梁等构件上需要写前预检、写后复读、局部失败报告和自动回滚。
- 故障注入验证证明：如果第二个成员未按预期写入，工具应返回失败并恢复已写成员。
- AutoCAD 出图工具也需要保存后检查目标文件是否真实存在。

建议改动：

- 在 skill 中补一条规则：凡是会改模型、图纸、配置、数据库或远端状态的动作，默认需要预检、复读、失败报告和回滚策略。
- 轻量场景可以只做“写后复读 + 明确失败”，但不能只依赖返回码。

复用范围：

- skill-core

是否能简化流程：

- yes

是否能防止严重错误：

- yes

推荐结论：

- 修改 skill

### 主链路去 GUI 化

来源项目：

- `D:\AIwork\PKPM-Agent`
- AutoCAD 2024 + autocad-mcp File IPC 验证
- Codex 历史任务恢复排查

观察到的问题或改进：

- GUI 操作易受窗口状态、登录状态、授权弹窗、焦点、坐标和界面刷新影响。
- 复杂任务如果主链路依赖 GUI，稳定性和可复现性会很差。

真实证据：

- PKPM-Agent 任务中，官方 GUI Agent 授权异常后，切换到 `standalone_model` 后台桥接才完成 PKPM -> AutoCAD PoC。
- AutoCAD 侧通过 File IPC、`TRUSTEDPATHS`、dispatcher、预热脚本完成了更稳定的主链路。
- Codex 历史任务恢复排查中，不能只看左侧 UI，要查真实文件和日志。

建议改动：

- 在 skill 中补一条规则：GUI 优先作为观察、启动、兜底层；主链路应优先沉到脚本、文件协议、IPC、本地服务或 MCP。
- 如果必须用 GUI，先把它限定为最小操作面，并补可重复的预热/状态检查。

复用范围：

- skill-core

是否能简化流程：

- yes

是否能防止严重错误：

- yes

推荐结论：

- 修改 skill
