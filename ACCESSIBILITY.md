# Accessibility

Accessibility is a condition of this project being usable in a classroom, not a
nice-to-have. This page states what we aim for, what has actually been tested, what we
already know is broken, and how to report a barrier.

## Target

We work toward **WCAG 2.2 Level AA** for anything a person reads or operates. That is a
goal that guides the work; it is not a claim of verified conformance.

## Priorities

- **Keyboard first.** Every interactive element is reachable and operable with a
  keyboard alone, with a visible focus indicator and a logical tab order.
- **Screen reader support.** Content uses semantic structure and a logical heading
  hierarchy so it can be navigated with NVDA, JAWS and VoiceOver.
- **Plain language.** Short sentences, defined terms, descriptive link text, and no
  meaning carried by colour alone.
- **Text before pictures.** A diagram is always accompanied by the same information in
  text, because a screenshot of a user interface cannot be read aloud.

## What has actually been tested

No automated accessibility checks. Output is terminal text and scores.

## Known barriers

Scores are presented without the threshold that gives them meaning; a reader must remember the scale.

## Reporting a barrier

Open an issue at <https://github.com/myzticalbabe/madi/issues/new> and include:

- your operating system and runtime version;
- the assistive technology you were using, if any;
- the step you were on, and what you expected instead;
- whether the barrier blocks the task or only slows it down.

An accessibility issue is not a cosmetic issue. If a keyboard trap blocks a workflow,
we treat that with the same priority as a crash.

## For contributors

- A change to any interface must be operable by keyboard before it is merged.
- New images, diagrams and canvases need a text alternative.
- Do not use colour alone to convey state.
- Do not "fix" an accessibility report by removing the feature.
