# Discord User Operations

[English](./README.md) | [简体中文](./README.zh-CN.md)

Discord User Operations 是一个以普通用户身份在 Discord 上读取、搜索和写入的 skill。

## 功能

- 读取服务器、频道、论坛帖子与消息历史
- 按内容、作者、频道和日期范围搜索服务器消息
- 回复帖子，编辑和删除自己发送的消息
- 添加表情回应、读取置顶消息、处理私信（DM）
- 只通过已登录的浏览器会话工作：每次 API 调用都由真实浏览器发出，携带 Discord 期望的客户端身份
- 不提供直连 HTTP 路径——用复制出来的令牌从 shell 客户端调 API 会导致账号被风控
- 记录真正重要的 REST API 机制：认证、雪花 ID、限速与错误语义
- **不含任何脚本**：所有依赖环境的选择都写成让 agent 自己判断的决策

## 安装

```bash
npx skills add https://git.nite07.com/nite/skills.git -g -s discord-user-operations
```

## 依赖

- **一个浏览器会话**：一个你能驱动的浏览器工具，且能触达已登录的 Discord 会话——需要能导航、能执行 JS，并使用用户自己已登录的 profile，或有办法注入其存储的会话。有没有这样的工具，由 agent 看自己的 toolset 判断；没有时，[`references/browser-tool-setup.md`](./references/browser-tool-setup.md) 说明了怎么搭一个（CloakBrowser 内核挂在 Playwright MCP 后面，带上该路径需要的存储工具）——那是让你因地制宜的指导，不是让你去跑的脚本。**不支持任何 HTTP 客户端或「把令牌交给 shell」的变体**；原因见 [`references/account-safety.md`](./references/account-safety.md)。
- **认证**：要么在那个浏览器里直接登录——适合能显示二维码、出口看起来正常的主机；要么在登录界面不友好时（无头服务器、数据中心 IP、验证码）在你自己的浏览器里登录，再把 API 请求头里的令牌交给 agent。两种方式下，令牌都只在 `discord.com` 页面内使用；见 [`references/token-handoff.md`](./references/token-handoff.md)。
- **在两次运行之间保留会话**：浏览器有持久 profile 时由它保留。没有时，agent 先征得一次同意，再把会话存到本技能目录下的 `.state/`（git 忽略、文件权限 `0600`），下次从那里恢复——见 [`references/session-persistence.md`](./references/session-persistence.md)。会话数据不会写到别处。

## 适用场景

适合在这些场景中使用：

- 以自己的身份浏览 Discord 服务器和论坛帖子
- 读取频道历史，或搜索特定消息
- 回复某个帖子，或修改自己发过的内容
- 添加表情回应、查看置顶消息，或处理私信
- 通过自己的账号处理小规模、个人向的 Discord 任务

## 使用方式

1. 先解决认证：在 agent 的浏览器里登录，或者从你自己浏览器的 Network 面板取出令牌交给 agent（不要通过聊天发送）。
2. 提供一个目标：
   - 一个服务器、频道或帖子
   - 一条要回复或编辑的消息
3. 说明你的目标：
   - 读取或搜索
   - 拟好的回复或编辑
   - 表情回应、置顶查询或私信
4. 任何他人可见的内容，发送前先审阅具体文案。
5. 写入完成后重新读取目标，验证结果。

## 示例请求

```text
读取这个频道的最新消息并总结。

搜索这个服务器最近一周关于上线的消息。

帮我拟一条回复，我确认后发到这个帖子里。

把我最后一条消息的措辞改一下。
```

## 说明

- 面向个人、低频、以读取为主的使用方式，不适合批量操作或自动化外联。
- 使用用户令牌进行自动化处于 Discord 服务条款的灰色地带，请保持克制。
- 不要用脚本或 shell 客户端直接调 API。这条路并不「更快」：它缺少浏览器的客户端身份，会让账号被警告、被强制重置密码锁住，甚至更糟。浏览器会话是唯一受支持的传输方式。
- 任何他人可见的内容，发送前必须获得明确确认。
- 把令牌当作密码：不要粘贴到聊天、日志或提交中。
- 删除 `.state/` 不会让已保存的会话失效；要作废它，在 Discord 里退出该会话。重装技能可能删掉 `.state/`，届时需要重新登录。

## 致谢

REST 接口目录参考自 [olivier-motium/discord-user-mcp](https://github.com/olivier-motium/discord-user-mcp)（MIT）。

## 许可证

MIT
