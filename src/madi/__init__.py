# coding: utf-8
"""Madi -- the one browsing instrument.

Stdlib-only core (fetch, challenge taxonomy, readability, discovery,
native scorer, native screen); Playwright render rung optional.
"""

from .browser import (
    BROWSER_HEADERS,
    BROWSER_UA,
    HyperEdgeBrowser,
    RelevanceScorer,
    detect_challenge,
    discover_html,
    fetch,
    featurize,
    main_text,
    playwright_available,
    screen_text,
)

__version__ = "0.1.0"

__all__ = [
    "HyperEdgeBrowser",
    "BROWSER_HEADERS",
    "BROWSER_UA",
    "RelevanceScorer",
    "detect_challenge",
    "discover_html",
    "fetch",
    "featurize",
    "main_text",
    "playwright_available",
    "screen_text",
    "__version__",
]
