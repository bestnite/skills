# Android ADB

[English](./README.md) | [简体中文](./README.zh-CN.md)

An operator's manual for driving an Android device from a host shell — attaching over USB, emulator or wireless debugging, injecting input, flipping app and system state, reading logs, capturing artifacts, and running instrumented tests that fail CI honestly. Raw `adb` / `am` / `pm` / `cmd` / `logcat` only: no wrapper CLI, no MCP server, no scripts to install.

**Repository**: https://git.nite07.com/nite/skills (subdirectory `android-adb/`)

## What It Does

- **Wireless debugging end to end** — the `adb pair` / `adb connect` flow, mDNS discovery, why the pairing port is not the connect port, what to do when a device pairs successfully and never appears, and the version boundaries of the mDNS backends.
- **Attaching reliably** — transport selectors, `wait-for-*` versus real boot readiness, the nine device states and how each one recovers, RSA authorization, Linux udev rules, emulator startup races.
- **Driving the UI** — taps, swipes, long-press, key events, typed text, screen size and density overrides, system settings, app launches with typed extras, and the `cmd <service>` surface that replaces dead `svc` commands.
- **Seeing what happened** — logcat buffers, filters, formats, per-PID streams, failure-time capture.
- **Moving bytes** — screenshots, screen recording, pull/push, app-private files through `run-as`, and where test artifacts should land.
- **Tests and CI** — `am instrument` without Gradle, sharding, orchestrator isolation, and a gate that cannot report green on failure.
- **The parts the guides leave thin** — UI-tree dumps with `uiautomator`, bug reports, ANR evidence routes, Doze/App Standby testing, `cmd testharness enable`, IME switching, and the honest limits of locked-screen handling.

## Installation

```bash
# Install just this skill
npx skills add https://git.nite07.com/nite/skills.git -g -s android-adb
```

Manual installation: copy this whole directory (`SKILL.md`, `references/`, and this README pair) into the skills directory your agent reads. That location is your host's decision — check your agent's documentation rather than assuming a path.

## When To Use It

Use it when you want to:

- connect a phone or tablet over Wi-Fi and keep it connected across reboots and network switches;
- script a device from the host: tap, type, launch, toggle settings, wake it up;
- explain a flaky test run instead of re-running it until it passes;
- collect logs, a screenshot or a recording as evidence for a bug report;
- run instrumentation directly, shard it across devices, or make CI fail when tests fail.

Not for: fastboot / flashing, app implementation, or writing on-device test code (Espresso, Compose test, the UiAutomator library).

## What's Inside

```text
SKILL.md                              entry point: rules, workflows, pitfalls
references/
  connection.md                       transports, selectors, states, wireless pairing
  server-and-architecture.md          client/server/daemon, lifecycle, env vars, keys
  apps.md                             install flags, split APKs, pm, reset semantics
  input-and-state.md                  input, wm, settings, am, cmd, hermetic setup
  observability.md                    logcat buffers, filters, formats, capture
  capture-and-transfer.md             screencap, screenrecord, pull/push, run-as, TestStorage
  instrumented-tests-ci.md            am instrument, sharding, orchestrator, CI idioms
  ui-tree-and-diagnostics.md          uiautomator dump, bug reports, ANR, Doze, IME
LICENSE                               MIT
```

`SKILL.md` carries the nine hard rules, the four workflows with completion criteria, and a symptom → cause → fix table. Everything long-form lives in `references/` and loads only when needed.

## How It Was Built

Every claim was checked against primary sources — AOSP source, `developer.android.com`, and the SDK Platform Tools release notes — rather than against other tutorials. That audit shaped the content in three ways:

- **Conflicts were kept, not averaged.** Where the documentation contradicts itself — the mDNS backend timeline, which Android versions still document `adb tcpip`, the version gate on ADB Wi-Fi 2.0 — the reference records each claim with its version boundary and names the command that settles it.
- **Three widely-copied claims did not survive.** `adb logcat -v json` has no counterpart in AOSP's format list; `--force-queryable` is a `pm install` flag, not an `adb install` one; and the common mDNS timeline is off by a version (Openscreen became the default in 35.0.2, not v34, and was deleted in 37.0.1).
- **Thin areas were filled from primary sources, not invented.** UI-tree dumps, bug reports, ANR traces, Doze control, test-device reset and IME switching are written from AOSP source and the official docs, each line marked with its evidence class.

## Evidence: Verified vs Sourced

Host-side behaviour — selectors, `wait-for` semantics, PTY corruption on binary streams, dual-shell quoting, the exit-code matrix, `pm clear` versus `force-stop` — is documented behaviour, reproducible on any host. Device-side thresholds (`svc` silently no-op on API 30+, `screenrecord`'s 180 s cap, `uiautomator`'s output shape, wireless connection transitions) come from AOSP source and the official docs; they were not exercised across devices here, and are marked as such where they matter.

Every state change in the workflows has a read-back assertion next to it, so a wrong assumption surfaces as a failed check instead of a passing test suite.

## When the Documentation and Your Binary Disagree

Trust the binary. `adb help` says which variables and flags a build actually implements, `adb server-status` reports the active USB and mDNS backends, and `adb host-features` lists compiled-in capabilities. After a platform-tools major release, re-read those three before trusting anything in this skill — the version tables exist to make that cheap, not to replace the check.

## Sources

All material is derived from Android's own documentation and source:

- [Android Debug Bridge](https://developer.android.com/tools/adb) — commands, wireless debugging, shell, reset, backends;
- [logcat](https://developer.android.com/tools/logcat) — buffers, filters, formats;
- [SDK Platform Tools release notes](https://developer.android.com/tools/releases/platform-tools) — version boundaries for the USB and mDNS backends;
- [Capture and read bug reports](https://developer.android.com/studio/debug/bug-report), [ANRs](https://developer.android.com/topic/performance/vitals/anr), [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby);
- AOSP source: `packages/modules/adb` (including `docs/user/adb.1.md`), `frameworks/testing/uiautomator`, `frameworks/base` (`PackageManagerShellCommand`), `system/logging`;
- [source.android.com — capture traces with adb](https://source.android.com/docs/core/graphics/winscope/capture/adb).

## License

MIT — see [LICENSE](./LICENSE).
