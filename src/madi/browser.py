# coding: utf-8
"""browser.py -- HyperEdgeBrowser: the one browsing instrument for grant work.

Grant discovery lives behind JS-gated portals: RFP listings that render
client-side, eligibility quizzes behind logins, submission forms with five
steps. This module folds every rung this tree has learned into one place:

- Rung 1 (stdlib): plain GET with a full browser header set. Fast, no deps.
- Rung 2 (taxonomy): every response is classified -- ``ok``, ``blocked``
  (with the challenge named: cloudflare, captcha, imperva, bot-wall), or
  ``error``. ``blocked`` is a finding about the environment, never an
  empty result; the two are never merged.
- Rung 3 (render): headless Chromium via Playwright executes the page's
  JavaScript the way a real browser does, so challenges that clear on
  their own resolve here.
- Sessions: an optional state directory persists login state
  (``storage_state``) across runs, so a portal login happens once.
- Interaction: fill/click helpers for portal forms, with a politeness
  delay between navigations so the instrument never hammers a host.
- Evidence: screenshots on demand into an evidence directory, so every
  extracted claim can be traced to a pixel.

Playwright is an OPTIONAL dependency (``pip install grantforge[browser]``)
and is imported lazily: importing this module never requires it, and
every render path raises a RuntimeError naming exactly what to install.
"""

from __future__ import annotations

import math
import os
import random
import re
import time
import urllib.parse as _parse
import urllib.request as _request

__all__ = [
    "HyperEdgeBrowser",
    "BROWSER_UA",
    "BROWSER_HEADERS",
    "CHALLENGE_MARKS",
    "detect_challenge",
    "fetch",
    "playwright_available",
    "RelevanceScorer",
    "featurize",
    "screen_text",
]

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

BROWSER_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": ("text/html,application/xhtml+xml,application/xml;"
               "q=0.9,image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

# (kind, marker): marker found in body or headers names the challenge.
# A bare 403/503 with no marker is an error, not a challenge.
CHALLENGE_MARKS = (
    ("cloudflare-iuam", "Just a moment"),
    ("cloudflare-iuam", "cf-chl"),
    ("cloudflare-iuam", "challenges.cloudflare.com"),
    ("cloudflare-turnstile", "turnstile"),
    ("cloudflare-deny", "cf-error-details"),
    ("captcha-wall", "g-recaptcha"),
    ("captcha-wall", "hcaptcha"),
    ("imperva", "incapsula"),
    ("imperva", "imperva"),
    ("imperva", "reese84"),
    ("bot-wall", "Access Denied"),
    ("bot-wall", "Attention Required"),
    ("bot-wall", "are you a robot"),
)

TIMEOUT_S = 30
RENDER_SETTLE_MS = 4000
POLITENESS_S = 1.0


def playwright_available() -> bool:
    """True iff Playwright is importable (render rung usable)."""
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False


def _require_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except Exception as e:
        raise RuntimeError(
            "HyperEdgeBrowser render rung needs Playwright: "
            "pip install grantforge[browser] && playwright install chromium "
            "(%s)" % (e,)
        )


def detect_challenge(status, headers, body):
    """Name the bot challenge on a response, or None if it reads clean."""
    try:
        text = body if isinstance(body, str) else (body or b"").decode(
            "utf-8", "replace")
    except Exception:
        text = ""
    low = text.lower()
    try:
        head = " ".join("%s: %s" % (k, v)
                         for k, v in dict(headers or {}).items()).lower()
    except Exception:
        head = ""
    for kind, mark in CHALLENGE_MARKS:
        m = mark.lower()
        if m in low or m in head:
            return kind
    return None


def _shape(url, final_url, status, state, text="", title="",
           challenge=None, detail="", elapsed_ms=0):
    return {
        "url": url,
        "final_url": final_url or url,
        "status": status,
        "state": state,            # ok | blocked | error
        "challenge": challenge,    # named wall, or None
        "title": title,
        "text": text,
        "detail": detail,
        "elapsed_ms": elapsed_ms,
    }


def fetch(url, timeout_s=TIMEOUT_S):
    """Rung 1+2: stdlib GET with browser headers, challenge-classified.

    Never needs Playwright. Returns the shaped result dict; raises
    nothing -- transport failures come back as ``state: error``.
    """
    start = time.perf_counter()
    try:
        req = _request.Request(url, headers=BROWSER_HEADERS)
        with _request.urlopen(req, timeout=timeout_s) as r:
            raw = r.read()
            status = r.status
            headers = dict(r.headers or {})
            final = r.geturl()
    except Exception as e:
        ms = int((time.perf_counter() - start) * 1000)
        return _shape(url, url, 0, "error", detail=str(e)[:200],
                      elapsed_ms=ms)
    ms = int((time.perf_counter() - start) * 1000)
    challenge = None
    if status in (403, 429, 503):
        challenge = detect_challenge(status, headers, raw)
    if challenge:
        return _shape(url, final, status, "blocked", challenge=challenge,
                      detail="named wall: %s" % challenge, elapsed_ms=ms)
    if status >= 400:
        return _shape(url, final, status, "error",
                      detail="HTTP %d, no challenge marker" % status,
                      elapsed_ms=ms)
    try:
        text = raw.decode("utf-8", "replace")
    except Exception:
        text = ""
    return _shape(url, final, status, "ok", text=text, elapsed_ms=ms)


class HyperEdgeBrowser:
    """Rung 3 + sessions + interaction + evidence, one instrument.

    Usage::

        with HyperEdgeBrowser(state_dir="~/.grantforge/browser",
                              evidence_dir="evidence/") as b:
            page = b.goto("https://portal.example/rfps")
            if page["state"] == "blocked":
                ...  # named wall in page["challenge"]; log in by hand once
            b.fill("#q", "NSF AI institutes")
            b.click("button[type=submit]")
            page = b.read()
            b.screenshot("rfp-list")

    The first ``goto`` reuses persisted login state when ``state_dir``
    holds one; call :meth:`save_state` after a manual login and the
    next run inherits it. Playwright imports lazily on first use.
    """

    def __init__(self, state_dir=None, evidence_dir=None, headless=True,
                 timeout_s=TIMEOUT_S, politeness_s=POLITENESS_S):
        self.state_dir = os.path.expanduser(state_dir) if state_dir else None
        self.evidence_dir = evidence_dir
        self.headless = headless
        self.timeout_s = timeout_s
        self.politeness_s = politeness_s
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._last_nav = 0.0

    # -- lifecycle ----------------------------------------------------
    def _ensure(self):
        if self._page is not None:
            return self._page
        sync_playwright = _require_playwright()
        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch(headless=self.headless)
        except Exception:
            self._browser = self._pw.chromium.launch(
                headless=self.headless, channel="chrome")
        kwargs = {"user_agent": BROWSER_UA}
        if self.state_dir:
            os.makedirs(self.state_dir, exist_ok=True)
            state_file = os.path.join(self.state_dir, "storage_state.json")
            if os.path.exists(state_file):
                kwargs["storage_state"] = state_file
        self._context = self._browser.new_context(**kwargs)
        self._page = self._context.new_page()
        return self._page

    def save_state(self):
        """Persist current login state into ``state_dir`` for next run."""
        if not self.state_dir:
            raise RuntimeError("save_state needs state_dir")
        self._ensure()
        os.makedirs(self.state_dir, exist_ok=True)
        dest = os.path.join(self.state_dir, "storage_state.json")
        self._context.storage_state(path=dest)
        return dest

    def close(self):
        for obj in (self._page, self._context, self._browser):
            try:
                if obj is not None:
                    obj.close()
            except Exception:
                pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass
        self._page = self._context = self._browser = self._pw = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    # -- navigation ---------------------------------------------------
    def _polite(self):
        wait = self.politeness_s - (time.perf_counter() - self._last_nav)
        if wait > 0:
            time.sleep(wait)
        self._last_nav = time.perf_counter()

    def goto(self, url):
        """Render a URL with JS; returns the shaped result dict."""
        page = self._ensure()
        self._polite()
        start = time.perf_counter()
        try:
            resp = page.goto(url, timeout=int(self.timeout_s * 1000),
                             wait_until="domcontentloaded")
            try:
                page.wait_for_timeout(RENDER_SETTLE_MS)
            except Exception:
                pass
            status = resp.status if resp is not None else 0
            final = page.url
            title = ""
            try:
                title = page.title() or ""
            except Exception:
                pass
            try:
                text = page.evaluate(
                    "() => document.body ? document.body.innerText : ''")
            except Exception as e:
                text = ""
                return _shape(url, final, status, "error",
                              detail="extract failed: %s" % str(e)[:160],
                              elapsed_ms=int(
                                  (time.perf_counter() - start) * 1000))
        except Exception as e:
            ms = int((time.perf_counter() - start) * 1000)
            return _shape(url, url, 0, "error", detail=str(e)[:200],
                          elapsed_ms=ms)
        ms = int((time.perf_counter() - start) * 1000)
        challenge = detect_challenge(status, {}, text)
        if challenge:
            return _shape(url, final, status, "blocked", title=title,
                          challenge=challenge,
                          detail="named wall after render: %s" % challenge,
                          elapsed_ms=ms)
        return _shape(url, final, status, "ok", text=text or "",
                      title=title, elapsed_ms=ms)

    def read(self):
        """Re-read the current page (after fills/clicks); shaped dict."""
        if self._page is None:
            return _shape("", "", 0, "error", detail="no page yet")
        url = self._page.url
        try:
            title = self._page.title() or ""
        except Exception:
            title = ""
        try:
            text = self._page.evaluate(
                "() => document.body ? document.body.innerText : ''")
        except Exception as e:
            return _shape(url, url, 0, "error",
                          detail="extract failed: %s" % str(e)[:160])
        challenge = detect_challenge(200, {}, text or "")
        if challenge:
            return _shape(url, url, 200, "blocked", title=title,
                          challenge=challenge,
                          detail="named wall after interaction: %s"
                          % challenge)
        return _shape(url, url, 200, "ok", text=text or "", title=title)

    # -- interaction --------------------------------------------------
    def fill(self, selector, value, submit=False):
        """Fill a form field; optionally press Enter after."""
        page = self._ensure()
        self._polite()
        page.fill(selector, value)
        if submit:
            page.press(selector, "Enter")
            try:
                page.wait_for_timeout(RENDER_SETTLE_MS)
            except Exception:
                pass

    def click(self, selector):
        """Click and let the page settle; follow with :meth:`read`."""
        page = self._ensure()
        self._polite()
        page.click(selector)
        try:
            page.wait_for_timeout(RENDER_SETTLE_MS)
        except Exception:
            pass

    # -- evidence -----------------------------------------------------
    def screen(self):
        """Run the native bypass-kit screen over the current page text."""
        if self._page is None:
            return {"state": "error", "findings": [],
                    "detail": "no page yet"}
        try:
            text = self._page.evaluate(
                "() => document.body ? document.body.innerText : ''")
        except Exception as e:
            return {"state": "error", "findings": [],
                    "detail": "extract failed: %s" % str(e)[:160]}
        return screen_text(text or "")

    def score(self, query, seed=7):
        """Score the current page's relevance to `query` (str or terms)."""
        if self._page is None:
            return 0.0
        try:
            text = self._page.evaluate(
                "() => document.body ? document.body.innerText : ''")
        except Exception:
            return 0.0
        terms = query.split() if isinstance(query, str) else list(query)
        return RelevanceScorer(seed=seed).score_page(text or "", terms)

    def screenshot(self, name):
        """Capture the current page into ``evidence_dir``; returns path."""
        if not self.evidence_dir:
            raise RuntimeError("screenshot needs evidence_dir")
        self._ensure()
        os.makedirs(self.evidence_dir, exist_ok=True)
        safe = _parse.quote(name, safe="")[:80] or "page"
        dest = os.path.join(
            self.evidence_dir,
            "%s_%s.png" % (time.strftime("%Y%m%d_%H%M%S"), safe))
        self._page.screenshot(path=dest)
        return dest


# ---------------------------------------------------------------------
# NATIVE MellifluousML: seeded lego-block relevance scorer, stdlib only.
#
# In the Mellifluous spirit: deterministic (one seeded stream, so a
# score reproduces bit-for-bit from the seed alone), perfectly-formed
# (dim mismatches raise with both sides named), stdlib-only (no numpy,
# no torch -- the heavy-dep paradigm bypassed completely). The query
# prior carries a fixed positive weight so relevance rises strictly
# with query overlap; the seeded net contributes a bounded adjustment.
# ---------------------------------------------------------------------

_RFP_MARKS = ("deadline", "due date", "eligibility", "award",
              "budget", "submit", "proposal", "rfp", "solicitation")


def featurize(text, query_terms):
    """Six fixed features: [overlap, length, headings, links, lists, rfp]."""
    body = text or ""
    low = body.lower()
    terms = [t.lower() for t in (query_terms or []) if t]
    overlap = sum(1 for t in terms if t in low) / max(1, len(terms))
    lines = body.splitlines() or [""]
    n_lines = len(lines)
    headings = sum(1 for ln in lines if ln.lstrip().startswith("#"))
    links = low.count("http") + low.count("](")
    listish = sum(1 for ln in lines
                  if ln.lstrip()[:2] in ("- ", "* ", "1.", "2.", "3."))
    rfp = sum(low.count(m) for m in _RFP_MARKS)
    return [overlap,
            min(len(body) / 8000.0, 1.0),
            min(headings / n_lines * 10.0, 1.0),
            min(links / 50.0, 1.0),
            min(listish / n_lines * 10.0, 1.0),
            min(rfp / 20.0, 1.0)]


class _Dense:
    """Seeded fully-connected block: owns W (out x in) and b (out)."""

    def __init__(self, in_dim, out_dim, seed):
        if in_dim < 1 or out_dim < 1:
            raise ValueError("dense dims must be >= 1, got %d -> %d"
                             % (in_dim, out_dim))
        rng = random.Random(seed)
        bound = math.sqrt(6.0 / (in_dim + out_dim))
        self.in_dim = in_dim
        self.out_dim = out_dim
        self.W = [[rng.uniform(-bound, bound) for _ in range(in_dim)]
                  for _ in range(out_dim)]
        self.b = [rng.uniform(-bound, bound) for _ in range(out_dim)]

    def forward(self, x):
        if len(x) != self.in_dim:
            raise ValueError("dense %d->%d got input len %d"
                             % (self.in_dim, self.out_dim, len(x)))
        return [sum(w * v for w, v in zip(row, x)) + b
                for row, b in zip(self.W, self.b)]


class RelevanceScorer:
    """Native relevance scorer: fixed query prior + bounded net adjust."""

    def __init__(self, seed=7, query_weight=2.0):
        self.seed = seed
        self.query_weight = query_weight
        self.hidden = _Dense(5, 4, seed)
        self.head = _Dense(4, 1, seed + 1)

    def score(self, features):
        """Score a 6-vector from :func:`featurize`; strictly rises with
        features[0] (query overlap), lives in (0, 1), reproduces from
        the seed alone."""
        if len(features) != 6:
            raise ValueError("scorer needs 6 features, got %d"
                             % len(features))
        overlap = features[0]
        hidden = [math.tanh(v)
                  for v in self.hidden.forward(features[1:])]
        adjust = self.head.forward(hidden)[0]
        adjust = max(-3.0, min(3.0, adjust))
        logit = self.query_weight * overlap + adjust
        return 1.0 / (1.0 + math.exp(-logit))

    def score_page(self, text, query_terms):
        """Featurize `text` against `query_terms`, then score."""
        return self.score(featurize(text, query_terms))


# ---------------------------------------------------------------------
# NATIVE bypass-kit: adversarial screen over extracted page text.
#
# The kit's contract, kept: a probe that fires is a finding -- record
# it, never silently drop the page, never auto-patch the text. Probes
# cover instruction smuggles, section spoofs, path escapes, unicode
# tricks, and oversized blobs. Pure stdlib, no browser needed.
# ---------------------------------------------------------------------

_OVERSIZE_CHARS = 200000

_SMUGGLE_RES = (
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"you\s+are\s+now\s+(a|an|the)",
    r"new\s+instructions?\s*:",
    r"^\s*(system|assistant|developer)\s*:",
    r"\[SYSTEM\]",
    r"<<\s*SYS\s*>>",
)
_PATH_MARKS = ("../", "..\\", "%2e%2e", "file://")
_BIDI_CHARS = ("\u202e", "\u202a", "\u202b", "\u2066",
               "\u2067", "\u2068")
_ZERO_WIDTH = ("\u200b", "\u200c", "\u200d", "\ufeff")
_SPOOF_HEAD = re.compile(r"^#{1,6}\s+.*(system|prompt|instruction|override)",
                         re.IGNORECASE)


def _excerpt(text, at, radius=40):
    frag = text[max(0, at - radius):at + radius].replace("\n", " ")
    return frag[:120]


def screen_text(text):
    """Screen extracted text; ``clean`` or ``suspect`` with findings."""
    body = text or ""
    findings = []
    for pattern in _SMUGGLE_RES:
        try:
            for m in re.finditer(pattern, body,
                                 re.IGNORECASE | re.MULTILINE):
                findings.append({"probe": "instruction-smuggle",
                                 "detail": pattern,
                                 "excerpt": _excerpt(body, m.start())})
                break
        except re.error:
            continue
    for ln in body.splitlines():
        if _SPOOF_HEAD.match(ln):
            findings.append({"probe": "section-spoof",
                             "detail": "heading claims system/prompt role",
                             "excerpt": ln.strip()[:120]})
            break
    low = body.lower()
    for mark in _PATH_MARKS:
        at = low.find(mark.lower())
        if at >= 0:
            findings.append({"probe": "path-escape",
                             "detail": mark,
                             "excerpt": _excerpt(body, at)})
            break
    for ch in _BIDI_CHARS:
        if ch in body:
            findings.append({"probe": "unicode-trick",
                             "detail": "bidi control U+%04X" % ord(ch),
                             "excerpt": _excerpt(body, body.find(ch))})
            break
    for ch in _ZERO_WIDTH:
        if ch in body:
            findings.append({"probe": "unicode-trick",
                             "detail": "zero-width U+%04X" % ord(ch),
                             "excerpt": _excerpt(body, body.find(ch))})
            break
    if len(body) >= _OVERSIZE_CHARS:
        findings.append({"probe": "oversized",
                         "detail": "%d chars" % len(body),
                         "excerpt": ""})
    return {"state": "suspect" if findings else "clean",
            "findings": findings}
