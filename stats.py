"""Independent, testable loadout/aim math for Marble Flick v0.4.

The 50-point cap is enforced for both teams. All non-injured discs on a
team share the same allocation. Injuries temporarily halve final outputs.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import math
import random

STAT_CAPS = {"accuracy": 15, "speed": 30, "power": 30, "toughness": 30, "critical": 10}
POINT_BUDGET = 50
INJURY_TURNS = 2  # Counts the injured disc's owner's completed attack turns.


@dataclass
class TeamStats:
    accuracy: int = 0
    speed: int = 0
    power: int = 0
    toughness: int = 0
    critical: int = 0

    @property
    def used(self) -> int:
        return sum(getattr(self, k) for k in STAT_CAPS)

    @property
    def remaining(self) -> int:
        return POINT_BUDGET - self.used

    def set(self, stat: str, requested: int) -> int:
        """Set one slider, clamping to its own max and unspent points."""
        if stat not in STAT_CAPS:
            raise ValueError(f"Unknown stat: {stat}")
        current = getattr(self, stat)
        value = max(0, min(STAT_CAPS[stat], int(requested), current + self.remaining))
        setattr(self, stat, value)
        return value

    def reset(self) -> None:
        for name in STAT_CAPS:
            setattr(self, name, 0)

    def preset(self, **kwargs: int) -> None:
        """Swap to a named test allocation in a single atomic operation."""
        if set(kwargs) - set(STAT_CAPS):
            raise ValueError("Unknown stat in preset")
        if any(v < 0 or v > STAT_CAPS[k] for k, v in kwargs.items()):
            raise ValueError("Out of range preset")
        if sum(kwargs.values()) > POINT_BUDGET:
            raise ValueError("Preset exceeds 50-point budget")
        self.reset()
        for k, v in kwargs.items():
            setattr(self, k, v)

    def clone(self) -> "TeamStats":
        return TeamStats(**{k: getattr(self, k) for k in STAT_CAPS})


def shot_speed_multiplier(stats: TeamStats, injured: bool = False) -> float:
    """SPEED only mildly affects takeoff velocity: +10% at 30/30.

    Most of the speed stat's value comes from resistance to drag in motion.
    """
    base = 1.0 + 0.10 * stats.speed / 30
    return base * (0.5 if injured else 1.0)


def drag_resistance_multiplier(stats: TeamStats, injured: bool = False) -> float:
    """Multiplier on surface drag: 1.0 -> 0.70 (SPEED 30).

    Injury halves the *bonus*, not the drag itself, to avoid runaway friction.
    """
    bonus = 0.30 * stats.speed / 30 * (0.5 if injured else 1.0)
    return 1.0 - bonus


def power_transfer_multiplier(stats: TeamStats, injured: bool = False) -> float:
    """Game-specific outgoing knockback multiplier: 1.0 -> 1.8 at POWER 30.

    Applies to the *target's* received impulse, not the shooter's launch speed.
    The normal impulse solver is conserved at level zero. Injury halves the
    target-bound portion of the impulse; this deliberately isn't strict Newtonian
    physics, so SPEED and POWER can produce different tactical builds.
    """
    factor = 1.0 + 0.80 * stats.power / 30
    return factor * (0.5 if injured else 1.0)


def collision_mass_multiplier(stats: TeamStats, role: str, injured: bool = False) -> float:
    """Only static defence uses effective mass. POWER uses impulse scaling.

    A moving disc isn't given a second arbitrary mass bonus, to keep POWER
    meaningful and predictable against stationary defenders.
    """
    if role == "defend":
        result = 1.0 + stats.toughness / 30
    elif role in ("attack", "neutral"):
        result = 1.0
    else:
        raise ValueError(f"Invalid collision role {role}")
    return result * (0.5 if injured else 1.0)


def critical_chance(stats: TeamStats, injured: bool = False) -> float:
    chance = 0.02 * stats.critical  # max 20%
    return chance * (0.5 if injured else 1.0)


def accuracy_cone(floor: str, stats: TeamStats, injured: bool = False) -> float:
    """FULL cone width in degrees, not +/− degrees.

    Normal / ice: 5 degrees base -> 0 by accuracy 5.
    Mud: 20 degrees base -> 10 at accuracy 15.
    """
    if floor == "mud":
        width = 20.0 - 10.0 * stats.accuracy / 15
    else:
        width = max(0.0, 5.0 - stats.accuracy)
    return width * (2 if injured else 1)


def apply_shot_error(dx: float, dy: float, cone_degrees: float,
                     rng: random.Random) -> tuple[float, float, float]:
    """Rotate fired vector by an angle selected uniformly inside full cone."""
    if dx == 0 and dy == 0:
        return dx, dy, 0.0
    deviation = rng.uniform(-cone_degrees / 2, cone_degrees / 2) if cone_degrees else 0.0
    rad = math.radians(deviation)
    co, si = math.cos(rad), math.sin(rad)
    return dx * co - dy * si, dx * si + dy * co, deviation
