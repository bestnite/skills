# CS.RIN.RU 游戏资源搜索

[English](./README.md) | [简体中文](./README.zh-CN.md)

一个给 Agent 用的技能：在 [CS.RIN.RU](https://cs.rin.ru/forum)（Steam Underground）上找游戏，搜索论坛、读对帖子、给结果排序，再把下载下来的版本打补丁跑起来。

只给链接等于只做了一半。一份跑不起来的「干净 Steam 文件」不算资源，所以两段流程都收在这个技能里。

## 覆盖内容

- **站的访问模型** —— 顶替常规反爬的 401 Cookie 握手、匿名能看什么看不到什么、以及为什么带链接的答案必须登录态
- **真正可用的检索** —— phpBB 的查询参数、用 AppID 当关键词一次命中最新 Build 的技巧、按发帖时间排序、分页，以及反复搜会触发的限流
- **读帖** —— 两种帖子模板（游戏卡 / 上传帖）、Build 号抽取、帖子永久链接、引文与签名的坑，以及站方渲染的两种链接状态
- **排序** —— Clean Steam Files 优先于站方推荐直链站，再优先于知名上传者，最后才是散户上传；同档之内看网盘质量和 Build 新旧。规则建立在论坛自己维护的两份置顶信任名单上
- **打补丁** —— Steamless 去 Steam Stub、Unsteam 与 uc-online2 在线联机、GBE Fork 离线/局域网、Nemirtingas 接管 EOS，以及虚幻引擎双 exe 的坑
- **会话卫生** —— Cookie 允许存在哪、为什么粘贴的会话会在两次请求之间失效、以及怎么区分「没登录」和「没找到」

## 不覆盖内容

- **不代下。** 技能只返回链接并给出下载器建议，不负责拉取、解压、安装。
- **不碰账号。** 不注册、不找回密码、不规避封禁。登录态要么是用户给的 Cookie，要么是用户给的账号密码，原样使用。
- **不绕过登录墙。** 墙后的链接就留在墙后：能给什么就给什么，给不了就说给不了，不去猜 URL。
- **不碰封禁站点。** 论坛的不推荐站点名单与封禁网盘名单是硬约束，即使只剩这类链接也不展示。

## 安装

```bash
npx skills add https://git.nite07.com/nite/skills.git -g -s csrin-game-search
```

手动安装：把本目录复制进你的 Agent 读取技能的目录。

## 依赖

- 能访问 `cs.rin.ru`（直连域名不通时可用它的 onion 服务）
- 任何以「拿到下载链接」收尾的任务都需要登录态，由用户以 Cookie 或账号密码提供
- 只有用到随附模板时才需要 Python 3.9+；模板仅用标准库，也不替你做任何决定

## 结构

```text
SKILL.md                            # 入口：三阶段流程与排序摘要
references/access-and-session.md    # 握手、登录表单、Cookie 形式、游客权限矩阵、故障对照表
references/search-recipes.md        # 查询参数、AppID 检索、排序、限流、回退方案
references/thread-and-post-format.md# 帖子模板、Build 号、分页、链接标签
references/source-ranking.md        # 来源分级、网盘分级、站方信任名单、汇报格式
references/patch-and-run.md         # Steamless、Unsteam、GBE Fork、uc-online2、Nemirtingas EOS
references/session-persistence.md   # Cookie 可存哪、怎么撤销
templates/csrin_session.py          # 可复制改写的客户端：握手、可选登录、取页、解析
```

## 风险提示

论坛是文件分享社区，链接指向第三方网盘，文件本身不归论坛所有。站方专门维护恶意站点名单，正因为从这些地方下载会中招：请开广告拦截、优先用站方推荐的网盘、下载后先扫描，并默认把任何「解压密码」和「专用下载器」提示当成可疑。

本技能不授予任何游戏授权。文件从哪来、当地法律如何看待，由使用者自己负责。
