## What changed

<!-- One or two sentences. Link the issue this closes, if any. -->

## Why

<!-- The problem this solves. "Because the linter said so" is not a reason. -->

## How it was checked

<!-- The commands you ran, and their result. "Not run" is an acceptable answer if explained. -->

## Checks

- [ ] The change is focused; unrelated cleanup is in a separate pull request
- [ ] Existing checks pass (or the failure is explained above)
- [ ] New behaviour is covered by a test, or the reason it is not is stated
- [ ] Documentation is updated if behaviour or usage changed
- [ ] `python -m pytest tests/ -v --tb=short` passes on Python 3.13 or newer
- [ ] If the change touches the render rung, `MADI_LIVE_BROWSER=1` was run — or the
      reason it could not be is stated above
- [ ] The core still imports without Playwright installed
- [ ] No new runtime dependency outside an optional extra

## If this touches learner-facing content

<!-- This repository holds no learner-facing pages today. Tick these only if your
     change adds an example, a demo, or teaching material. -->

- [ ] Keyboard-navigable, with visible focus
- [ ] Every image or canvas has a text alternative
- [ ] New terms are defined the first time they appear
- [ ] Reading level suits the intended age group
