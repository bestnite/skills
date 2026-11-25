# Link verification

Verified against the live board and real hosts on 2026-11-25.

File-host links rot. A post from August can carry a dead download by November, and the board runs a whole thread for reporting dead links precisely because it is routine. So a ranked list without a liveness check is a guess with a date on it.

## When to check

Check the links you are about to hand over when the agent has something that can fetch a URL — `curl`, a web-fetch tool, a browser. That is a capability question, not a policy one: the skill says *what* to check and *how to read the answer*, and the agent decides with what.

If nothing can fetch, say the links are unverified and why. Never label a link alive on the strength of a post's date.

## Three verdicts, not two

| Verdict | Meaning | Report as |
|---|---|---|
| `ALIVE` | the host says the file exists | verified, with the check date |
| `DEAD` | the host says the file is gone | drop it, or keep it only to explain why the next candidate is being offered |
| `UNVERIFIED` | the host would not answer honestly: a JavaScript-only page, a 429, a transport error | "could not check with plain HTTP" |
| `BLOCKED` | the host answered 401/403/451 to a normal client | one browser attempt, then the user's problem |

The `UNVERIFIED` bucket is the one that matters. A link behind a bot check is not a broken link, and calling it dead sends the user away from a working file. The reverse mistake — calling a dead link alive because the page returned 200 — is just as common, which is why a status code alone is not enough.

**One escalation, not a search for tools.** An `UNVERIFIED` link gets exactly one more attempt — a browser, which renders the JavaScript and shows what the site actually says. If that answers too, done. If the browser is refused as well (403, "request blocked", a human check that will not pass), the verdict is `BLOCKED` and it stays with the user: they have a real browser, cookies and the right network, and chasing the host further spends minutes to learn nothing.

Do not walk a chain of tools — fetch tool, then another browser, then a different client with another user agent. Each attempt costs a round trip and the host has already told you its answer.

Measured on 2026-11-25: a host whose content API answered `401` and whose page is JavaScript-only was unreadable over HTTP, and a rendered browser answered "This content does not exist" — the link was in fact dead. A second host returned `404` to a plain client and served its download page to a browser — the link was alive. One escalation covered both.

## Spend seconds, not minutes

Link checking is the last step and the easiest place to lose the run: a dozen URLs sent one at a time, each waiting out its own timeout, is time the user never gets back.

- **A container page is one link, not an inventory.** A `filecrypt`/`pearcrypt` container usually answers 403 to a plain client, which is `BLOCKED`. Say that and stop: do not drive a browser through its JavaScript, captcha or reveal buttons to count files or read sizes, and do not chase a saved snapshot on disk. The size and the file count belong in the report only when the post states them; otherwise the answer is "not stated", which is a complete answer.
- **Check what the user will click.** The primary link of the two or three best candidates, plus a fallback host if there is one. Not every part of a twelve-part upload, not every link in the thread: the first part of a split set tells you whether the set is alive.
- **One pass, in parallel, capped per host.** `scripts/check_links.py` runs the URLs together with an 8 s timeout, six in flight overall and at most two against any single host — twelve parts of one upload therefore do not arrive as twelve simultaneous requests and turn a working link into a 429. Flags: `--timeout`, `--workers`, `--per-host`, `--json`; exit 0 when something is alive, 1 when nothing is, 2 on bad usage.
- **Budget it.** A few seconds per host, one browser attempt at most, and no retry when a host already refused. If the cheap pass cannot settle a link, `BLOCKED` is a finished answer, not a failure.

## Hosts answer in three different ways

| Behaviour | How to check | Why status alone fails |
|---|---|---|
| A public JSON API states liveness | ask the API, read its status or `success` field | the page itself is JavaScript |
| The page answers 200 for a missing file | fetch the page, look for the host's "not found" wording | 200 means "I served you a page", not "the file exists" |
| The API refuses anonymous callers, or the page renders only in a browser | do not guess — `UNVERIFIED` | alive and dead are indistinguishable without a browser |

`scripts/check_links.py` implements all three for the hosts this skill meets most often, one request per link, and prints a verdict line each or a JSON array with `--json`. Read it before writing an ad-hoc check, and extend the host table rather than sprinkling special cases through the call.

## Rules

- Check the candidate links, not every link in the thread: the top of the ranked list is what the user will click.
- One request per link. No retry loops, no parallel hammering — a host that throttles will answer 429 and you will have turned a live link into an `UNVERIFIED` one.
- Do not download, range-request, or follow into the actual file to test it. Liveness is the question; the archive is the user's business.
- Record when you checked. "Alive as of <date>" is a claim that expires; "alive" without a date is a claim that lies later.
- A dead link is information for the ranking, not a reason to stop: the next candidate on the list is now the first one.

## Never return a single candidate

One link is a single point of failure, and these hosts fail often. Hand over **every viable candidate found, best first** — three or four is the usual number when a game has been shared for a while — with these properties:

- **spread across hosts**, so one host's quota or takedown does not sink the whole answer;
- **spread across uploaders**, because one uploader's reupload may be the only one that still works;
- **each with its own verdict**, and the dead or unverified ones labelled as such rather than silently dropped.

When the first choice is dead, say what replaced it and why: "the top build's 1fichier link is gone, its Pixeldrain copy is alive, and a second uploader has the same build on another host". That sentence is the difference between a search result and an answer.
