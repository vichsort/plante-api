from src.shared.domain import PlantEError


class PlantLimitExceededError(PlantEError):
    """The active plan has no room for another plant in the garden (Pro included)."""
    code = "PLANTE_4220_PLANT_LIMIT_REACHED"
    status_code = 403

    def __init__(self, plan: str, current_count: int, max_allowed: int):
        super().__init__(
            message=f"The {plan} plan allows up to {max_allowed} plants in the garden.",
            details={"plan": plan, "current_count": current_count, "max_allowed": max_allowed},
        )


class DailyQuotaExceededError(PlantEError):
    """The active plan's AI tokens for today are used up (Pro included); they renew tomorrow."""
    code = "PLANTE_4250_DAILY_QUOTA_EXCEEDED"
    status_code = 429

    def __init__(self, plan: str, used_today: int, daily_limit: int):
        super().__init__(
            message=f"Daily quota of the {plan} plan used up ({used_today} of {daily_limit} tokens). It renews tomorrow.",
            details={"plan": plan, "used_today": used_today, "daily_limit": daily_limit},
        )
