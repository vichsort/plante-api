from src.shared.domain import PlantEError


class PlantLimitExceededError(PlantEError):
    """The active quota has no room for another plant in the garden (extended included)."""
    code = "PLANTE_4220_PLANT_LIMIT_REACHED"
    status_code = 403

    def __init__(self, quota: str, current_count: int, max_allowed: int):
        super().__init__(
            message=f"The {quota} quota allows up to {max_allowed} plants in the garden.",
            details={"quota": quota, "current_count": current_count, "max_allowed": max_allowed},
        )


class DailyQuotaExceededError(PlantEError):
    """The active quota's AI tokens for today are used up (extended included); they renew tomorrow."""
    code = "PLANTE_4250_DAILY_QUOTA_EXCEEDED"
    status_code = 429

    def __init__(self, quota: str, used_today: int, daily_limit: int):
        super().__init__(
            message=f"Daily tokens of the {quota} quota used up ({used_today} of {daily_limit}). They renew tomorrow.",
            details={"quota": quota, "used_today": used_today, "daily_limit": daily_limit},
        )
