import random
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationCode:
    """
    Format PLA-XXX-C-XXX, where C is a check digit: the sum of the six other digits, modulo 10.
    Example: PLA-347-5-218 (5 = (3+4+7+2+1+8) % 10).
    """
    raw_code: str

    def __post_init__(self) -> None:
        # Hyphens, spaces and case do not matter
        clean_code = self.raw_code.replace("-", "").strip().upper()
        if not re.match(r"^PLA\d{7}$", clean_code):
            raise ValueError("Verification code in an invalid format.")

        first_part, check_digit, second_part = clean_code[3:6], int(clean_code[6]), clean_code[7:10]
        if check_digit != sum(int(d) for d in first_part + second_part) % 10:
            raise ValueError("Verification code with a wrong check digit.")

        object.__setattr__(self, "raw_code", clean_code)

    @classmethod
    def generate(cls) -> "VerificationCode":
        first = [random.randint(0, 9) for _ in range(3)]
        second = [random.randint(0, 9) for _ in range(3)]
        v = sum(first + second) % 10
        raw = f"PLA-{''.join(map(str, first))}-{v}-{''.join(map(str, second))}"
        return cls(raw)

    def __str__(self) -> str:
        return self.raw_code
