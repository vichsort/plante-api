# Funding and quota: no paid plan, quota by request

Decided on 2026-10-19 with the maintainer. The next step is the refactor at the end of this file.

## Context

- PlantE was born from a class project in the maintainer's technical course. It is for study and
  for the scientific community, not for profit. There will never be a private app; everything is
  open and up for discussion.
- The goal is partnerships with open source projects, organizations and NGOs, and maybe presenting
  it at a science fair (Latinoware).
- Money only exists to pay for what the service costs: the identification credits (Kindwise,
  PlantNet, Gemini) and, later, the AWS infrastructure.
- The "Pro" plan was only a demo: there was never a payment, and the upgrade is a flag with a
  deadline.

## Why it matters: what counts as commercial use

Creative Commons "non-commercial" (NC) means a use "primarily intended for or directed toward
commercial advantage or monetary compensation". What decides is the **use**, not the intention or
who uses it. Charging for more usage, even only to cover costs, reads as monetary compensation for
many. A paid tier would:

- keep out of the model that serves the app every NC source (part of Pl@ntNet-300K, iNaturalist,
  whose terms forbid training AI for commercial purposes) — see the terms table in
  `src/modules/training/README.md`;
- weaken the request for a research license from Kindwise (their T&C 17.3.3 forbids building a
  system "based on the same principle"; 17.6 allows agreeing on other terms);
- make the maintainer a seller (consumer protection: refunds, cancellation) and make partners wary.

## Decisions

1. **No paid plan. Donations without any usage perk.**
   - Expenses are public (e.g. Open Collective, which shows every cost), which is also the best
     proof of credibility.
   - Supporters get only a symbolic thanks: a supporters page and a badge on the profile.
   - Donating never grants quota.
2. **Two quota levels, `standard` and `extended`:**
   - **`standard`** is everyone's (today 3 tokens a day and 3 plants). It goes up **for everyone**
     as donations cover the costs (a collective goal shown on the transparency page).
   - **`extended`** is granted **by request, never by payment**: a school, a researcher, an NGO or
     anyone with a use that justifies it asks, and the maintainer grants it for free, case by case,
     with a deadline (e.g. 30 tokens a day for 90 days). When it expires, the user is back to
     `standard` on their own.
   - The client reads the level from the limit errors (`details.quota`), e.g. to show "your
     extended quota lasts until 15/01".
3. **Security bug, fixed on `main` too:** `POST /profile/subscription/upgrade` lets any signed-in
   user give themselves the Pro plan for free, for any number of days (even negative). That turns
   3 tokens a day into 30 and lets anyone spend the Kindwise credits (10 identifications a month on
   the free key). It exists on `main` (`src/api/routers/profile.py`) and on `develop`
   (`src/modules/subscription/api/router.py`).

## The refactor (next step)

One branch, one commit per theme, a pause per milestone.

1. **Hotfix on `main`:** remove the public upgrade route; release `v0.1.3`. It flows down to
   `develop`.
2. **Rename the module `subscription` → `quota`.** Mechanical but wide: imports in garden,
   identification and health, the composition, tests, READMEs and the module map of the error-code
   test. Error numbers do not change (B stays `2`).
3. **`FREE`/`PRO` → `standard`/`extended`.** The database enum values are renamed by migration
   (`ALTER TYPE … RENAME VALUE`, rows untouched); limit errors carry `details.quota` instead of
   `details.plan`; messages say "quota", never "plan" or "subscribe".
4. **Grant by the maintainer, without an HTTP route:** a command such as
   `python -m src.modules.quota.grant <email> --days 90` (and a revoke). It runs on the server with
   database access, so no admin role is needed.
5. **Limits from configuration:** the `standard` (and `extended`) limits come from settings, so the
   collective goal raises them without a code change.
6. **Docs:** module README, error catalog, this file's status.

Open points for the refactor:

- the `extended` limits (keep 30 tokens a day and 50 plants?);
- what replaces `SubscriptionUpgradedEvent` (nobody consumes it today; achievements might later).

## Before publishing (credibility checklist)

- [x] `LICENSE` (MIT) — the README already pointed to it.
- [ ] An "About" page: origin in the technical course, non-profit, what the model is for.
- [ ] Transparency page: donations in, costs out, the collective goal.
- [ ] Privacy policy and terms, with the training consent: photos become an anonymous dataset and
      are sent to identification providers (Kindwise may use them to train and share them under
      CC BY-SA 4.0, T&C 17.5).
- [ ] A project email (e.g. contato@planteai.org) for contacts with providers and partners.
- [ ] Emails to Kindwise (research license, T&C 17.3.3 and 17.6) and PlantNet (training with
      CC BY-SA images), once the maintainer wants to send them.
