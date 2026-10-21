# Write operations

Everything on this page changes state on a real account. Publishing makes a
listing public; messaging puts text in front of another person. Read the rules
before the recipes.

## Rules that are not optional

- **Explicit user approval for the exact content, before every write.** Draft the
  title/description/price or the message text, show it to the user, wait for a
  yes. This mirrors the approval posture in the Discord skill: nothing visible to
  others goes out without a human saying so.
- **Pace it like a human: at most ~1 write per minute.** The upstream project
  ships exactly that as its default limiter, plus a 10-minute circuit breaker when
  it sees risk-control keywords. Treat that as the floor, not a target.
- **Verify by reading back.** A `SUCCESS` ret means the server accepted the
  request — not that the listing is live or that the message landed. Re-read
  (`mtop.taobao.idle.pc.detail`, message history) and report what you see.
- **Never blind-retry a write.** A failed write may have partially landed (images
  uploaded, a listing created without a price, a message sent but acked late).
  Re-read first, then decide.
- **One account, one session.** Don't run writes from two clients at once.

## Chain 1 — publish a listing

Four steps, in order. The image URLs from step 1 feed steps 2 and 4.

**1. Upload the images** (not mtop — a plain multipart POST, no signing):

```
POST https://stream-upload.goofish.com/api/upload.api
     ?floderId=0&appkey=xy_chat&_input_charset=utf-8
multipart field: file
headers: origin/referer https://www.goofish.com, a desktop user-agent
cookies: the same session
```

Response carries `object.url`, `object.pix` (`"1024x1024"`) and `object.size`.
Upstream declares the part as `image/png` regardless of the actual file type.

**2. Let the server pick the category** — `mtop.taobao.idle.kgraph.property.recommend`,
version `2.0`, spm `a21ybx.publish.0.0`. Its result sits at
`data.categoryPredictResult`: `catId`, `catName`, `channelCatId`, `tbCatId`,
`confidence`. The payload reuses the same image objects as the publish call (see
the template).

**3. Get the posting location** — `mtop.taobao.idle.local.poi.get`, version `1.0`,
data `{"longitude": …, "latitude": …}` (upstream defaults to central Shanghai).
Result: `data.commonAddresses[]` and `data.selectedPoi`, each carrying `prov`,
`city`, `area`, `divisionId`, `poi`, `longitude`, `latitude`, `poiId`. Use the
account's own address — do not invent coordinates.

**4. Publish** — `mtop.idle.pc.idleitem.publish`, version `1.0`, spm
`a21ybx.publish.0.0`, with the payload assembled in `templates/publish_item.py`.
The listing id comes back at `data.itemId`.

Field notes worth knowing before you touch the payload:

| Field | Meaning |
|---|---|
| `itemPriceDTO.priceInCent` | price in **cents**, as a string |
| `itemPriceDTO.origPriceInCent` | optional original price, cents |
| `defaultPrice` | `true` means "no price set" (used when price ≤ 0) |
| `itemPostFeeDTO` | shipping mode; the delivery literals are the API's own Chinese values (see the template) |
| `itemTypeStr` / `quantity` / `simpleItem` | `"b"` / `"1"` / `"true"` for a normal single item |
| `sourceId` / `bizcode` / `publishScene` | all `pcMainPublish` — the web client's own values |
| `uniqueCode` | opaque tracking value carried over from upstream with unexplained provenance. Treat it as opaque and re-derive it if the call is rejected. |

## Chain 2 — take a listing down

`com.taobao.idle.item.delete`, version `1.1`, data `{"itemId": "<id>"}`, spm
`a21ybx.item.0.0`. Re-read the listing afterwards to see the new state.

## Chain 3 — message a user (WebSocket, not mtop)

Messaging does not go over HTTP. It is a long-lived socket to the same gateway the
web client uses, and the sequence matters:

1. **Get an IM access token** — `mtop.taobao.idlemessage.pc.login.token` (v1.0,
   spm `a21ybx.im.0.0`) → `data.accessToken`. **This is the most heavily guarded
   call in the whole API surface** — the upstream project says frequent calls
   trigger `RGV587`. Fetch it once and cache it (upstream uses a 30-minute TTL)
   rather than per message; the cache file is `<skill dir>/.state/im-token`
   (`session-persistence.md`).
2. **Connect** to `wss://wss-goofish.dingtalk.com/` with the session cookies and
   the client's handshake headers.
3. **Register, then wait for readiness**: send `/reg` and `/r/SyncStatus/ackDiff`,
   then wait for the server's `/s/vulcan` frame. Any `/r/` request sent before
   `/s/vulcan` comes back gets `code 400`.
4. **Heartbeat**: `{"lwp": "/!"}` roughly every 15 seconds.
5. **Find the conversation**: for an item-based chat, `/r/SingleChatConversation/create`
   creates the single chat and returns the `cid` you need.
6. **Send** via `/r/MessageSend/sendByReceiverScope` with the text (or image
   `url` + width/height) as a base64-encoded JSON payload.
7. **Wait for the ack** with the matching `mid`. `code 200` means the server
   accepted the send. **It does not mean the message was delivered or even
   persisted** — only a read-back of the history (or the other person) settles
   that. No ack at all means the state is unknown: report it that way instead of
   claiming success.

Reading a conversation uses the same socket (`/r/MessageManager/listUserMessages`),
and inbound frames are base64 — upstream tries plain JSON, then base64 JSON, then
a `decrypt` routine bundled in its JS for the protobuf-shaped bodies.

## Status of this page

The item chain and the IM chain are transcribed from the upstream implementation
(`fancyboi999/goofish-cli`, Apache-2.0) and checked structurally — **they have not
been exercised against a real account from this repository.** No live write was
performed. Fields marked as carried-over (`uniqueCode`) and the whole IM sequence
deserve a supervised first run on a throwaway listing and a test message before
anything is trusted, and the user's approval rule above applies to that run too.
