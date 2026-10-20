# Apps: Install, Reset, Inspect

`adb install` / `pm` semantics. The recurring bug this file exists to prevent: using `am force-stop` as a test reset.

## Install flags that matter

```bash
adb install -r app-debug.apk                       # reinstall, keep data
adb install -r -d app-debug.apk                    # allow versionCode downgrade
adb install -r -t -g app-androidTest.apk           # test APK, all runtime permissions granted
adb install -r -d --user current app-debug.apk     # force foreground-user install
```

Without `-r` an existing package returns `INSTALL_FAILED_ALREADY_EXISTS`, so every CI script installs with `-r`. `-d` applies to debuggable packages on stock builds.

| Flag | Meaning |
|---|---|
| `-l` | Legacy DRM forward-lock; effectively unused |
| `-s` | Install to SD/external storage (where supported) |
| `--user <id>` | Target user profile; default all users, `current` = foreground user |
| `--install-location 0\|1\|2` | 0=default, 1=internal, 2=external |
| `-f` | Internal system memory |
| `-i <installer_pkg>` | Mark the install with a given installer package |
| `--fastdeploy` | Patch-only install (changed bytes only) |
| `--incremental` / `--no-incremental` | Streaming install; needs APK Signature Scheme v4 `.idsig` sidecar; `--wait` blocks until fully available |

## Split APKs

App Bundles produce base + per-feature/per-config splits. A single split alone fails:

```bash
adb install-multiple -r -t -g \
  base-master.apk base-arm64_v8a.apk base-xxhdpi.apk
```

Installing one split by itself gives `INSTALL_FAILED_INVALID_APK` with no hint that it is a split.

## Reset: `pm clear`, not `am force-stop`

```bash
adb shell pm clear com.example.app
adb shell pm clear com.example.app.test       # also reset test-process state
```

`am force-stop` kills the process and leaves SharedPreferences, Room/SQLite databases, `/data/data/<pkg>` files, image caches and granted runtime permissions intact. That is the most common hidden bug in test scaffolding: the next case inherits the previous case's state and flakes. Only use `force-stop` when "kill the process but keep state" is the actual goal (e.g. testing resume-from-killed).

`cmd activity stop-app <pkg>` (API 28+) is the modern `force-stop` equivalent — same non-clearing semantics.

## List, locate, inspect

```
pm list packages [-f] [-d] [-e] [-s] [-3] [-i] [-u] [--user <id>] [<filter>]
```

| Flag | Meaning |
|---|---|
| `-f` | See associated file |
| `-d` | Disabled packages only |
| `-e` | Enabled packages only |
| `-s` | System packages only |
| `-3` | Third-party packages only |
| `-i` | Show installer per package |
| `-u` | Include uninstalled packages |

```bash
adb shell pm list packages -3 | sort                   # sideloaded apps
adb shell pm list packages -f com.example              # APK paths
adb shell pm path com.example.app                      # package:/data/app/.../base.apk
adb shell dumpsys package com.example.app | head -200  # install/permission detail
```

`pm list packages | grep -v 'com.android'` to find third-party apps is wrong in both directions: plenty of third-party ids contain `com.android`, and Google preinstalls are `com.google.android.*`. Use `-3`.

## Runtime permissions (API 23+)

Docs: "Grant a permission to an app. On devices running Android 6.0 (API level 23) and higher, the permission can be any permission declared in the app manifest."

```bash
adb shell pm grant  com.example.app android.permission.CAMERA
adb shell pm revoke com.example.app android.permission.CAMERA
adb shell pm reset-permissions                         # every app back to defaults
```

`-g` at install time is the hermetic choice; `pm grant` is for patching gaps afterwards. Missing grants park UI tests on a permission dialog.

## Enable / disable

```bash
adb shell pm disable com.example.app                       # whole package
adb shell pm disable-user --user 0 com.example.app         # per-user, preserves data
adb shell pm enable  com.example.app
adb shell pm enable  com.example.app/.MyTestActivity       # single component
```

Useful to pin accessibility services / IMEs to a known state, or to A/B competitors. `disable-user --user 0` scopes to one user and keeps data; `disable` does not.

## Uninstall

```
pm uninstall [-k] [--user <id>] [--versionCode <vc>] <package>
```

```bash
adb uninstall com.example.app                       # = pm uninstall <pkg>
adb shell pm uninstall -k com.example.app           # keep data/cache dirs
adb shell pm uninstall --user 0 com.example.app     # primary user only
```

`-k` keeps data — the upgrade-from-clean scenario. `--versionCode <vc>` ("Only uninstalls if the app has the given version code") is what makes CI uninstall idempotent: without it, uninstalling an absent package exits non-zero and breaks the script.

## Baseline profiles

```bash
adb shell cmd package dump-profiles <package>
adb pull /data/misc/profman/<package>.prof.txt
```

ART collects execution profiles from API 24. The docs warn: "It is only possible to retrieve the execution profile filename if you have root access to the file system, for example, on an emulator." On a non-root user build, capture the profile programmatically with `androidx.benchmark` Macrobenchmark instead.

## `adb shell` quoting (Platform Tools 23+)

Docs, verbatim: "With Android Platform Tools 23 and higher, `adb` handles arguments the same way that the `ssh(1)` command does. … `adb shell setprop key 'two words'` is now an error … To make the command work, quote twice, once for the local shell and once for the remote shell, as you do with `ssh(1)`. For example, `adb shell setprop key \"'two words'\"` works because the local shell takes the outer level of quoting and the device still sees the inner level of quoting."

```bash
adb shell setprop key \"'two words'\"
```

Every call carrying spaces or metacharacters obeys this rule — the local shell eats one layer before the device ever sees it.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `Failure [INSTALL_FAILED_TEST_ONLY: installPackageLI]` | Every Gradle `android:testOnly="true"` APK needs `-t` | `adb install -r -t -g app-androidTest.apk` |
| `Failure [INSTALL_FAILED_VERSION_DOWNGRADE]` | installed debug APK has a higher versionCode | add `-d`; if the signing key also changed, uninstall first |
| `INSTALL_FAILED_USER_RESTRICTED` | installing user (secondary/work profile) is restricted | `--user 0` or `--user current`; disable "Install via USB" restriction in that profile |
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | different signing key | `adb uninstall <pkg>`, resign with the same key |
| `INSTALL_FAILED_INSUFFICIENT_STORAGE` | no space | `adb shell df /data`, clean up |
| Second run of a suite fails on leaked state | `am force-stop` used as reset | `pm clear` on app and `.test` |
| `dumpsys package` shows CAMERA still denied after grant | wrong user profile / wrong package id | check `--user`, re-read with `dumpsys package PKG \| grep CAMERA` |

## Verification

- `adb install …` prints `Success`; `adb shell pm path PKG` then resolves to `package:/data/app/.../base.apk`.
- After `pm clear`, `adb shell run-as PKG ls /data/data/PKG` shows only freshly created `cache/` and `code_cache/`.
- After `pm grant`, `adb shell dumpsys package PKG | grep <PERMISSION>` shows it granted.
- `adb uninstall PKG` prints `Success` and `pm list packages PKG` no longer lists it.
