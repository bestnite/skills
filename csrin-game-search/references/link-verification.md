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
| `UNVERIFIED` | the host would not answer honestly: 401, 403, 429, 503, a challenge page, a JavaScript-only page, a transport error | "could not check", never "dead" |

The `UNVERIFIED` bucket is the one that matters. A link behind a bot check is not a broken link, and calling it dead sends the user away from a working file. The reverse mistake — calling a dead link alive because the page returned 200 — is just as common, which is why a status code alone is not enough.

**`UNVERIFIED` is a handoff, not a conclusion.** It means "the cheap check could not tell", so the next step is the strongest tool in the agent's own context, in this order:

1. **A browser** — renders the JavaScript page, passes the bot check, and shows what the site actually says. This is the tool that turns an honest "cannot tell" into an answer.
2. **A fetch or extract tool** — a different transport and user agent than a bare HTTP client, which gets past some soft blocks.
3. **An API with a guest token**, when the host offers one.

Only when all of those fail does the verdict stay `UNVERIFIED`, and then the report says which tools were tried. Measured on 2026-11-25: a host whose content API answered `401` and whose page is JavaScript-only was declared unknowable over HTTP, and a rendered browser answered "This content does not exist" — the link was in fact dead. A second host refused anonymous API calls the same way, while its rendered page showed the file name. Both verdicts came from the browser, and neither was reachable with `curl`.

## Hosts answer in three different ways

| Behaviour | How to check | Why status alone fails |
|---|---|---|
| A public JSON API states liveness | ask the API, read its status or `success` field | the page itself is JavaScript |
| The page answers 200 for a missing file | fetch the page, look for the host's "not found" wording | 200 means "I served you a page", not "the file exists" |
| The API refuses anonymous callers, or the page renders only in a browser | do not guess — `UNVERIFIED` | alive and dead are indistinguishable without a browser |

`templates/check_links.py` implements all three for the hosts this skill meets most often, one request per link, and prints a verdict line each. Read it before writing an ad-hoc check, and extend the host table rather than sprinkling special cases through the call.

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
