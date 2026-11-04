"""Convert saved R-multiple targets to absolute MT5 target prices, read-only.

These are *candidate* prices only. A future execution adapter must check
symbol tick size and all broker stop/freeze/volume constraints independently.
"""
from decimal import Decimal, InvalidOperation
from typing import Sequence

from rule_engine import Position
from tp_planner import TakeProfitStage


def derive_stages(position: Position, targets_r: Sequence[float],
                  percents: Sequence[int]) -> list[TakeProfitStage]:
    if not (len(targets_r) == len(percents) and 1 <= len(targets_r) <= 3):
        raise ValueError("TP stages must have matching sizes")
    if sum(percents) != 100 or any(type(x) is not int or x <= 0 for x in percents):
        raise ValueError("TP percentages must be positive integers totaling 100")
    try:
        entry = Decimal(str(position.entry))
        stop = Decimal(str(position.original_sl))
        multiples = [Decimal(str(x)) for x in targets_r]
    except (InvalidOperation, ValueError, TypeError) as e:
        raise ValueError("Invalid trading input") from e
    values = [entry, stop, *multiples]
    if not all(x.is_finite() for x in values):
        raise ValueError("Nonfinite trading input")
    if entry <= 0 or stop <= 0 or stop == entry:
        raise ValueError("Initial stop-loss is required")
    if position.is_buy and stop >= entry:
        raise ValueError("Buy stop-loss must be below entry")
    if not position.is_buy and stop <= entry:
        raise ValueError("Sell stop-loss must be above entry")
    if any(x < Decimal('0.1') or x > 30 for x in multiples):
        raise ValueError("Target R must be between 0.1 and 30")
    if any(multiples[i] <= multiples[i - 1] for i in range(1, len(multiples))):
        raise ValueError("Targets must increase")
    risk = abs(entry - stop)
    direction = Decimal(1) if position.is_buy else Decimal(-1)
    return [TakeProfitStage(target_price=float(entry + direction * risk * mult),
                            percent_of_initial_volume=pct)
            for mult, pct in zip(multiples, percents)]
