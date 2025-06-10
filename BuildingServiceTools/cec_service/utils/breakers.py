"""Breaker size selection utilities."""
from bisect import bisect_left


STANDARD_BREAKERS = [60, 100, 125, 150, 200, 225, 300, 400]


def next_standard_breaker(amps: float) -> int:
    """Return the next standard breaker size in amps."""
    index = bisect_left(STANDARD_BREAKERS, int(round(amps)))
    if index < len(STANDARD_BREAKERS):
        return STANDARD_BREAKERS[index]
    return int(amps + 1)  # round up for values above list
