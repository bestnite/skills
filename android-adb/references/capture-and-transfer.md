# Capture and Transfer

Screenshots, screen recording, file movement, app-private extraction, and where test artifacts should land. One principle spans the whole file: **binary bytes never cross a PTY**.

## Screenshots

```bash
# Save on device, then pull (safe while the test keeps running)
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png ./screen.png

# Stream straight to the host, binary-clean
adb exec-out screencap -p > screen.png

# Multi-display
adb shell screencap -p -d 0 /sdcard/main.png
adb shell screencap -p -d 1 /sdcard/external.png
```

```
screencap [-h] [-p] [-d <displayId>] [<path-on-device>]
```

| Flag | Meaning |
|---|---|
| (none) | raw RGBA framebuffer — **not** a PNG, despite any `.png` suffix |
| `-p` | encode as PNG; required when streaming to stdout |
| `-d <displayId>` | capture a specific logical display |

`adb shell screencap -p > out.png` is the wrong streaming form: `adb shell` allocates a PTY that turns `\n` into `\r\n` on some hosts (notably Windows), corrupting PNG, MP4 and tar. Writing device-side and `pull`ing is immune, because `pull` is binary-clean.

## Screen recording

```
screenrecord [--size WIDTHxHEIGHT] [--bit-rate RATE] [--time-limit TIME]
             [--rotate] [--bugreport] [--verbose] <path-on-device>
```

| Flag | Verbatim meaning |
|---|---|
| `--size WxH` | default is the native resolution if supported, else `1280x720` |
| `--bit-rate R` | default `20Mbps` |
| `--time-limit T` | "default and maximum value is 180 (3 minutes)" |
| `--rotate` | rotate 90°, experimental |
| `--bugreport` | overlay frame info + timestamps for bug-report attachments |
| `--verbose` | log to the command line |

```bash
adb shell screenrecord --bugreport --time-limit 60 \
  --bit-rate 8000000 --size 720x1280 /sdcard/repro.mp4
adb pull /sdcard/repro.mp4 ./repro.mp4
adb logcat -d -v threadtime,year,UTC > repro-logcat.txt
```

`--bugreport` only pays off if you capture logcat at the same moment with a matching timestamp format. `--bit-rate` is written in bits per second in the source example while the table says megabits — copy the number literally, do not convert.

Hard limits:

- `--time-limit` above 180 is silently truncated, no warning. For longer runs, chain 180 s segments and `ffmpeg -f concat -i list.txt -c copy out.mp4`; seamless mirroring is scrcpy's job, not screenrecord's.
- No stdout streaming: it writes one device-side MP4. Live mirroring ⇒ scrcpy/Vysor.
- No audio ("Audio is not recorded with the video file"), no Wear OS support, rotation mid-recording is unsupported.
- Stop early with SIGINT to the device-side process, never host-side `kill -9`:

```bash
adb shell screenrecord --time-limit 180 /sdcard/run.mp4 &
REC=$!
# … on failure …
adb shell pkill -INT screenrecord
wait $REC
adb pull /sdcard/run.mp4 ./run.mp4
```

`SIGKILL` leaves the MP4 unfinalized: file present, duration 0, unplayable. Prefer `/data/local/tmp/` when the SD card may not be mounted yet or you do not want to touch public storage; `/sdcard/` is the default user-visible location.

## pull / push

```
adb pull <remote> [<local>]      # device → host (defaults to cwd)
adb push <local>  <remote>       # host → device

push [--sync] [-z ALGORITHM] [-Z] LOCAL... REMOTE
pull [-a]     [-z ALGORITHM] [-Z] REMOTE... LOCAL
```

| Flag | Meaning |
|---|---|
| `-z <algo>` | compression: `any` / `none` / `brotli` / `lz4` / `zstd` |
| `-Z` | disable compression |
| `--sync` (push) | only push files whose timestamps differ |
| `-a` (pull) | preserve timestamp and mode |
| `-n` | dry run |
| `-q` | suppress progress |

All modern flags need platform-tools ≥ 30 (`-z brotli`/`zstd` additionally need adbd from Android 11+). The legacy `adb pull -p` (show progress) is a **no-op** now — progress is default, `-q` silences it. Do not copy `-p` into new scripts.

```bash
adb push --sync -z brotli ./fixtures/ /sdcard/fixtures/
```

For a fixtures directory with hundreds of unchanged files the second push transfers nothing; on USB 2.0 the difference is large.

## Path permissions — the load-bearing table

| Path | `adb shell` writable? | `pull` works? |
|---|---|---|
| `/data/local/tmp/` | yes | yes |
| `/sdcard/` (= `/storage/emulated/0/`) | yes (scoped storage rules API 30+) | yes |
| `/data/data/<pkg>/` | only via `run-as <pkg>` (debuggable) | only via `run-as` |
| `/sdcard/Android/data/<pkg>/files/` | package-owned | yes for the owning package and for `adb shell` (FUSE/sdcardfs bridge) |

Most `Permission denied` reports are a misreading of this table.

`/data/local/tmp/` is shell-private staging (`0771`): pushed APKs, test data, captured screenshots, JSON inputs. The UID trap: the app runs as `u0_aXX`, not `shell`, so it cannot read what you pushed unless you `chmod 0644` and the parent directory is world-readable.

`/sdcard/` keeps working for tests on API 30+ because the `shell` user retains FUSE/sdcardfs access even after scoped storage tightened. App-written files go through MediaStore — conflating the two sides produces the wrong conclusion "/sdcard is unusable after Android 11".

## `run-as` (debuggable APKs only)

```bash
adb shell run-as com.example.app ls -lR files/
adb exec-out run-as com.example.app cat databases/main.db > main.db
adb exec-out run-as com.example.app tar cf - databases/ | tar xf - -C ./pulled
```

Mechanics: a setuid helper that drops `shell` into the app UID **iff** the merged manifest has `android:debuggable="true"` (default for `debug` variants). Three things it cannot do:

1. Work on release builds — prints "Package is not debuggable".
2. Switch to a system UID (only the target package's UID).
3. Cross profile boundaries by itself — pass `--user N`.

For binary content and directories, `exec-out` is mandatory (`MUST` in the source): `adb shell run-as … cat` corrupts bytes via PTY translation, so a pulled SQLite file may not open. `run-as` has no `adb pull` equivalent — hence the tar pipe.

## Where app-written artifacts should land

Preferred: the app's own external-private dir, writable by the app and readable by `adb shell` without `run-as`.

```kotlin
val out = File(context.getExternalFilesDir(null), "captures/${name}.png")
out.outputStream().use { it.write(bitmapBytes) }
```

```bash
adb pull /sdcard/Android/data/com.example/files/captures/ ./artifacts/
```

Gradle sinks:

| Path | Origin |
|---|---|
| `app/build/outputs/connected_android_test_additional_output/<flavor><Variant>/connected/<deviceId>/` | driven by the `additionalTestOutputDir` runner arg |
| `app/build/outputs/androidTest-results/connected/<flavor><Variant>/TEST-*.xml` | JUnit XML for Jenkins/GHA |
| `app/build/reports/androidTests/connected/` | HTML report |

CI must archive `connected_android_test_additional_output/**/*` or TestStorage output is silently discarded.

## TestStorage

```kotlin
androidTestImplementation("androidx.test:runner:1.7.0")
androidTestUtil("androidx.test.services:test-services:1.6.0")
```

```bash
adb shell am instrument -w -r \
  -e useTestStorageService true \
  com.example.test/androidx.test.runner.AndroidJUnitRunner
```

```kotlin
val storage = androidx.test.platform.io.PlatformTestStorageRegistry.getInstance()
storage.openOutputFile("screenshots/fail-${test.methodName}.png").use { out ->
    out.write(pngBytes)
}
```

It solves four problems at once: the sink is managed by TestStorageService rather than `/sdcard`; `connectedAndroidTest` picks it up into `connected_android_test_additional_output/`; per-test namespacing is the runner's job; and — the real motivation — artifacts survive `clearPackageData: 'true'`, which wipes anything hand-written under `/sdcard`. Non-Gradle pipelines find the same layout under the legacy prefix `/sdcard/googletest/test_outputfiles/...`.

## Capture on failure, three layers

Host script:

```bash
set +e
./gradlew connectedDebugAndroidTest
RC=$?
set -e

if [ "$RC" -ne 0 ]; then
  mkdir -p artifacts
  adb shell screencap -p /sdcard/fail.png
  adb pull /sdcard/fail.png artifacts/fail.png
  adb logcat -d -v threadtime > artifacts/logcat.txt
  adb logcat -d -b crash    -v threadtime > artifacts/crash.txt
fi
exit $RC
```

Device-side, JUnit4 rule:

```kotlin
class CaptureOnFailureRule(private val outputDir: File) : TestWatcher() {
    override fun failed(e: Throwable, description: Description) {
        val testName = "${description.className}.${description.methodName}"
        val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
        val target = File(outputDir, testName).apply { mkdirs() }
        device.executeShellCommand("screencap -p /sdcard/fail.png")
        val log = device.executeShellCommand("logcat -d -v threadtime")
        File(target, "logcat.txt").writeText(log)
    }
}
```

Note `executeShellCommand` takes a **device-side** command with no `adb` prefix — mixing host and device syntax is the common error here. The TestStorage variant replaces the file write with `openOutputFile` and inherits the Gradle sink.

Only capture on failure: capturing every test both drowns CI storage and hides the interesting run.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `file out.png` says `data` | missing `-p` | `screencap -p`, then pull |
| PNG/MP4 opens as garbage, hex full of `0d 0a` | PTY newline translation | `exec-out`, or device-side file + pull |
| 10-minute recording came out 3 minutes, no error | `--time-limit` cap 180 s | chain segments, or scrcpy |
| MP4 exists but is zero-length/corrupt | host-side `kill -9` | `adb shell pkill -INT screenrecord` then `wait` |
| Video has no audio | not recorded by design | separate audio track or another tool |
| `pull /data/data/PKG/...` → `Permission denied` | `0700`, app UID | `exec-out run-as PKG …`, or `adb root` on userdebug/eng |
| Pulled SQLite will not open | `adb shell run-as … cat` through a PTY | `adb exec-out run-as … cat`; verify with `file` |
| Directory cannot be pulled | `run-as` has no pull form | tar over `exec-out` |
| App cannot read a pushed fixture | app UID vs `/data/local/tmp` `0771` | `chmod 0644`, world-readable parent |
| Every push of hundreds of files is slow | no `--sync` | `adb push --sync -z brotli` |
| `adb pull -p` shows no progress | flag deprecated to a no-op | drop `-p`; use `-q` for silence |
| Artifacts vanish when `clearPackageData` is on | `/sdcard` wiped between tests | use TestStorage |
| TestStorage wrote files but Gradle output is empty | missing `androidTestUtil(...test-services...)` or the `-e useTestStorageService true` arg | add both; check the googletest prefix for non-Gradle |
| App writes to `/sdcard/<dir>/` fail on API 30+ | MediaStore scoping | `Context.getExternalFilesDir(null)` |
