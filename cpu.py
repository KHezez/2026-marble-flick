"""CPU opponent for Marble Flick. No pygame or remote/ML dependencies.

Easy aims with noisy geometry. Normal/Hard try short physics rollouts and score
ring-outs, opponent displacement, injuries and self-preservation. The planner
runs incrementally (one candidate per rendered frame) to keep the UI reactive.
"""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import math
import random
from typing import Optional

from physics import Arena, Egg, MAX_PULL, STOP_SPEED, BASE_POWER_SCALE


@dataclass(frozen=True)
class Shot:
    egg_id: int
    dx: float
    dy: float
    score: float = 0.0


DIFFICULTIES = ("easy", "normal", "hard")


def _margin(arena: Arena, egg: Egg) -> float:
    return min(egg.x - arena.left, arena.right - egg.x,
               egg.y - arena.top, arena.bottom - egg.y)


def _line_blocked(arena: Arena, shooter: Egg, target: Egg) -> bool:
    """Cheap coarse line test, used for candidate ordering only."""
    dx, dy = target.x - shooter.x, target.y - shooter.y
    dist_sq = dx * dx + dy * dy
    if dist_sq < 1e-8:
        return False
    for o in arena.obstacles:
        if not o.alive:
            continue
        # Obstacle rectangle expanded to account for marble radius.
        bx, by = o.x - shooter.r, o.y - shooter.r
        bw, bh = o.w + 2 * shooter.r, o.h + 2 * shooter.r
        # Segment vs AABB slab intersection.
        low, high = 0.01, 0.97
        for start, delta, bound, size in ((shooter.x, dx, bx, bw), (shooter.y, dy, by, bh)):
            if abs(delta) < 1e-9:
                if not (bound <= start <= bound + size):
                    break
            else:
                t1, t2 = (bound - start) / delta, (bound + size - start) / delta
                low = max(low, min(t1, t2))
                high = min(high, max(t1, t2))
                if low > high:
                    break
        else:
            return True
    return False


def _shot_towards(shooter: Egg, target: Egg, strength: float, offset: float = 0.0) -> Shot:
    dx, dy = target.x - shooter.x, target.y - shooter.y
    dist = math.hypot(dx, dy)
    if dist < 1:
        dx, dy, dist = 0.0, 1.0, 1.0
    ux, uy = dx / dist, dy / dist
    # Tangential offset in world pixels. This helps with banked / glancing hits.
    tx, ty = ux * dist - uy * offset, uy * dist + ux * offset
    length = math.hypot(tx, ty)
    pull = MAX_PULL * strength
    return Shot(shooter.id, tx / length * pull, ty / length * pull)


def _score(arena: Arena, world: Arena, our_team: int) -> float:
    by_id = {e.id: e for e in world.eggs}
    before_enemy = arena.living(1 - our_team)
    before_friend = arena.living(our_team)
    eliminated_enemy = sum(not by_id[e.id].alive for e in before_enemy)
    eliminated_friend = sum(not by_id[e.id].alive for e in before_friend)
    # A ringout is incomparably more important than dealing positional damage.
    score = 1800.0 * eliminated_enemy - 2350.0 * eliminated_friend
    for e in before_enemy:
        after = by_id[e.id]
        if not after.alive:
            continue
        moved = math.hypot(e.x - after.x, e.y - after.y)
        edge_gain = _margin(arena, e) - _margin(world, after)
        score += max(-75.0, min(150.0, edge_gain)) * 1.6
        score += min(125.0, moved) * 0.50
        if e.injury_turns == 0 and after.injury_turns > 0:
            score += 90
    for e in before_friend:
        after = by_id[e.id]
        if not after.alive:
            continue
        edge_loss = _margin(arena, e) - _margin(world, after)
        score -= max(0.0, min(200.0, edge_loss)) * 1.25
        if _margin(world, after) < 48:
            score -= 45
    return score


class CPUPlanner:
    """Incremental candidate search (call `think_one()` once per frame).

    Snapshot is immutable during search, so renders / user live edits cannot
    corrupt a simulated world. The actual shot still uses the current arena.
    """

    def __init__(self, arena: Arena, team: int = 1,
                 difficulty: str = "normal", seed: int = 0):
        if difficulty not in DIFFICULTIES:
            raise ValueError("Unsupported CPU difficulty")
        self.world = deepcopy(arena)
        self.team = team
        self.difficulty = difficulty
        self.rng = random.Random(seed)
        self.candidates = self._generate()
        self.total = len(self.candidates)
        self.done = 0
        self.best: Optional[Shot] = None
        self.best_score = float('-inf')

    def _generate(self) -> list[Shot]:
        ours = [e for e in self.world.living(self.team) if not e.brickwall]
        theirs = self.world.living(1 - self.team)
        if not ours or not theirs:
            return []
        # Rank shot opportunities by range + position, then refine candidates.
        opportunities = []
        for a in ours:
            for b in theirs:
                distance = math.hypot(a.x - b.x, a.y - b.y)
                blocked = _line_blocked(self.world, a, b)
                # Most base shots cover ~400px. Penalize unreachable targets.
                unreachable = max(0, distance - 395)
                closeness_to_edge = max(0, 70 - _margin(self.world, b))
                quality = distance + 4.0 * unreachable + (210 if blocked else 0) - .65 * closeness_to_edge
                opportunities.append((quality, a, b))
        opportunities.sort(key=lambda entry: entry[0])
        if self.difficulty == 'easy':
            # Easy is deliberately imprecise and can choose a suboptimal target.
            top = opportunities[:min(10, len(opportunities))]
            _, a, b = self.rng.choice(top)
            delta = self.rng.uniform(-31, 31)
            strength = self.rng.uniform(.65, 1.0)
            return [_shot_towards(a, b, strength, delta)]
        if self.difficulty == 'normal':
            head, target = 7, 13
            strengths = (1.0, .88)
            offsets = (0.0,)
        else:
            head, target = 12, 27
            strengths = (1.0, .86, .70)
            offsets = (0.0, -13.0, 13.0)
        shots: list[Shot] = []
        # Every high-quality opportunity gets a direct shot; some get varied
        # release force / glancing angles. Samples bounded to keep CPU fast.
        for idx, (_, a, b) in enumerate(opportunities[:head]):
            strengths_here = strengths if idx < (5 if self.difficulty == 'hard' else 4) else (1.0,)
            offsets_here = offsets if idx < (3 if self.difficulty == 'hard' else 0) else (0.0,)
            for offset in offsets_here:
                for strength in strengths_here:
                    shots.append(_shot_towards(a, b, strength, offset))
        # Keep direct shots for diversity (rather than all variants of one target).
        unique: list[Shot] = []
        seen: set[tuple[int,int,int]] = set()
        for sh in shots:
            key=(sh.egg_id, round(math.degrees(math.atan2(sh.dy, sh.dx))*3), round(math.hypot(sh.dx,sh.dy)/10))
            if key not in seen:
                seen.add(key)
                unique.append(sh)
        # Hard: a couple more possible direct targets are valued over oversampling
        # very similar angles.
        return unique[:target]

    def think_one(self) -> Optional[Shot]:
        """Evaluate one option. Returns chosen Shot only once fully evaluated."""
        if self.done >= self.total:
            return self.best
        shot = self.candidates[self.done]
        self.done += 1
        if self.difficulty == 'easy':
            self.best = shot
            return shot
        clone = deepcopy(self.world)
        if not clone.shoot(shot.egg_id, shot.dx, shot.dy):
            return self.best if self.done == self.total else None
        # Fast-but-authentic physics preview, step 1/120 (substeps in engine).
        # Do not model random accuracy deviation: the real shot applies it.
        for _ in range(420):
            if not clone.moving():
                break
            clone.step(1/120)
        value = _score(self.world, clone, self.team)
        # Tiny stable tie breaker; prevents exact same shot pattern repeatedly.
        value += self.rng.random() * 0.75
        if value > self.best_score:
            self.best_score = value
            self.best = Shot(shot.egg_id, shot.dx, shot.dy, value)
        return self.best if self.done == self.total else None
