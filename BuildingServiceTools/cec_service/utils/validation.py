"""Validation helpers for input values."""


class ValidationError(ValueError):
    """Raised when validation fails."""


def pos_or_none(val: float | None, field: str) -> float | None:
    """Return value if positive or None; raise otherwise."""
    if val is None:
        return None
    if val < 0:
        raise ValidationError(f"{field} must be positive")
    return val
