"""
The maintainer's command for the extended quota (docs/decisions/2026-10-19-funding-and-quota.md).
It runs on the server with database access, so there is no HTTP route and no admin role:

    python -m src.bootstrap.quota_admin grant someone@school.org --days 90
    python -m src.bootstrap.quota_admin revoke someone@school.org

The grant counts from now (it replaces an earlier deadline) and starts with a full quota.
"""
import argparse
import asyncio
import sys
from collections.abc import Sequence

import structlog

from src.bootstrap.connections import close_connections
from src.bootstrap.container import Container
from src.modules.quota import MAX_GRANT_DAYS, GrantExtendedQuotaInputDTO
from src.shared.domain import UserNotFoundError

log = structlog.stdlib.get_logger()


def _days(value: str) -> int:
    days = int(value)
    if not 1 <= days <= MAX_GRANT_DAYS:
        raise argparse.ArgumentTypeError(f"must be between 1 and {MAX_GRANT_DAYS}")
    return days


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.bootstrap.quota_admin", description=__doc__.split("\n\n")[0])
    actions = parser.add_subparsers(dest="action", required=True)
    grant = actions.add_parser("grant", help="grant the extended quota")
    grant.add_argument("email")
    grant.add_argument("--days", type=_days, required=True, help=f"1 to {MAX_GRANT_DAYS}")
    revoke = actions.add_parser("revoke", help="back to the standard quota now")
    revoke.add_argument("email")
    return parser


async def run(container: Container, argv: Sequence[str]) -> str:
    """Runs one action and returns what to tell the maintainer. Raises `UserNotFoundError`."""
    args = _parser().parse_args(argv)
    user_id = await container.identity.directory().id_by_email(args.email)
    if args.action == "grant":
        quota = await container.quota.grant_extended_quota().execute(
            GrantExtendedQuotaInputDTO(user_id=user_id, days=args.days),
        )
        until = container.calendar().date_of(quota.expires_at)
        log.info("plante.quota.extended_granted", user_id=str(user_id), expires_at=quota.expires_at.isoformat())
        return f"Extended quota for {args.email} until {until.isoformat()} (local day)."
    await container.quota.revoke_extended_quota().execute(user_id)
    log.info("plante.quota.extended_revoked", user_id=str(user_id))
    return f"{args.email} is back to the standard quota."


def main(argv: Sequence[str] | None = None) -> int:
    container = Container()

    async def _run_and_close() -> str:
        try:
            return await run(container, sys.argv[1:] if argv is None else argv)
        finally:
            await close_connections(container)

    try:
        message = asyncio.run(_run_and_close())
    except UserNotFoundError as exc:
        print(exc.message, file=sys.stderr)
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
