"""Read-only take-profit planner. Produces intentions, NEVER places orders.

A production runner must persist pending/completed actions atomically and
confirm each change with the broker before declaring a stage complete.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from typing import FrozenSet, Optional, Sequence

from rule_engine import PlannedAction, Position


@dataclass(frozen=True)
class TakeProfitStage:
    target_price: float
    percent_of_initial_volume: int


def _decimal(value: float) -> Decimal:
    try:
        d = Decimal(str(value))
        if not d.is_finite():
            raise ValueError("Non-finite number")
        return d
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid volume or broker constraint") from exc


def plan_take_profit(
    position: Position,
    *,
    initial_volume: float,
    current_volume: float,
    stages: Sequence[TakeProfitStage],
    minimum_volume: float,
    volume_step: float,
    completed: FrozenSet[str] = frozenset(),
    pending: FrozenSet[str] = frozenset(),
) -> Optional[PlannedAction]:
    """Return at most one action, respecting ordered TP stages.

    If a prior stage is pending, do not plan the next stage. If the partial
    lot amount cannot be executed without violating the broker's minimum
    volume or volume step, do not send a potentially destructive order.
    """
    if not position.account_id or position.ticket <= 0 or not (1 <= len(stages) <= 3):
        return None
    if any(not isinstance(s.percent_of_initial_volume, int) or
           isinstance(s.percent_of_initial_volume, bool) or
           s.percent_of_initial_volume <= 0 for s in stages):
        return None
    if sum(s.percent_of_initial_volume for s in stages) != 100:
        return None
    try:
        initial = _decimal(initial_volume)
        current = _decimal(current_volume)
        minimum = _decimal(minimum_volume)
        step = _decimal(volume_step)
        entry = _decimal(position.entry)
        price = _decimal(position.current_price)
        targets = [_decimal(s.target_price) for s in stages]
    except ValueError:
        return None

    if not (initial >= current >= minimum > 0 and step > 0 and entry > 0 and price > 0):
        return None
    if any((target <= entry if position.is_buy else target >= entry) for target in targets):
        return None
    if any((targets[i] <= targets[i - 1] if position.is_buy
            else targets[i] >= targets[i - 1]) for i in range(1, len(targets))):
        return None

    for i, stage in enumerate(stages):
        key = f"{position.account_id}:{position.ticket}:TP{i+1}"
        if key in completed:
            continue
        if key in pending:
            return None
        if i and f"{position.account_id}:{position.ticket}:TP{i}" not in completed:
            return None
        hit = price >= targets[i] if position.is_buy else price <= targets[i]
        if not hit:
            return None
        if i == len(stages) - 1:
            return PlannedAction(key=key, kind="CLOSE_POSITION",
                                 position_ticket=position.ticket)
        raw = initial * Decimal(stage.percent_of_initial_volume) / Decimal(100)
        lots = (raw / step).to_integral_value(rounding=ROUND_FLOOR) * step
        if lots < minimum or current - lots < minimum:
            return None
        return PlannedAction(key=key, kind="PARTIAL_CLOSE",
                             position_ticket=position.ticket,
                             volume=float(lots))
    return None
