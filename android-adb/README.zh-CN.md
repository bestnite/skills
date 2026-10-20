# Android ADB

[English](./README.md) | [简体中文](./README.zh-CN.md)

在主机终端上操作 Android 设备的一份手册：USB / 模拟器 / 无线调试接入，注入触控与文本，改应用和系统状态，读日志，抓取产物，跑能「真的红」的 instrumentation 测试。只用原生 `adb` / `am` / `pm` / `cmd` / `logcat`——没有包装 CLI，没有 MCP 服务，也不用装脚本。

**仓库地址**：https://git.nite07.com/nite/skills（子目录 `android-adb/`）

## 功能

- **无线调试全流程**——`adb pair` / `adb connect`、mDNS 发现、配对端口为什么不是调试端口、配对成功却不见设备该查什么，以及 mDNS 后端随版本变迁的边界。
- **稳定接入**——设备选择器、`wait-for-*` 与「系统真的启动完成」的区别、九种设备状态及各自的恢复动作、RSA 授权、Linux udev 规则、模拟器启动竞态。
- **驱动界面**——点击、滑动、长按、按键、文本输入、分辨率与密度覆盖、系统设置、带类型 extras 的启动，以及用来替代已失效 `svc` 的 `cmd <service>`。
- **看清发生了什么**——logcat 各 buffer、过滤、格式、按 PID 取流、失败时刻的取证顺序。
- **搬字节**——截图、录屏、pull/push、经 `run-as` 取应用私有文件、测试产物该落在哪。
- **测试与 CI**——绕开 Gradle 直接 `am instrument`、分片、Orchestrator 隔离，以及一个不会「测试挂了却绿」的门禁。
- **常见技能包缺失的部分**——`uiautomator` UI 树 dump、bug report、ANR 证据链、Doze/App Standby 测试、`cmd testharness enable`、输入法切换，以及锁屏这件事能做到哪、做不到哪。

## 安装

```bash
# 只装这个技能
npx skills add https://git.nite07.com/nite/skills.git -g -s android-adb
```

手动安装：把整个目录（`SKILL.md`、`references/`、两份 README）复制到你的 agent 读取技能的位置。这个位置由你的环境决定，查你所用 agent 的文档，不要照抄某个路径。

## 适用场景

- 手机/平板要用 Wi-Fi 连 adb，并且希望重启、换网之后还能连上；
- 需要从主机脚本操作设备：点击、输入、启动、改开关、唤醒屏幕；
- 想弄清一次 flaky 到底为什么失败，而不是重跑到绿为止；
- 要把日志、截图或录屏整理成可提交的证据；
- 直接跑 instrumentation、按设备分片，或让 CI 在测试失败时真的失败。

不适用：fastboot / 刷机、应用实现、以及在设备上写测试代码（Espresso、Compose test、UiAutomator 库）。

## 目录结构

```text
SKILL.md                              入口：硬规则、工作流、症状对照表
references/
  connection.md                       传输与选择器、状态机、无线配对
  server-and-architecture.md          client/server/daemon、生命周期、环境变量、密钥
  apps.md                             安装参数、split APK、pm、复位语义
  input-and-state.md                  input、wm、settings、am、cmd、干净环境搭建
  observability.md                    logcat buffer、过滤、格式、取证
  capture-and-transfer.md             screencap、screenrecord、pull/push、run-as、TestStorage
  instrumented-tests-ci.md            am instrument、分片、orchestrator、CI 惯用法
  ui-tree-and-diagnostics.md          uiautomator dump、bug report、ANR、Doze、输入法
LICENSE                               MIT 许可
```

`SKILL.md` 放九条硬规则、四段带完成判据的流程，以及一张「症状 → 根因 → 修法」表；长篇内容都在 `references/` 里按需加载。

## 它是怎么核出来的

每一条结论都对着 Android 自己的一手材料核（AOSP 源码、developer.android.com、SDK Platform Tools release notes），而不是对着别的教程抄。核的过程改了三类内容：

- **冲突保留，不做折中。** 官方材料自己说法不一致时（mDNS 后端的时间线、`adb tcpip` 到底还适用到哪个版本、ADB Wi-Fi 2.0 的门槛），记录各自的说法与版本边界，并给出能一锤定音的那条命令。
- **三条被广泛抄用的说法没通过核验。** `adb logcat -v json` 在 AOSP 的格式列表里并不存在；`--force-queryable` 是 `pm install` 的参数，不是 `adb install` 的；mDNS 后端的时间线普遍差了一个版本（Openscreen 是 35.0.2 成为默认，不是 v34；37.0.1 被删除）。
- **讲得薄的地方按一手材料补写，不靠推测。** UI 树 dump、bug report、ANR 轨迹、Doze 控制、测试机复位、输入法切换，都是从 AOSP 源码与官方文档写出来的，每一条都标了证据等级。

## 已验证与摘录的边界

主机侧行为是文档化且可复现的：选择器、`wait-for` 语义、PTY 对二进制流的破坏、双 shell 引号规则、退出码矩阵、`pm clear` 与 `force-stop` 的区别。设备侧阈值（`svc` 在 API 30+ 静默失效、`screenrecord` 的 180 秒上限、`uiautomator` 的输出形态、无线连接的状态迁移）来自 AOSP 源码与官方文档，**没有**在这里跨设备实测——文中在这些地方明确标了。

另外，流程里每个状态改动旁边都有一条读回断言：假设错了会表现为一次校验失败，而不是一个「绿着错」的测试。

## 当文档和你的二进制互相矛盾

以二进制为准。`adb help` 说明这个构建实际实现了哪些变量与参数，`adb server-status` 报当前 USB 与 mDNS 后端，`adb host-features` 列出编译进去的能力。platform-tools 大版本升级之后，先读这三样，再决定要不要信这份技能里的任何一句话——版本分段表的意义是让这个检查变便宜，而不是替代它。

## 来源

全部内容取自 Android 官方文档与 AOSP 源码：

- [Android Debug Bridge](https://developer.android.com/tools/adb) —— 命令、无线调试、shell、设备复位、后端；
- [logcat](https://developer.android.com/tools/logcat) —— buffer、过滤、格式；
- [SDK Platform Tools release notes](https://developer.android.com/tools/releases/platform-tools) —— USB 与 mDNS 后端的版本边界；
- [捕获与阅读 bug report](https://developer.android.com/studio/debug/bug-report)、[ANR](https://developer.android.com/topic/performance/vitals/anr)、[Doze 与 App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)；
- AOSP 源码：`packages/modules/adb`（含 `docs/user/adb.1.md`）、`frameworks/testing/uiautomator`、`frameworks/base`（`PackageManagerShellCommand`）、`system/logging`；
- [source.android.com —— 用 adb 抓 trace](https://source.android.com/docs/core/graphics/winscope/capture/adb)。

## 许可

MIT，见 [LICENSE](./LICENSE)。
