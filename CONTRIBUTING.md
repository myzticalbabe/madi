# Contributing

Thanks for taking an interest in `madi`. It is part of the
[Azazael](https://github.com/myzticalbabe) ecosystem, a set of repositories for
education and research tooling.

`madi` is a small Python library with a standard-library-only core: it fetches a page
with real browser headers, classifies the response as `ok`, `blocked` (naming the
challenge — cloudflare, captcha, imperva, bot-wall) or `error`, then extracts readable
text, scores it for relevance, and screens it for adversarial content. Playwright is
an optional extra, needed only for the render and interact rung.

## Before you start

- Read the project `README.md` for what the repository actually does and how to run it.
- Search the existing issues and pull requests — the change you want may already be
  discussed.
- For anything larger than a typo or a one-line fix, open an issue first so the design
  can be agreed before code is written.

## Set up your development environment

`madi` requires **Python 3.13 or newer**; `pyproject.toml` declares
`requires-python = ">=3.13"`.

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

Then install the package in editable mode together with the test dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

The library itself has **no runtime dependencies**. The command above only adds
`pytest`, which is what the test suite needs.

The render and interact rung additionally needs Playwright and a Chromium build:

```bash
python -m pip install -e ".[browser]"
playwright install chromium
```

Playwright is imported lazily. Importing `madi` never requires it, and every render
path raises a `RuntimeError` naming exactly what to install.

## Run the checks

This is the command CI runs, and the one to run before every pull request:

```bash
python -m pytest tests/ -v --tb=short
```

The suite is offline-safe: it uses a local HTTP server on `127.0.0.1` and never
touches the internet. One test is skipped unless you ask for it:

```bash
MADI_LIVE_BROWSER=1 python -m pytest tests/ -v --tb=short
```

That test drives a real Chromium against `example.com`, so it needs Playwright
installed and network access. If it cannot run in your environment, say so in the
pull request rather than deleting or skipping the step.

## Ways to contribute that are not code

- Report a bug with a minimal reproduction.
- Improve the documentation or add an example.
- Report an accessibility problem (keyboard traps, missing text alternatives,
  unreadable contrast).
- Review a pull request and say what confused you — that is real feedback.

## Making a change

1. Fork the repository and create a branch: `git checkout -b fix/short-description`.
2. Keep the change focused. Unrelated refactors belong in a separate pull request.
3. Match the surrounding style; do not reformat whole files to make a small fix.
4. Run the checks the project documents in its `README.md` or `.github/workflows`.
   If a check cannot run in your environment, say so in the pull request instead of
   deleting the step.
5. Write a commit message that explains *why* the change was made.
6. Open the pull request and fill in the template.

## Reporting bugs

A good report contains:

- what you expected to happen and what happened instead;
- the exact command, page, or input that triggers it;
- the full error output, not a paraphrase;
- your operating system and runtime versions.

Use the **Bug report** issue form. It asks for the same four things.

## Learner-facing content

This repository holds no learner-facing pages today — it is a library, not a course.
If your change adds an example, a demo, or any teaching material, then:

- keep the reading level age-appropriate and define any new term the first time it is
  used;
- keep the layout keyboard-navigable and give every image or canvas a text alternative;
- avoid examples that assume prior exposure to programming.

## Code of conduct

Participation is covered by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Be kind; assume
good faith.

## Licence

By contributing you agree that your contribution is licensed under the same licence as
the repository. See [LICENSE](LICENSE).
