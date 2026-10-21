# xianyu-operations

[English](./README.md) | [简体中文](./README.zh-CN.md)

给 AI agent 用的闲鱼（Xianyu / Goofish）操作：关键词搜索、商品详情、自己的商品列表、消息会话列表，以及发布/下架商品与发送消息（写操作，须用户逐次同意）。

闲鱼没有开放 API，也没有 OAuth 注册，所以访问凭据是一个登录态的浏览器会话。**所有请求都由浏览器发出**——搜索页从渲染后的 DOM 里读，其余结构化接口用页面内的 `fetch()` 调用。从 agent 本机直接用 HTTP 客户端调接口**不是**受支持的通道：它能连着跑十来次，然后触发阿里的风控（`RGV587`），表面上像是会话失效。签名仍然在本机算；只有"发送"这一步归浏览器。

## 安装

```bash
npx skills add https://git.nite07.com/nite/skills.git -g -s xianyu-operations
```

或直接把目录拷进你的 agent skills 目录。

## 目录里有什么

三个模板加五份参考文档：

| 文件 | 作用 |
|---|---|
| `templates/mtop_request.py` | 可复制改造的片段：给 mtop 请求签名，并打印出应在页面里执行的 `fetch()` 调用。**只用标准库**，完全不联网 |
| `templates/publish_item.py` | 发布商品的载荷组装（图片、价格、运费、类目、地址） |
| `templates/im_send_message.py` | 通过 WebSocket 网关发消息：整套 LWP 帧序列（需要 `websockets`） |
| `references/mtop-apis.md` | 已验证的接口、入参、字段路径、错误码、页面内 `fetch()` 写法、风控说明 |
| `references/browser-search.md` | 搜索提取器与浏览器操作步骤（纯文本） |
| `references/write-operations.md` | 发布 / 下架 / 发消息的配方，以及约束写操作的规则 |
| `references/browser-tool-setup.md` | 本机没有浏览器工具时怎么搭一个 |
| `references/session-persistence.md` | 会话在两次运行之间存在哪：优先用浏览器自己的持久 profile，否则存到本技能目录下的 `.state/` |
| `.gitignore` | 忽略 `.state/`——技能写入会话数据的唯一位置 |

代码刻意做窄，而且是模板而非成品工具：它只算那件必须逐字节准确的事，同时把"会话放在哪、驱动哪个浏览器、失败怎么重试"留给你改。依赖环境、依赖判断的部分全部留在文档里，让 agent 能因地制宜，而不是等技能去适配自己的环境。

## 依赖

- Python 3（任意较新版本）。不需要任何第三方包：不需要 `requests`，也不需要 `playwright`。
- 一个已登录的闲鱼会话（`unb` 与 `_m_h5_tk` 必填），装进浏览器工具里。浏览器有持久 profile 时由它保留会话；没有时，agent 先征得一次同意，再把会话存到本技能目录下的 `.state/storage-state.json`，下次从那里恢复。
- 一个具备三项能力的浏览器工具：导航并读取渲染后的 DOM、在页面里执行 JS、注入 cookie（方式不限——cookie API、storage-state 文件、CDP，或用户已登录的 profile）。若环境里没有，按 `references/browser-tool-setup.md` 搭一个。

## 用法

```bash
cp templates/mtop_request.py ./mtop_request.py
$EDITOR mtop_request.py     # 三处标记：会话来源、api/入参、fetch 形式
python3 mtop_request.py
```

它会打印签名后的 URL、form body，以及一段可直接执行的 `fetch()` 片段。把这段片段放到已打开 `www.goofish.com` 的页面里跑，由浏览器发出请求并取回 JSON。响应结构看 `references/mtop-apis.md`——商品数据在 `data.itemDO` 下。

关键词搜索同样走浏览器：照 `references/browser-search.md` 走，提取器与步骤都在那份文档里。

## 写操作

发布商品、下架商品、发送消息都已支持，但受三条规则约束：**具体内容先经用户同意**、写操作节奏约每分钟一次、每次写完都要回读验证（`SUCCESS` 只代表服务端收下了，不代表已生效）。不做批量操作，也不做自动化外联——那才是账号被限制的原因。

## 安全

保存下来的会话等同于一个活着的账号会话。技能只把它写进自己目录下的 `.state/`（git 忽略、文件权限 `0600`），不进聊天记录，也不贴进对话。重装技能可能删掉 `.state/`，届时需要重新登录。删除 `.state/` 并不会让会话失效；要作废它，用闲鱼 App 里的"退出所有设备"。

## 说明

非官方：它说的是 Web 客户端内部接口，随时可能变。2026-09 对着真实响应验证过一次；请求形状、字段路径与已知响应码记录在 [`references/mtop-apis.md`](./references/mtop-apis.md)。
