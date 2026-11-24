# CS.RIN.RU 游戏资源搜索

[English](./README.md) | [简体中文](./README.zh-CN.md)

一个给 Agent 用的技能：在 [CS.RIN.RU](https://cs.rin.ru/forum)（Steam Underground）上找游戏，搜索论坛、读对帖子、给结果排序，再把下载下来的版本打补丁跑起来。

只给链接等于只做了一半。一份跑不起来的「干净 Steam 文件」不算资源，所以两段流程都收在这个技能里。

## 覆盖内容

- **站的访问模型** —— 顶替常规反爬的 401 Cookie 握手、匿名能看什么看不到什么、以及为什么带链接的答案必须登录态
- **真正可用的检索** —— phpBB 的查询参数、用 AppID 当关键词一次命中最新 Build 的技巧、按发帖时间排序、分页，以及反复搜会触发的限流
- **读帖** —— 两种帖子模板（游戏卡 / 上传帖）、Build 号抽取、帖子永久链接、引文与签名的坑、作者栏里带的注册时间与发帖量，以及站方渲染的两种链接状态
- **干净文件板块** —— `Steam Content Sharing`（`f=22`，只对登录用户可见）：主题结构、用 depot/manifest 证明 Build 的那一帖、标题格式、压缩包密码约定、分卷解压，以及 crack 到底在哪个板块
- **排序** —— 先看上传者自己的记录：用论坛的作者检索拿发帖总量与注册年限，再抽读一页看这些帖是资源还是闲聊，而不是从站点名字猜；然后是两个板块的 Build 新旧对比、资源类型和网盘质量，封禁网盘一票否决。SCS 是「纯度下限」而不是「新鲜度上限」：它靠志愿者更新，常常落后于主论坛用户自己发的版本
- **D 加密游戏** —— 为什么干净文件跑不起来、游戏帖里的 hypervisor 版本长什么样、AVX2 / VT-x 等硬件门槛、`VBS.cmd`、关掉 Windows 虚拟化安全后的代价与还原方法、Linux 方案，以及文件为什么绑定单一 Build 与单一游戏
- **自包含的答案** —— 每条候选自带版本、Build、下载/解压体积、内容、crack 或模拟器版本、解压密码、安装步骤与每条链接的判定；论坛链接只作为出处，不是让用户自己去翻
- **链接验活** —— 给出的每条候选都先验过：有效 / 失效 / 连浏览器也问不出来时才标未验证；答案永远带多条跨网盘、跨上传者的候选，因为这类链接死得快
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
- 任何以「拿到下载链接」收尾的任务都需要登录态。账号密码更可靠，登录会在 Agent 自己的网络上下文里建立会话；粘贴 Cookie 只在 Agent 与浏览器同一出口时有效
- 只有用到随附模板时才需要 Python 3.9+；模板仅用标准库，也不替你做任何决定

## 结构

```text
SKILL.md                            # 入口：三阶段流程与排序摘要
references/access-and-session.md    # 握手、登录表单、Cookie 形式、游客权限矩阵、故障对照表
references/search-recipes.md        # 查询参数、AppID 检索、排序、限流、回退方案
references/thread-and-post-format.md# 帖子模板、Build 号、分页、链接标签
references/source-ranking.md        # 上传者记录、Build 对比、资源类型、网盘质量、封禁名单
references/scs-and-clean-files.md   # f=22：主题、depot/manifest、密码、解压
references/denuvo-and-hypervisor.md # D 加密：hypervisor 版本、硬件门槛、安全代价
references/link-verification.md    # 三种判定、各主机行为、为什么不能只给一条
templates/check_links.py           # 验活脚本：按主机判定、仅标准库
references/patch-and-run.md         # Steamless、Unsteam、GBE Fork、uc-online2、Nemirtingas EOS
references/session-persistence.md   # Cookie 可存哪、怎么撤销
templates/csrin_session.py          # 可复制改写的客户端：握手、可选登录、取页、解析
```

## 风险提示

论坛是文件分享社区，链接指向第三方网盘，文件本身不归论坛所有。站方专门维护恶意站点名单，正因为从这些地方下载会中招：请开广告拦截、优先用站方推荐的网盘、下载后先扫描，并默认把任何「解压密码」和「专用下载器」提示当成可疑。

本技能不授予任何游戏授权。文件从哪来、当地法律如何看待，由使用者自己负责。
