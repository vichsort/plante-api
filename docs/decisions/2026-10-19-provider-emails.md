# Emails to the identification providers

Decided on 2026-10-19: before the label engine uses anything the providers return, ask them. Not
sent yet; the maintainer sends them when ready ("depois, calma"). The reading of the terms below
is ours, not legal advice: that is exactly why we ask.

Related: the terms table in `src/modules/training/README.md` and the funding decision in
`2026-10-19-funding-and-quota.md`.

## Before sending

- [ ] Paid plan replaced by donations (the quota refactor): the email can say there is no paid
      tier, which is what makes the research request credible.
- [ ] Project email (e.g. contato@planteai.org), not a personal one.
- [ ] An "About" page on planteai.org to link: origin in a class project of the maintainer's
      technical course, non-profit, open source (MIT), what the model is for.

## How to present PlantE (both emails)

- Educational, open source project born in a class of a technical course; for study and for the
  scientific community, not for profit.
- No paid tier: donations only pay for the provider credits and the infrastructure, and the
  expenses are public.
- Everything stays open: code, and the dataset and model when they exist. No private app.
- Privacy by design: the training dataset is anonymous from the moment it is written.
- Planned: a presentation at a science fair (Latinoware).
- Short and specific: name the clauses and ask yes/no questions they can answer.

## Kindwise (FlowerChecker s.r.o.)

**Contact:** support@FlowerChecker.com (the address their T&C name for all communication).
**Source:** [API Terms and Conditions, v3](https://www.kindwise.com/terms-and-conditions).

Why we ask:

- **17.3.3:** the client may not use the services "to develop his/her own automatized system,
  program or application based on the same principle as FlowerChecker Digital Services". A plant
  identifier of our own is that.
- **17.4.1:** photos in the output (the similar images) may only be used to process the answer for
  the end users of the application.
- **17.6:** the parties may agree on other license terms, so a research license is possible.
- **17.5** (the other direction): they hold an irrevocable license to the photos we send, may use
  them for machine learning and may share them under CC BY-SA 4.0 (faces blurred). This goes into
  our consent text whatever they answer.

Questions:

1. May an educational, non-profit, open source project train its own plant identification model
   on its users' photos, using your identification answers as labels?
2. May the similar images returned by the API be used as labeled training data, keeping each
   image's license and attribution?
3. If neither is allowed under the current terms, do you offer a research or academic license
   (17.6)? Under what conditions?
4. Do you have an academic or non-profit program for credits?

## PlantNet (CIRAD, on behalf of the Pl@ntNet partners)

**Contact:** contact@plantnet-project.org.
**Sources:** [using images](https://my.plantnet.org/doc/references/using-images),
[API access agreement v4](https://my.plantnet.org/documents/agreement_PlantNet_API_english_v4.pdf).

Why we ask:

- Images are under CC BY, CC BY-SA or public domain; internal and commercial use is allowed citing
  the source and the owner ("Contributor / Pl@ntNet, CC BY-SA"). Any other use needs CIRAD's
  written consent. Nothing explicit about training.
- ShareAlike applied to a trained model is a gray area.
- The agreement we read is the paid one; we use the free plan, whose terms we have not checked.

Questions:

1. May the images returned by the identification API be used to train an open, non-profit plant
   identification model, keeping each image's license and attribution?
2. For CC BY-SA images: what do you expect from a trained model and the dataset (same license for
   the published dataset? for the model weights?)
3. Which terms apply to the free API plan, and do they allow this use?
4. Would you be open to a partnership (e.g. sharing back our anonymous, licensed dataset of
   Brazilian plants)?

## Status

| Provider | Sent | Answer |
| :--- | :--- | :--- |
| Kindwise | no | — |
| PlantNet | no | — |

Until there are answers, the label engine uses neither provider's images, and Kindwise answers
are not used as training labels.
