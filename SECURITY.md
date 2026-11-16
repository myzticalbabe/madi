# Security Policy

## Reporting a vulnerability

Do **not** open a public issue for a security problem.

Use GitHub's private reporting: **Security** tab → **Report a vulnerability**.

If that form is unavailable — private vulnerability reporting is a repository setting
and may not be switched on for every repository — contact
[@myzticalbabe](https://github.com/myzticalbabe) directly instead. Either route reaches
the same single maintainer; neither requires an account on a mailing list.

Include what you did, what happened, and what you expected. A proof of concept is
helpful but not required.

Expect an acknowledgement within 7 days. This is a single-maintainer project, so
please allow time before escalating.

## Supported versions

`madi` is pre-1.0. There are no maintained release branches; fixes land on `main` and
ship in the next release.

| Version | Supported |
| --- | --- |
| `0.1.x` (current) | Yes |
| `main` (development) | Yes |
| `< 0.1.0` | No |

## What this project handles

`madi` is a library. It runs inside the caller's process, has no server, no accounts,
no database, and no telemetry. It makes outbound HTTP requests, but only the ones the
caller explicitly asks for.

That makes the realistic risk surface narrower than it first looks:

| Surface | Reality |
|---|---|
| Data collected | None. `madi` collects nothing and sends nothing anywhere except the URLs the caller passes in. |
| Storage | None of its own. The only file it writes is the browser state file described below. |
| Network egress | Only to the URLs the caller requests, plus Playwright's own browser downloads. |
| Cookies | Only those the caller chooses to persist via `HyperEdgeBrowser.save_state`. |
| Backend / API | None. There is no server in this repository. |
| Secrets | None in the repository itself. The browser state file can hold session credentials — see below. |

The realistic risk surface is therefore supply chain and untrusted page content, not
data breach:

1. **Untrusted HTML** — `src/madi/browser.py` parses pages that come from the open
   internet. `main_text` and `discover_html` consume whatever the page contains, and
   `discover_html` resolves link targets with `urljoin`, so a hostile page controls the
   URLs and form fields that come back to the caller. Parser bugs that let untrusted
   content escape into a caller's context are in scope. The adversarial screen in
   `screen_text` exists because this content is treated as hostile by design; reports
   that a probe should have fired but did not are in scope.
2. **Persisted browser state** — `HyperEdgeBrowser.save_state` writes
   `storage_state.json`, which contains cookies and session tokens, into the directory
   the caller names as `state_dir`. If a caller points `state_dir` at a shared or
   committed directory, those credentials are exposed. In scope: any way `madi` writes
   that file outside the directory the caller chose, or makes it world-readable.
3. **The CI workflows** — `.github/workflows/*.yml` run on push and on pull requests.
   Workflow-level issues (unpinned actions, script injection through a branch name or
   issue title) are in scope.
4. **Dependencies** — the `browser` extra installs Playwright and the `test` extra
   installs pytest. Dependency review and a malicious or compromised package are in
   scope.

Out of scope: reports that require the user to have already modified their own copy of
the code, reports about the hosts `madi` fetches from rather than about `madi` itself,
and reports about the GitHub Pages host.

## Hardening rules for contributors

- Keep the core standard-library-only. A new runtime dependency changes the
  installation story for every caller; put it behind an extra and keep the import
  lazy.
- Keep Playwright imports lazy and keep the `RuntimeError` message naming what to
  install.
- Never log or persist a URL, a cookie, or a token that the caller did not ask you to
  persist.
- Write browser state only under the `state_dir` the caller gave you.
- Pin GitHub Actions to a commit SHA, not a tag.
- Never interpolate an untrusted value into `run:` in a workflow.
