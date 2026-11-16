# STEM learning guide — madi

MADI is the browsing instrument: fetch, a challenge taxonomy, readability scoring, discovery, and a native scorer.

This guide is for teachers, mentors, club leaders, parents and students who want to
use this repository as a vehicle for real STEM learning — in particular for girls and
other groups still under-represented in computing, engineering and mathematics. It
says what the project actually teaches, how to run a session with it, and what to
remove so that nobody is excluded by accident.

## What this project teaches

**Subject areas**

- web retrieval
- text analysis
- readability metrics
- classification

**Skills practised**

- measuring instead of asserting ("it reads badly" becomes a number)
- building a taxonomy and testing it against real pages
- recognising when a metric is the wrong metric

## Prerequisites

Python 3.13. Fixture pages are included, so no live internet access is required for the exercises.

Nothing else is assumed for the entry-level activity below: no prior programming
experience, no particular hardware, and no home internet connection.

## Six practices this repository is set up to support

These follow the published guidance on gender-equitable STEM education — connect the
work to learners' lives, let them investigate real problems, treat struggle as part of
the work, name and challenge stereotypes, make the work collaborative, and put
learners in front of diverse role models.

1. **Connect it to their lives.** the reading-level of a school letter, a news article, or a terms-of-service page — and who that excludes
2. **Let them investigate.** give the group three pages on one topic and ask which is hardest to read, then compare with the score
3. **Make struggle normal.** Build the session so that the first attempt is *expected*
   to fail. Say out loud that debugging is the subject, not a penalty. Ask "what did
   that error tell you?" before offering the answer.
4. **Challenge the stereotype.** Name who does this work and why it is not a gendered
   skill. Praise the method ("you isolated the variable"), not the person ("you're a
   natural") — the second kind of praise teaches learners that ability is fixed.
5. **Make it social.** pairs score each other's writing and have to defend the number
6. **Show diverse role models.** researchers in information retrieval and in plain-language communication

## A 90-minute session

1. *(15 min)* Score three fixture pages by hand with the formula.
2. *(25 min)* Run the tool; find where the number disagrees with the group's judgement.
3. *(35 min)* Add one taxonomy category and a test for it.
4. *(15 min)* Rewrite the hardest fixture at a lower score and compare.

## Vocabulary to define before the session

Specialist vocabulary is a hidden entry test if nobody explains it. Define each of
these the first time it appears, in one sentence, in the learners' own words:

1. **readability score** — a number estimating reading difficulty.
2. **taxonomy** — the named categories a page can fall into.
3. **fixture** — a saved page used for testing.

## Accessibility

Read [ACCESSIBILITY.md](ACCESSIBILITY.md) before running a session. Two rules matter
most in a mixed-ability room:

- Every activity must be completable with a keyboard alone, with a visible focus ring.
- Every instruction names the control or the heading ("the **Run** button in the
  toolbar"), never a colour or a position.

Pair learners rather than singling anyone out, and always offer a text-only route for
a visual step.

## Contributing as a learner

Small, well-scoped contributions are the point, not a consolation prize:

- Browse issues labelled
  [`good first issue`](https://github.com/myzticalbabe/madi/labels/good%20first%20issue).
- Read [CONTRIBUTING.md](CONTRIBUTING.md) — it has a section written for first-time
  contributors.
- Ask in [SUPPORT.md](SUPPORT.md) if anything is unclear. Asking is expected here; it
  is not a failure.

## Licence and classroom reuse

Classroom, club and workshop use is welcome. See `LICENSE` for the exact terms, and
check whether your institution requires a separate agreement before redistributing
modified copies.
