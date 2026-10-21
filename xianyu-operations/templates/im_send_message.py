#!/usr/bin/env python3
"""Send a Xianyu chat message — WebSocket client.

Messaging is not an HTTP call. It is a long-lived LWP socket to the same gateway
the web client uses (`wss://wss-goofish.dingtalk.com/`), and the order of frames
matters. This template keeps the sequence faithful; the parts only you can know
(where the cookies are, who you are messaging, the device id) are in the EDIT block.

Dependencies: `websockets` (pip install websockets / uv run --with websockets).

Sequence, and why each step exists:
  1. accessToken via mtop — the most risk-guarded call in the whole surface, so it
     is fetched once and cached, never per message.
  2. connect with the session cookies in the handshake headers.
  3. `/reg` + `/r/SyncStatus/ackDiff`, then WAIT for the server's `/s/vulcan`.
     Any `/r/` request sent earlier is answered with code 400 — "registered" does
     not mean "ready to send".
  4. heartbeat `{"lwp": "/!"}` every ~15s (LWP heartbeat, not WS ping).
  5. optionally create the single chat for an item, to learn the `cid`.
  6. send via `/r/MessageSend/sendByReceiverScope`, payload base64-encoded.
  7. wait for the ack with the matching mid: code 200 = the server accepted it.
     That is NOT delivery. No ack = unknown state; report it as unknown.

Read references/write-operations.md first: approval, pacing and read-back rules
apply to every write, including this one.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# --------------------------------------------------------------------- EDIT block
COOKIES = ""            # raw "k=v; k=v" string, or a path to a file holding one
                        # (for a saved session: <skill dir>/.state/storage-state.json)
TOID = ""               # the other party's user id (the seller/buyer you reply to)
MYID = ""               # your own user id — the `unb` cookie value
CID = ""                # conversation id, if you already know it
ITEM_ID = ""            # if CID is empty: create the single chat for this item
TEXT = ""               # message text (kind="text")
IMAGE_URL = ""          # kind="image": url + size, from the image upload step
IMAGE_WIDTH = 0
IMAGE_HEIGHT = 0
KIND = "text"           # "text" | "image"
DEVICE_ID = ""          # stable per account: keep it in <skill dir>/.state/device-id,
                        # don't regenerate per run (uuid4-style + "-" + MYID is fine)
ACCESS_TOKEN = ""       # optional: reuse a token you already have (cached in
                        # <skill dir>/.state/im-token, or set GOOFISH_IM_TOKEN);
                        # otherwise it is fetched below
# ----------------------------------------------------------------------------------

APP_KEY = "34839810"                                   # mtop web appKey
IM_APP_KEY = "444e9908a51d1cb236a27862abc769c9"        # IM appKey (protocol constant)
WS_URL = "wss://wss-goofish.dingtalk.com/"
MTOP_HOST = "https://h5api.m.goofish.com"
UA_WEB = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
UA_IM = (UA_WEB + " DingTalk(2.1.5) OS(Windows/10) Browser(Chrome/133.0.0.0) "
         "DingWeb/2.1.5 IMPaaS DingWeb/2.1.5")


# --------------------------------------------------------------- cookies + signing
def load_cookies(source: str) -> dict[str, str]:
    text = source.strip()
    p = Path(text).expanduser()
    if text and "\n" not in text and "=" not in text and p.is_file():
        text = p.read_text(encoding="utf-8").strip()
    if text.startswith("[") or text.startswith("{"):
        data = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get("cookies"), list):
            data = data["cookies"]
        if isinstance(data, list):
            return {c["name"]: c["value"] for c in data if "name" in c}
        return {str(k): str(v) for k, v in data.items()}
    jar = {}
    for part in re.split(r"[;\n]", text):
        if "=" in part:
            k, v = part.split("=", 1)
            jar[k.strip()] = v.strip()
    return jar


def mtop(session_jar: dict[str, str], api: str, data: dict, *, version: str = "1.0",
         spm: str = "a21ybx.im.0.0") -> dict:
    """One signed mtop POST — the same algorithm as templates/mtop_request.py."""
    import urllib.request
    from urllib.parse import urlencode

    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    token = (session_jar.get("_m_h5_tk") or "").split("_")[0]
    t_ms = str(int(time.time() * 1000))
    sign = hashlib.md5(f"{token}&{t_ms}&{APP_KEY}&{payload}".encode()).hexdigest()
    query = urlencode({
        "jsv": "2.7.2", "appKey": APP_KEY, "t": t_ms, "sign": sign, "v": version,
        "type": "originaljson", "accountSite": "xianyu", "dataType": "json",
        "timeout": "20000", "api": api, "sessionOption": "AutoLoginOnly", "spm_cnt": spm,
    })
    req = urllib.request.Request(
        f"{MTOP_HOST}/h5/{api}/{version}/?{query}",
        data=f"data={urlencode({'data': payload})[5:]}".encode(),
        headers={"accept": "application/json",
                 "content-type": "application/x-www-form-urlencoded",
                 "origin": "https://www.goofish.com",
                 "referer": "https://www.goofish.com/",
                 "user-agent": UA_WEB,
                 "cookie": "; ".join(f"{k}={v}" for k, v in session_jar.items())},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def get_access_token(jar: dict[str, str]) -> str:
    """IM accessToken. Cache it — upstream uses a 30-minute TTL and warns that
    hammering this endpoint triggers RGV587."""
    raw = mtop(jar, "mtop.taobao.idlemessage.pc.login.token",
               {"appKey": IM_APP_KEY, "deviceId": DEVICE_ID})
    token = ((raw.get("data") or {}).get("accessToken") or "")
    if not token:
        raise SystemExit(f"no accessToken in response: {raw.get('ret')}")
    return token


# ------------------------------------------------------------------- LWP frames
def mid() -> str:
    return f"{int(1000 * __import__('random').random())}{int(time.time() * 1000)} 0"


def _ack(frame: dict) -> dict:
    h = frame.get("headers") or {}
    out = {"code": 200, "headers": {"mid": h.get("mid") or mid(), "sid": h.get("sid", "")}}
    for k in ("app-key", "ua", "dt"):
        if k in h:
            out["headers"][k] = h[k]
    return out


async def _recv(ws, timeout: float):
    try:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    except (TimeoutError, asyncio.TimeoutError):
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


async def register(ws, jar: dict[str, str], token: str) -> dict[str, str]:
    reg_mid, ack_mid = mid(), mid()
    await ws.send(json.dumps({"lwp": "/reg", "headers": {
        "cache-header": "app-key token ua wv", "app-key": IM_APP_KEY, "token": token,
        "ua": UA_IM, "dt": "j", "wv": "im:3,au:3,sy:6", "sync": "0,0;0;0;",
        "did": DEVICE_ID, "mid": reg_mid}}))
    now_ms = int(time.time() * 1000)
    await ws.send(json.dumps({"lwp": "/r/SyncStatus/ackDiff",
                              "headers": {"mid": ack_mid},
                              "body": [{"pipeline": "sync", "tooLong2Tag": "PNM,1",
                                        "channel": "sync", "topic": "sync", "highPts": 0,
                                        "pts": now_ms * 1000, "seq": 0, "timestamp": now_ms}]}))
    return {"reg": reg_mid, "ack_diff": ack_mid}


async def wait_ready(ws, mids: dict[str, str], timeout: float = 15.0) -> bool:
    """Wait for /s/vulcan, acking inbound frames meanwhile. /reg != 200 is fatal;
    an ackDiff rejection is not (it is routinely 400 and sync still works)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        frame = await _recv(ws, min(3.0, deadline - time.monotonic()))
        if frame is None:
            continue
        fmid = (frame.get("headers") or {}).get("mid")
        if fmid == mids.get("reg") and frame.get("code") != 200:
            raise SystemExit(f"IM registration failed: /reg code={frame.get('code')}")
        try:
            await ws.send(json.dumps(_ack(frame)))
        except Exception:
            pass
        if frame.get("lwp") == "/s/vulcan":
            return True
    return False


async def heartbeat(ws, interval: float = 15.0) -> None:
    while True:
        try:
            await ws.send(json.dumps({"lwp": "/!", "headers": {"mid": mid()}}))
        except Exception:
            return
        await asyncio.sleep(interval)


async def recv_ack(ws, want_mid: str, timeout: float = 10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        frame = await _recv(ws, min(3.0, deadline - time.monotonic()))
        if frame is None:
            continue
        if (frame.get("headers") or {}).get("mid") == want_mid:
            return frame
        try:
            await ws.send(json.dumps(_ack(frame)))
        except Exception:
            pass
    return None


async def create_chat(ws, *, item_id: str) -> str:
    m = mid()
    await ws.send(json.dumps({"lwp": "/r/SingleChatConversation/create",
                              "headers": {"mid": m},
                              "body": [{"pairFirst": f"{TOID}@goofish",
                                        "pairSecond": f"{MYID}@goofish", "bizType": "1",
                                        "extension": {"itemId": item_id},
                                        "ctx": {"appVersion": "1.0", "platform": "web"}}]}))
    return m


async def send(ws, *, cid: str, kind: str, text: str = "") -> str:
    """Send text or image. Returns the mid to match the ack against."""
    if kind == "text":
        payload = {"contentType": 1, "text": {"text": text}}
        ctype = 1
    elif kind == "image":
        payload = {"contentType": 2, "image": {"pics": [
            {"type": 0, "url": IMAGE_URL, "width": IMAGE_WIDTH, "height": IMAGE_HEIGHT}]}}
        ctype = 2
    else:
        raise SystemExit(f"unsupported kind: {kind}")
    m = mid()
    data_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
    await ws.send(json.dumps({
        "lwp": "/r/MessageSend/sendByReceiverScope",
        "headers": {"mid": m},
        "body": [
            {"uuid": str(uuid.uuid4()), "cid": f"{cid}@goofish", "conversationType": 1,
             "content": {"contentType": 101, "custom": {"type": ctype, "data": data_b64}},
             "redPointPolicy": 0, "extension": {"extJson": "{}"},
             "ctx": {"appVersion": "1.0", "platform": "web"},
             "mtags": {}, "msgReadStatusSetting": 1},
            {"actualReceivers": [f"{TOID}@goofish", f"{MYID}@goofish"]},
        ]}))
    return m


@asynccontextmanager
async def connect(jar: dict[str, str]):
    import websockets
    headers = {
        "Cookie": "; ".join(f"{k}={v}" for k, v in jar.items()),
        "Host": "wss-goofish.dingtalk.com", "Connection": "Upgrade",
        "Pragma": "no-cache", "Cache-Control": "no-cache", "User-Agent": UA_WEB,
        "Origin": "https://www.goofish.com", "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    # ping_interval=None: this protocol uses the LWP /! heartbeat, not WS pings.
    async with websockets.connect(WS_URL, additional_headers=headers,
                                  ping_interval=None, max_size=4 * 1024 * 1024) as ws:
        yield ws


async def main() -> None:
    jar = load_cookies(COOKIES)
    myid = MYID or jar.get("unb", "")
    token = ACCESS_TOKEN or get_access_token(jar)
    async with connect(jar) as ws:
        mids = await register(ws, jar, token)
        hb = asyncio.create_task(heartbeat(ws))
        try:
            if not await wait_ready(ws, mids):
                raise SystemExit("socket never became ready (/s/vulcan timed out) — nothing sent")
            cid = CID
            if not cid and ITEM_ID:
                cid = ""  # the create call returns the cid in its ack body; read it there
                create_mid = await create_chat(ws, item_id=ITEM_ID)
                ack = await recv_ack(ws, create_mid)
                cid = str(((ack or {}).get("body") or {}).get("cid", ""))
                if not cid:
                    raise SystemExit(f"could not learn the cid: {json.dumps(ack)[:300]}")
            if not cid:
                raise SystemExit("need CID or ITEM_ID to know where to send")
            send_mid = await send(ws, cid=cid, kind=KIND, text=TEXT)
            ack = await recv_ack(ws, send_mid)
        finally:
            hb.cancel()
    code = (ack or {}).get("code")
    if code != 200:
        raise SystemExit(f"send NOT accepted ({'no ack, state unknown' if ack is None else f'code={code}'})")
    print(json.dumps({"ok": True, "cid": cid, "message_id": str(((ack or {}).get('body') or {}).get('messageId', '')),
                      "note": "server accepted the send — not proof of delivery. Re-read the conversation."},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
