# Server, Architecture and Host Environment

When adb "is being weird", the first question is which of the three pieces is broken: the local CLI, the long-lived host server on TCP 5037, or the device-side daemon. Most wasted hours come from skipping that question.

## Topology

- **Client** — the `adb` CLI in your terminal. Serializes commands to the local server over a socket.
- **Server** (`adb-server`) — host-side background process. Multiplexes clients, tracks transports, forwards to `adbd`. Binds **localhost:5037** by default.
- **Daemon** (`adbd`) — runs on the device (started by `init` on userdebug/eng, by the system on user builds), executes in the device's user space.

`* daemon not running; starting now at tcp:5037` followed by `* daemon started successfully` is informational: the CLI auto-started the server. Treating it as an error wastes time.

## Lifecycle

| Command | Effect |
|---|---|
| `adb start-server` | Ensure a server on 5037; no-op if a compatible one runs. Fails if the port is held by another process or an incompatible old server. |
| `adb kill-server` | Terminate the local server; the next `adb` command restarts it. **Drops every other client's session on this host.** |
| `adb reconnect` | "Kick connection from host side to force reconnect." Stuck USB transport. |
| `adb reconnect device` | "Kick connection from device side." Makes `adbd` re-handshake. |
| `adb reconnect offline` | "Reset offline/unauthorized devices to force reconnect." Targets only broken transports. |
| `adb -P PORT …` | Override the server port (≡ `ANDROID_ADB_SERVER_PORT`). |
| `adb server-status` | Server configuration as protobuf-ish text: `usb_backend`, `mdns_backend`, `mdns_backend_forced`, `version`, `burst_mode`, `mdns_enabled`, executable and log paths. The fastest way to answer "which backend am I actually on" |

Recovery ladder for a stuck transport — smallest action first:

```bash
adb reconnect offline
# if that fails:
adb kill-server && adb start-server && adb devices
```

`kill-server` is last because it is a shared resource: it kicks Logcat, Android Studio and every other client holding a transport.

## Which binary is actually running

```bash
adb --version
which -a adb         # find shadowed copies
```

```
Android Debug Bridge version 1.0.41         # wire protocol (stable for years)
Version 35.0.2-12147458                      # platform-tools release + Google build
Installed as /opt/homebrew/bin/adb           # the file the OS resolved
Running on Darwin 24.6.0 (arm64)
```

Wire compatibility is decided by the first line only: a client/server mismatch kills the running server with `adb server version (XX) doesn't match this client (YY); killing...`.

With Android Studio installed, keep exactly one `adb`. Studio auto-updates its own `platform-tools/`; a second copy earlier in `PATH` produces three distinct failures: version skew (every command kills the other's server), two servers fighting over 5037, and different default backends (`libusb` vs native) giving inconsistent device enumeration.

```bash
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$ANDROID_HOME/platform-tools:$PATH"
adb kill-server                  # clear stale state once
adb --version                    # confirm the resolved path
```

Setting `PATH` once inside a script is not enough — Studio's Run button uses its own `platform-tools/adb`, so order decides who wins.

## Environment variables (from `adb help`)

| Variable | Purpose |
|---|---|
| `ADB_TRACE` | Debug categories, comma/space separated: `all,adb,sockets,packets,rwx,usb,sync,sysdeps,transport,jdwp,services,auth,fdevent,shell,incremental,mdns`. Newer adb also accepts a level per category (`usb:v, services:w`) |
| `ADB_VENDOR_KEYS` | Colon-separated RSA key files/dirs; skips the "Allow USB debugging?" dialog on headless CI |
| `ANDROID_SERIAL` | Default device serial (≡ `-s`), overridden by an explicit `-s` |
| `ANDROID_ADB_SERVER_PORT` | Server port (default 5037) ≡ `-P PORT` |
| `ADB_LOCAL_TRANSPORT_MAX_PORT` | Highest odd port scanned for emulators, default `5585` (16 emulators) |
| `ADB_MDNS_AUTO_CONNECT` | CSV of auto-connectable mDNS service types, default `adb-tls-connect` |
| `ADB_MDNS_OPENSCREEN` | `1`/`0` selects the mDNS backend. Openscreen became the default in 35.0.2; `libadbmdns` replaced it in 37.0.0 and Openscreen was deleted in 37.0.1, where the variable stops mattering. The AOSP man page and developer guide still describe the old behaviour |
| `ADB_LIBUSB` | `1`/`0` forces libusb. Timeline: 35.0.0 (2024-02) "Switch to libusb as the default on Linux"; 36.0.0 (2025-04) rewritten libusb backend + Windows hot-plug; 36.0.2 (2025-09) "Make legacy USB backend the default on Linux (instead of libusb) due to instability reports"; 37.0.1 disables libusb on macOS and introduces `libadbusb` on Windows. Pin it explicitly when reproducibility matters |
| `ADB_USB_LEGACY` | `1` disables the new `libadbusb` USB backend on Windows (37.0.1+) |
| `ADB_BURST_MODE` | `1`/`0` unacknowledged pipelined transfers; experimental, ADB 36.0.0+ |
| `ANDROID_LOG_TAGS` | Default logcat filter (see `observability.md`) |

Headless CI needs a pre-seeded key and its own port:

```bash
export ADB_VENDOR_KEYS=/etc/adb/ci-key
export ANDROID_ADB_SERVER_PORT=5038
export ADB_LOCAL_TRANSPORT_MAX_PORT=5617
adb start-server
```

## Diagnostic trace

```bash
ADB_TRACE=all adb devices -l 2>~/adb-trace.log
```

Without a trace, a failure gives you one final error string and no transport/handshake evidence. Scope it to the reproduction and remove the variable afterwards.

## Server log (persistent, different from per-command trace and from logcat)

| OS | Path |
|---|---|
| Linux | `$TMPDIR/adb.$UID.log` (e.g. `/tmp/adb.1000.log`) |
| macOS | `$TMPDIR/adb.$UID.log` (e.g. `/var/folders/.../T/adb.501.log`) |
| Windows | `%TEMP%\adb.log` |

```bash
adb kill-server
ADB_TRACE=adb,transport,auth adb start-server
adb devices -l
ls -lh "$TMPDIR/adb.$UID.log"
```

The server is long-lived: only this file remembers what happened *before* (when a transport dropped, why auth failed). A per-command trace cannot answer that.

## `~/.android/` is load-bearing

`~/.android/adbkey` (private) and `adbkey.pub` are generated on first `adb` use. Each "Allow USB debugging?" appends the public key to the device's `/data/misc/adb/adb_keys`.

Deleting the keypair un-authorizes **every** device you ever accepted, and leaves orphaned public keys on devices. Only regenerate when the key is genuinely lost or corrupt, and accept the re-authorization cost:

```bash
adb keygen ~/.android/adbkey
```

Keep the private key `600`.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `adb server version (41) doesn't match this client (40); killing...` | Two platform-tools installs, wrong one first in `PATH` | one canonical `adb`; `adb kill-server` once; verify with `adb --version` |
| `unauthorized`/`offline` "fixed" into total failure | keypair deleted, every device now unknown | `adb reconnect offline` first; `kill-server`+`start-server` second; re-accept on the device last. Never delete keys as step one |
| `adb start-server` fails silently, `adb devices` hangs | something else holds 5037 | `lsof -nP -iTCP:5037 -sTCP:LISTEN`, or run a second server on `ANDROID_ADB_SERVER_PORT=5038` |
| Cannot explain a transport bug | only the final error was captured | attach `$TMPDIR/adb.$UID.log` plus an `ADB_TRACE=adb,transport,auth` reproduction |
| CI loses authorization between jobs | no `ADB_VENDOR_KEYS`, nobody can tap Allow | pre-seed the key file; never regenerate the keypair per job |
