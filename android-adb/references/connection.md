# Connection and Transport Selection

Attaching a device, picking among several, waiting for real readiness, and the wireless (`adb pair` / mDNS / legacy `tcpip`) path in full. Sources: `developer.android.com/tools/adb` and AOSP's `adb` man page (`packages/modules/adb/docs/user/adb.1.md`).

## Transports: always start here

```bash
adb devices -l
# List of devices attached
# emulator-5556  device  product:sdk_google_phone_x86_64 model:Android_SDK_built_for_x86_64 device:generic_x86_64 transport_id:1
# 0a388e93       device  usb:1-1 product:razor model:Nexus_7 device:flo transport_id:2
```

`-l` adds `product`, `model`, `device` and `transport_id`, plus the USB bus path (`usb:1-1`). Without it you cannot use `-t`, and you cannot tell two same-model devices apart.

Scripts take only ready targets:

```bash
adb devices | awk '$2=="device"{print $1}'
```

`adb get-serialno`, `adb get-state` and `adb get-devpath` exist, but `get-state` only knows `offline | bootloader | device` — it cannot report `recovery`, `sideload`, `unauthorized`, `no permissions` or `connecting`. Read `adb devices` instead when the answer matters.

## Selectors

| Flag | Meaning | Fails when |
|---|---|---|
| `-s <serial>` | Explicit serial: USB (`0a388e93`), emulator (`emulator-5554`), TCP (`192.168.1.42:5555`). Overrides `ANDROID_SERIAL`. | serial absent |
| `-d` | The only USB device | 0 or >1 USB devices |
| `-e` | The only TCP/IP device (emulators included) | 0 or >1 TCP devices |
| `-t <transport_id>` | Numeric id from `adb devices -l`; stable across re-plugs on the same port | id gone |

`-t` exists for the one case serials collide (duplicate AVDs, rare hardware bugs). To make a shared runner single-tenant, lock the server instead:

```bash
adb --one-device 0a388e93 start-server
```

This removes `error: more than one device/emulator` at the source, at the cost of restricting every client on that server to one device.

## Waiting for the right thing

```
wait-for[-TRANSPORT]-STATE
    TRANSPORT ∈ { usb, local, any }            (default: any)
    STATE     ∈ { device, recovery, rescue, sideload, bootloader, disconnect }
```

| Command | Blocks until |
|---|---|
| `adb wait-for-device` | any transport reaches `device` (CI opener) |
| `adb wait-for-usb-device` | a USB device reaches `device` |
| `adb wait-for-local-device` | a TCP/IP device (emulator or wireless) reaches `device` |
| `adb wait-for-bootloader` | device entered bootloader (fastboot territory) |
| `adb wait-for-recovery` / `wait-for-sideload` / `wait-for-rescue` | the corresponding mode |
| `adb wait-for-disconnect` | the selected device drops off |

`adb wait-for-device-online` is not a subcommand — `-online` is not a state. It prints a usage error.

`wait-for-*` only proves a transport exists. Boot readiness is a second, separate gate:

```bash
adb wait-for-device
until [[ "$(adb shell getprop sys.boot_completed | tr -d '\r')" == "1" ]]; do
  sleep 1
done
adb shell input keyevent 82   # AOSP slide-up keyguard only
```

`tr -d '\r'` is not optional: `adb shell` output carries CRLF on most implementations, so a direct `== "1"` comparison is never true and the loop spins forever.

Reboot needs the compound sequence, order intact:

```bash
adb shell reboot
adb wait-for-disconnect
adb wait-for-device
```

After `reboot` the transport can still linger briefly; waiting for `device` immediately returns and the next command hits a dying `adbd`. Establish "it went away" first.

Emulator startup has its own race — start the server first:

```bash
adb start-server
emulator -avd Pixel_API_34 &
adb -s emulator-5554 wait-for-device
```

Verbatim corner case: running emulators may not show up in `adb devices` when **all** of these hold — the adb server is not running, you passed `-port`/`-ports` with an odd port between 5554 and 5584, and you started the server after the emulator. Three conditions at once, which is why it is nearly impossible to self-diagnose.

## State machine

| State | Meaning | Recovery |
|---|---|---|
| `device` | adbd answers. **Not** a booted system. | check `sys.boot_completed` |
| `offline` | transport exists, adbd is not talking (suspend/resume, bad hub, cable) | `adb reconnect offline`, then re-plug |
| `unauthorized` | host RSA key not accepted on the device | unlock, tap **Allow**; no dialog ⇒ bad cable/port |
| `recovery` | recovery mode, few adb commands work | n/a |
| `sideload` | OTA sideload; pair with `adb sideload package.zip` | n/a |
| `bootloader` | fastboot mode, adb cannot talk | use `fastboot` |
| `rescue` | Rescue Party (Android 10+) | n/a |
| `connecting` | transient TLS handshake (wireless) | wait — do not `reconnect` into it |
| `no permissions` | Linux: USB visible, udev rule missing | see udev below |

`connecting` is the only state that heals by waiting; treating it as `offline` and reconnecting aborts the handshake mid-flight.

## Authorization

First connection on Android 4.2.2 (API 17)+ shows "Allow USB debugging?" with the workstation's RSA fingerprint. Before **Allow**, `adb devices` says `unauthorized`; after, the public key is appended to `/data/misc/adb/adb_keys`. "Always allow from this computer" binds that to `~/.android/adbkey`.

Revoke on the device (`Settings → Developer options → Revoke USB debugging authorizations`), not by deleting `~/.android/adbkey*` — deleting rotates the host keypair and silently un-authorizes every device you ever paired, which on a headless machine nobody can re-approve.

## Linux udev (`no permissions`)

`/etc/udev/rules.d/51-android.rules`, one line per vendor:

```
# Google
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0660", GROUP="plugdev", TAG+="uaccess"
# Samsung
SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0660", GROUP="plugdev", TAG+="uaccess"
```

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
# unplug and re-plug the device
```

`TAG+="uaccess"` grants the current login session; `GROUP="plugdev"` covers non-systemd-logind setups. Most distros ship the same file in `/lib/udev/rules.d/` via `android-udev` / `android-sdk-platform-tools-common` — install the package instead of hand-maintaining rules.

Windows needs the OEM driver (Pixel/Nexus: SDK Manager → Google USB Driver); macOS and Linux need none, and installing a Windows-style driver on macOS only creates conflicts.

## Wireless: `adb pair` (Android 11+)

Device: `Settings → System → Developer options → Wireless debugging` → on → **Pair device with pairing code**. It shows an `IP:PORT` and a six-digit code.

```bash
adb pair 192.168.1.42:42999
# Enter pairing code: 123456
# Successfully paired to 192.168.1.42:42999 [guid=adb-...-RQAZWM]
```

`adb pair` prompts interactively so the code never lands in shell history. The returned `[guid=...]` is the mDNS service instance name, matching what `adb mdns services` prints.

Then connect on the **debug** port — a different port from the pairing one:

```bash
adb connect 192.168.1.42:39555
adb devices
# 192.168.1.42:39555  device
adb disconnect 192.168.1.42:39555   # or `adb disconnect` with no arg = all TCP devices
```

Both ports are ephemeral and change whenever wireless debugging is toggled or the device reboots.

## mDNS discovery

```bash
adb mdns check
# mdns daemon version [openscreen discovery 0.0.0]   <- 35.0.2–36.x literal
# on 37.x the same command reports: mdns daemon version [adb discovery 0.0.0]

adb mdns services
# adb-XXXXXXXX-RQAZWM   _adb-tls-pairing._tcp  192.168.1.42:42999
# adb-XXXXXXXX-RQAZWM   _adb-tls-connect._tcp  192.168.1.42:39555
```

| Service type | What it is |
|---|---|
| `_adb._tcp` | legacy `adb tcpip` broadcast |
| `_adb-tls-pairing._tcp` | ephemeral pairing port, only while the pairing dialog is open |
| `_adb-tls-connect._tcp` | post-pairing debug port, auto-connected by default (`ADB_MDNS_AUTO_CONNECT=adb-tls-connect`) |

"Paired successfully but the device never appears" is explained here: pairing only produces the pairing entry; the device shows up when the server discovers and auto-connects the connect entry, which requires working mDNS.

### Backend: version-dependent, and the documents disagree

Authoritative timeline (platform-tools release notes, checked 2026-10):

| ADB version | Default mDNS backend | What `ADB_MDNS_OPENSCREEN` does |
|---|---|---|
| ≤ 35.0.1 | Bonjour / platform mDNS responder | `1` forces Openscreen (Windows/Linux since v34, macOS since v35) |
| 35.0.2 – 36.x | Openscreen on all platforms | `1`/`0` selects between Openscreen and Bonjour |
| 37.0.0 | `libadbmdns` (Openscreen kept as deprecated failover) | still parsed; sets `mdns_backend_forced` |
| 37.0.1+ | `libadbmdns` only — Openscreen deleted | **no effect** (release note: "ADB_MDNS_OPENSCREEN no longer has any effect") |

Three documents disagree on this and none of them is current: a widely-copied guide says "v34+ defaults to Openscreen", the developer guide (updated 2026-09-25) says "as of ADB v37 there are two backends, default `libadbmdns`, changeable with `ADB_MDNS_OPENSCREEN`", and the AOSP man page on `main` still claims "the default mDNS-SD backend is Bonjour". Verified on 2026-10 against the platform-tools release notes for 35.0.2, 37.0.0 and 37.0.1.

Determine it from the tool, never from a doc. `adb server-status` prints `mdns_backend:` and `mdns_backend_forced:`; on 37.0.x a pinned request shows as `mdns_backend_forced: true` while the backend still reports `LIBADBMDNS`, `adb help` does not list the variable at all, and `adb host-features` still advertises `openscreen_mdns` even when the active backend is `libadbmdns`. On 35.0.2–36.x the same commands report `openscreen`.

Therefore: never decide the backend from a doc — read `adb server-status`. And never gate CI on the literal in `adb mdns check`, because the string changed with the backend (`openscreen discovery 0.0.0` → `adb discovery 0.0.0` on 37.x).

## Failure order

Verbatim from the docs: "Device not connecting after pairing successfully: `adb` relies on mDNS to discover and automatically connect to paired devices. If your network or device configuration does not support mDNS or has disabled it, then you need to manually connect to the device using `adb connect ip:port`."

1. **Same network?** Same SSID, same VLAN/subnet on both ends.
2. **Secure/corporate Wi-Fi?** "Secure Wi-Fi networks, such as corporate Wi-Fi networks, may block p2p connections and not let you connect over Wi-Fi. Try connecting with a cable or another (non-corp) Wi-Fi network." This one blocks silently and is the usual reason a re-pairing loop never terminates.
3. **mDNS off?** `adb mdns check`; if the daemon is not running, fall back to `adb connect <ip>:<connect-port>` from the device screen.
4. **`connection refused`?** The wireless-debugging port closed — toggle off, device rebooted, or the pairing port was used. Re-enable/re-pair and take the port from `adb mdns services`.
5. **Drops after a network switch?** "`adb` over Wi-Fi sometimes turns off automatically: This can happen if the device either switches Wi-Fi networks or disconnects from the network. To resolve, re-connect to the network."

Order is the diagnostic asset: prove the network first, then p2p blocking, then the mDNS daemon, then port freshness, and only then blame the link. Skipping steps 1-2 means re-pairing forever inside a corporate network.

## Port lifetimes

| Port | Lifetime | Dies on |
|---|---|---|
| `_adb-tls-pairing._tcp` pairing port | one-shot | successful pairing, a second pairing prompt, toggle off |
| `_adb-tls-connect._tcp` debug port | current session | toggle off, reboot, Wi-Fi switch |
| legacy `5555` (`adb tcpip`) | until next reboot | reboot (falls back to USB-only; `adb usb` resets manually) |

After a reboot the pairing itself survives but the connect port changes — rely on mDNS auto-connect or re-read the port. In legacy `tcpip` mode a reboot ends wireless entirely and needs a new USB bootstrap.

## Legacy `adb tcpip`

```bash
# USB first, accept the RSA dialog, confirm with `adb devices`
adb tcpip 5555
# unplug USB
adb connect 192.168.1.42:5555
adb usb                      # back to USB-only
```

Four reasons it is the fallback: USB bootstrap required (defeats the point), `5555` is a well-known unauthenticated listener until reboot, reboot drops it, and there is no mDNS discovery. Scope, per the adb docs: the section is titled "only option available on Android 10 and lower", but a note adds that the workflow "is applicable also to Android 11 (and higher), the caveat being that it also involves an *initial* connection over physical USB". So: the only path on API 29 and below, a documented fallback above it, and — both sources agree — always inferior to `adb pair`.

## Version notes

- Wireless pairing: phones/tablets Android 11 (API 30)+; TV/Wear Android 13 (API 33)+.
- **ADB Wi-Fi 2.0** (per the adb docs): "Android 17, alongside adb 37.0.0 introduces adb Wi-Fi 2.0" — it auto-connects the device when it joins a wireless-debugging trusted network. It needs both a device on Android 17 and host platform-tools 37.0.0+; it is a new tier, not an upgrade of the API 30 baseline. Older devices keep the pair/connect flow described above.
- Developer options are hidden until you tap **Build number** seven times in **About phone**.
