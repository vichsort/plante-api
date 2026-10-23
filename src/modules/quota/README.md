# quota

## Propósito

How much AI each user may spend, and how much the whole service may spend
(`docs/decisions/2026-10-19-funding-and-quota.md`):

- **Quota level per user:** `standard` for everyone; `extended`, granted by the maintainer on
  request, never for payment. There is no paid plan and no upgrade route.
- **Daily tokens per user**, which the AI actions spend.
- **The service's daily limit** of calls to the paid providers, however many accounts there are.

All of it protects the providers' credits (Kindwise, Gemini), so it is real rule, not decoration.

Out of scope: payment, and knowing whether the user exists. This is a base module; the identity owns
the account, and here there is only the FK to `users`.

## API pública

`src.modules.quota` exports domain only:

- **`ITokenWallet`**: the user's daily tokens, for whoever spends AI (identification, diagnosis):
  1. check the balance before the expensive calls (`ensure_can_identify`, `ensure_can_diagnose`,
     `can_enrich_diagnosis`);
  2. call the providers outside the transaction;
  3. charge with `charge`, **inside the caller's transaction**, together with what was delivered.

  Called outside a transaction, `charge` raises instead of losing the charge silently.
- **`IProviderBudget`**: the service's daily limit. `take(now)` right before calling the provider,
  after the user's own checks.
- **`IGardenQuota`**: the garden's plant limit for the active level.
- **Types:** `Quota`, `QuotaLevel`, `QuotaLimits`/`LevelLimits`, `FeatureCost`,
  `GrantExtendedQuotaInputDTO`/`MAX_GRANT_DAYS` and the errors below.

The module has no routes. The composition builds it through `src.modules.quota.container`; the
maintainer's command is `src.bootstrap.quota_admin` (`grant`/`revoke`). The doubles for tests live
in `tests/fakes.py`, with the real rules.

## Decisões

- **No row = `standard` with a full quota.** Signing up does not call this module; the row is born
  on the first charge or grant.
- **The active level counts:** an expired `extended` counts as `standard` (`Quota.active_level`).
  A grant lasts up to `MAX_GRANT_DAYS` (365), counts from now and starts with a full quota; a
  revoke goes back to `standard` at once, and today's tokens stay spent.
- **Limits come from the settings** (`QUOTA_STANDARD_*`, `QUOTA_EXTENDED_*`): a collective goal
  raises `standard` without touching code. Defaults: `standard` 3 tokens a day and 3 plants;
  `extended` 10 and 10.
- **Daily tokens on the local day** (`LocalCalendar`, `LOCAL_TIMEZONE`), with no cron. `tokens_day`
  keeps the day the counter refers to, and the first charge of a new day starts from zero.
  - Costs: identify 1; diagnosis 1, plus 1 for Gemini's add-on (called only if both fit, and
    charged only if delivered); deep analysis 2 (the feature does not exist yet).
- **The charge locks the row** (`INSERT … ON CONFLICT DO NOTHING` + `SELECT … FOR UPDATE`): two
  simultaneous identifications cannot read the same balance and overwrite each other's charge.
- **Missing account:** the table's only FK is to `users`, so its violation becomes
  `UserNotFoundError` (from the kernel), without this module importing the identity.
- **Check the balance before, charge after.** Two simultaneous requests may both pass the check
  with the last token; the second charge goes 1 over. Accepted: locking the row during the AI calls
  would hold a connection for seconds.
- **The service's daily limit** (`PROVIDER_DAILY_LIMIT`, default 30): identifications and diagnoses
  (1 Kindwise credit each) per local day, counted in Redis (`plante:usage:provider_calls:<day>`,
  shared by every API process, expires in two days).
  - The per-user quota does not cover it: throwaway accounts each bring their own tokens.
  - Counted before the call: a provider failure still spends one (conservative). Gemini is not
    counted (separate, degradable add-on).
  - Redis down fails closed (`ServiceUnavailableError`): no count, no paid call.

## Erros

| Código | Erro | HTTP | Quando |
| :--- | :--- | :---: | :--- |
| `PLANTE_4220_PLANT_LIMIT_REACHED` | `PlantLimitExceededError` | 403 | The active level (`extended` too) reached the garden's plant limit. `details`: `quota`, `current_count`, `max_allowed`. |
| `PLANTE_4250_DAILY_QUOTA_EXCEEDED` | `DailyQuotaExceededError` | 429 | The active level's tokens for today (`extended` too) are not enough for the action; they renew the next day. `details`: `quota`, `used_today`, `daily_limit`. |
| `PLANTE_4251_SERVICE_DAILY_LIMIT_REACHED` | `ServiceDailyLimitError` | 429 | The whole service spent today's identifications and diagnoses; they renew the next day. `details`: `daily_limit`. |
