"""Pure, read-only strategy decision planner.

This module NEVER sends trading orders. An execution adapter must validate
broker constraints and persist idempotency and broker confirmations separately.
"""
from dataclasses import dataclass
from typing import FrozenSet, Optional


@dataclass(frozen=True)
class Position:
    account_id: str
    ticket: int
    is_buy: bool
    entry: float
    original_sl: float
    current_sl: Optional[float]
    current_price: float

@dataclass(frozen=True)
class PlannedAction:
    key: str
    kind: str
    position_ticket: int
    stop_loss: Optional[float] = None


def plan_break_even(position: Position, threshold_r: float,
                    completed: FrozenSet[str] = frozenset()) -> Optional[PlannedAction]:
    """Plan SL -> entry at a positive multiple of *original* risk.

    The initial stop must be saved when the position is first adopted.
    Never reconstruct initial risk from a moved live stop.
    """
    if position.ticket <= 0 or not position.account_id or not (0.1 <= threshold_r <= 10):
        return None
    risk = abs(position.entry - position.original_sl)
    if risk <= 0:
        return None
    # Reject initial stops on the profitable side of the entry.
    if position.is_buy and position.original_sl >= position.entry:
        return None
    if not position.is_buy and position.original_sl <= position.entry:
        return None
    favorable = ((position.current_price - position.entry) if position.is_buy
                 else (position.entry - position.current_price))
    if favorable < risk * threshold_r:
        return None
    if position.current_sl is not None:
        # Never worsen an existing SL, and do not repeat BE already present.
        if position.is_buy and position.current_sl >= position.entry:
            return None
        if not position.is_buy and position.current_sl <= position.entry:
            return None
    key = f"{position.account_id}:{position.ticket}:BE"
    if key in completed:
        return None
    return PlannedAction(key=key, kind="MOVE_SL_TO_ENTRY",
                         position_ticket=position.ticket, stop_loss=position.entry)
