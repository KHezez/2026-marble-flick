"""Dependency-free, deterministic 2-D physics for Flick Arena.

Rules are deliberately isolated from Pygame so abilities/perks can be added later.
World coordinates are in screen pixels. No invisible boundary walls:
an egg is eliminated when its centre crosses the arena boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, hypot, sin, cos, ceil, isfinite
from typing import Optional
import random
from stats import TeamStats, shot_speed_multiplier, drag_resistance_multiplier, power_transfer_multiplier, collision_mass_multiplier, critical_chance, INJURY_TURNS

from perks import factor, validate
from combat import CombatRules

# Tunable baseline for unupgraded eggs. Older prototype was far too slippery.
# Full speed stat upgrades may later increase launch strength separately.
DRAG = {"normal": 2.775, "ice": 1.85, "mud": 3.70}
STOP_SPEED = 17.0
RESTITUTION_EGGS = 0.83
ARENA_BOUNDS = (360.0, 130.0, 560.0, 675.0)
BASE_POWER_SCALE = 8.33  # drag 180 px => launch about 1500 px/s, previously 1800
MAX_PULL = 180.0
MIN_PULL = 14.0
MAX_SPEED = 18000.0  # Bounds ricochet energy and adaptive substep cost in steel arenas.


def vector_from_pull(egg_x: float, egg_y: float,
                     release_x: float, release_y: float) -> tuple[float, float]:
    """Slingshot controls: pull the mouse BACK from the egg to launch FORWARD."""
    return egg_x - release_x, egg_y - release_y


@dataclass
class Egg:
    id: int
    team: int                 # 0 = blue, 1 = red
    x: float
    y: float
    r: float = 19.0
    mass: float = 1.0
    vx: float = 0.0
    vy: float = 0.0
    alive: bool = True
    injury_turns: int = 0
    brickwall: bool = False
    tiger: bool = False
    chain: bool = False
    cola: bool = False
    chain_ready: bool = False
    chain_followups: int = 0
    chain_segment: int = 0
    chain_hit_segment: int = -1

    bull: bool = False
    defense: str = ""
    guard_used: bool = False
    invulnerable_until: float = 0.0
    curve: float = 0.0
    base_radius: float = 19.0
    owner: int = -1
    skin: str = ""
    boss: bool = False

    @property
    def speed(self) -> float:
        return hypot(self.vx, self.vy)


@dataclass
class Obstacle:
    id: int
    x: float                 # top-left
    y: float
    w: float
    h: float
    material: str            # wood | steel
    hp: float = 1.6
    alive: bool = True


@dataclass
class Event:
    kind: str                # hit | wood_hit | wood_break | fall
    x: float
    y: float
    team: int = -1
    strength: float = 0.0


@dataclass
class Arena(CombatRules):
    left: float = ARENA_BOUNDS[0]
    top: float = ARENA_BOUNDS[1]
    width: float = ARENA_BOUNDS[2]
    height: float = ARENA_BOUNDS[3]
    floor: str = "normal"
    eggs: list[Egg] = field(default_factory=list)
    obstacles: list[Obstacle] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    elapsed: float = 0.0
    drag_override: Optional[float] = None
    team_stats: dict[int, TeamStats] = field(default_factory=lambda: {0: TeamStats(), 1: TeamStats()})
    attacking_team: Optional[int] = None
    mud_variance: bool = True
    mud_drag: float = DRAG["mud"]
    _mud_period: int = -1
    rng: random.Random = field(default_factory=lambda: random.Random(21917))
    _contact_cooldowns: dict[tuple[int, int], float] = field(default_factory=dict)
    _power_contacts: dict = field(default_factory=dict)
    _wind_seen: set[int] = field(default_factory=set)
    active_shooter_id: Optional[int] = None

    zones: list = field(default_factory=list)
    counters: list = field(default_factory=list)
    boundary_walls: bool = False
    walls_open: bool = False
    map_key: str = 'classic'
    team_perks: dict = field(default_factory=lambda: {0: [], 1: []})
    turn_number: int = 1
    last_resort_used: set = field(default_factory=set)
    last_resort_until: dict = field(default_factory=dict)
    clutch_used: set = field(default_factory=set)
    previous_counts: dict = field(default_factory=dict)

    boss_state: dict | None = None
    boss_hits: dict = field(default_factory=dict)
    owner_stats: dict = field(default_factory=dict)
    owner_perks: dict = field(default_factory=dict)

    def stats_for(self,e):return self.owner_stats.get(e.owner,self.team_stats[e.team])
    def perks_for(self,e):return self.owner_perks.get(e.owner,self.team_perks.get(e.team,[]))
    def mult_for(self,e,stat):return factor(self.perks_for(e),stat)

    def configure_perks(self, loadouts, count):
        for team in (0, 1):
            validate(loadouts.get(team, []), count)
        self.team_perks = {t:list(loadouts.get(t, [])) for t in (0,1)}
        for team in (0,1):
            members = self.living(team)
            if 'heavenly' in self.team_perks[team]:
                for e in members[ceil(len(members)/2):]: e.alive = False
            for e in self.living(team):
                e.base_radius = 19 * self.mult(team, 'size')
                e.r = e.base_radius
            self.previous_counts[team] = len(self.living(team))
        self.check_survivors()

    def mult(self, team, stat):
        return factor(self.team_perks.get(team, []), stat)

    def cone(self, egg):
        from stats import accuracy_cone
        return accuracy_cone(self.terrain_at(egg.x,egg.y), self.stats_for(egg), egg.injury_turns > 0) / self.mult_for(egg, 'accuracy')

    def friendship(self, egg):
        if 'friendship' not in self.perks_for(egg): return 1.0
        neighbours = sum(e.id != egg.id and hypot(e.x-egg.x,e.y-egg.y) <= 95 for e in self.living(egg.team))
        return 1 + min(.25, .05 * (neighbours + 1)) if neighbours else 1.0

    def toughness(self, egg):
        return self.mult_for(egg, 'toughness') * self.friendship(egg)

    def check_survivors(self):
        for team in (0,1):
            alive = self.living(team)
            previous = self.previous_counts.get(team, len(alive))
            if len(alive)==1:
                e = alive[0]
                if previous>=2 and team not in self.clutch_used:
                    self.clutch_used.add(team)
                    self.events.append(Event('clutch', e.x,e.y,team,1))
                if 'last_resort' in self.perks_for(e) and team not in self.last_resort_used:
                    self.last_resort_used.add(team)
                    self.last_resort_until[team] = self.turn_number
                    self.events.append(Event('last_resort',e.x,e.y,team,1))
            self.previous_counts[team] = len(alive)

    def protected(self, egg):
        return self.last_resort_until.get(egg.team, -1) >= self.turn_number and len(self.living(egg.team)) == 1

    def resolve_edges(self):
        self.check_survivors()
        for e in self.living():
            if self.boundary_walls and self.turn_number>=13 and not self.walls_open:
                self.walls_open=True
                self.events.append(Event('walls_open',self.left+self.width/2,self.top+self.height/2,-1,1.5))
            if self.protected(e) or (self.boundary_walls and not self.walls_open):
                if e.x < self.left+e.r: e.x=self.left+e.r; e.vx=abs(e.vx)*.83
                if e.x > self.right-e.r: e.x=self.right-e.r; e.vx=-abs(e.vx)*.83
                if e.y < self.top+e.r: e.y=self.top+e.r; e.vy=abs(e.vy)*.83
                if e.y > self.bottom-e.r: e.y=self.bottom-e.r; e.vy=-abs(e.vy)*.83
            elif e.boss and not (self.left <= e.x <= self.right and self.top <= e.y <= self.bottom):
                from bosses import hurt
                hurt(self,35)
                e.x=max(self.left+e.r,min(self.right-e.r,e.x));e.y=max(self.top+e.r,min(self.bottom-e.r,e.y));e.vx=e.vy=0
            elif not (self.left <= e.x <= self.right and self.top <= e.y <= self.bottom):
                e.alive=False
                e.vx=e.vy=0
                self.events.append(Event('fall',e.x,e.y,e.team))
                # Re-evaluate immediately, BEFORE the next simultaneous ringout.
                self.check_survivors()

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height

    def living(self, team: Optional[int] = None) -> list[Egg]:
        return [e for e in self.eggs if e.alive and (team is None or e.team == team)]

    def moving(self) -> bool:
        return bool(self.counters) or any(e.speed >= STOP_SPEED for e in self.living())

    def finish_team_turn(self, team: int) -> None:
        """Injuries age only after their owner's next completed shooting turn."""
        for egg in self.living(team):
            if egg.injury_turns:
                egg.injury_turns -= 1

    def injure(self, egg_id: int, turns: int = INJURY_TURNS) -> bool:
        egg = next((e for e in self.living() if e.id == egg_id), None)
        if egg is None or egg.injury_turns or egg.brickwall or self.invulnerable(egg):
            return False  # non-stacking injury
        egg.injury_turns = max(0, turns - (1 if "tungsten" in self.perks_for(egg) else 0))
        self.events.append(Event("injury", egg.x, egg.y, team=egg.team, strength=1.0))
        return True

    def heal(self, egg_id: int) -> bool:
        egg = next((e for e in self.living() if e.id == egg_id), None)
        if egg is None:
            return False
        was_injured = egg.injury_turns > 0
        egg.injury_turns = 0
        return was_injured

    def activate_brickwall(self, egg_id: int) -> bool:
        e = next((egg for egg in self.living() if egg.id == egg_id), None)
        if e is None or e.brickwall or self.moving():
            return False
        e.brickwall = True
        e.r = e.base_radius * 1.75
        e.injury_turns = 0
        e.vx = e.vy = 0.0
        self.events.append(Event("brickwall_on", e.x, e.y, team=e.team))
        return True

    def deactivate_brickwall(self, egg_id: int) -> None:
        e = next((egg for egg in self.eggs if egg.id == egg_id), None)
        if e and e.brickwall:
            e.brickwall = False
            e.r = e.base_radius
            self.events.append(Event("brickwall_off", e.x, e.y, team=e.team))

    def _effective_mass(self, egg: Egg) -> float:
        if egg.brickwall or egg.defense=="infinity":
            return float("inf")
        if egg.team == self.attacking_team and egg.speed >= 85.0:
            role = "attack"
        elif egg.speed < 85.0:
            role = "defend"
        else:
            role = "neutral"
        return max(0.05, egg.mass * collision_mass_multiplier(
            self.stats_for(egg), role, egg.injury_turns > 0) * self.toughness(egg))

    def shoot(self, egg_id: int, dx: float, dy: float, power_scale: float = BASE_POWER_SCALE, ability: str = "", curve: float = 0.0) -> bool:
        """Launch an idle egg. Input vector points TOWARD the target.

        Magnitude: 0..180 screen pixels. At 180px, ~1500px/sec.
        """
        selected = next((e for e in self.eggs if e.id == egg_id and e.alive), None)
        magnitude = hypot(dx, dy)
        if selected is None or selected.brickwall or magnitude < MIN_PULL or self.moving():
            return False
        launch_speed = (min(magnitude, MAX_PULL) * power_scale *
                        shot_speed_multiplier(self.stats_for(selected), selected.injury_turns > 0))
        launch_speed *= self.mult_for(selected, "speed")
        selected.curve = max(-1.5, min(1.5, curve)) if "curve" in self.perks_for(selected) else 0.0
        if ability == "tiger":
            launch_speed *= 2.0  # v0.8 +100% speed
        if ability == "bull":launch_speed *= 1.5
        for e in self.eggs:
            e.bull = False
            e.tiger = e.chain = e.cola = False
            e.chain_ready = False
            e.chain_followups = 0
            e.chain_segment = 0
            e.chain_hit_segment = -1
        selected.bull = ability == "bull"
        selected.tiger = ability == "tiger"
        selected.chain = ability == "chain"
        selected.cola = ability == "cola"
        self.active_shooter_id = selected.id
        self._wind_seen.clear()
        self.attacking_team = selected.team
        self._contact_cooldowns.clear();self._power_contacts.clear()
        selected.vx = dx / magnitude * launch_speed
        selected.vy = dy / magnitude * launch_speed
        return True

    def chain_redirect(self, egg_id: int, dx: float, dy: float) -> bool:
        """Re-accelerate after a distinct enemy hit, maximum five followups."""
        e = next((egg for egg in self.living() if egg.id == egg_id), None)
        magnitude = hypot(dx, dy)
        if not e or not e.chain or not e.chain_ready or e.chain_followups >= 5 or magnitude < 1.0:
            return False
        self._power_contacts.clear()
        e.chain_followups += 1
        e.chain_segment += 1
        e.chain_ready = False
        # Each link becomes noticeably weaker than the previous one.
        attenuation = 0.78 ** e.chain_followups
        speed = MAX_PULL * BASE_POWER_SCALE * 0.91 * attenuation
        speed *= shot_speed_multiplier(self.stats_for(e), e.injury_turns > 0) * self.mult_for(e, "speed")
        e.vx, e.vy = dx / magnitude * speed, dy / magnitude * speed
        self.events.append(Event("chain_dash", e.x, e.y, e.team, 1.0))
        return True

    def trigger_cola_if_stopped(self) -> bool:
        """Detonate when the shooter stops. Can be called after each fixed step."""
        e = next((egg for egg in self.living() if egg.id == self.active_shooter_id), None)
        if not e or not e.cola or e.speed >= STOP_SPEED:
            return False
        e.cola = False
        radius = 177.0
        for other in self.living():
            if other.id == e.id or other.brickwall or self.invulnerable(other) or self.counter_locked(other):
                continue
            dx, dy = other.x - e.x, other.y - e.y
            dist = hypot(dx, dy)
            if dist <= radius + other.r:
                if dist < 0.001:
                    dx, dy, dist = 0.0, 1.0, 1.0
                strength = self.mult_for(e, "power") * power_transfer_multiplier(self.stats_for(e), e.injury_turns > 0) * 1220.0 * max(0.15, 1.0 - dist / (radius + other.r))
                if other.boss:
                    from bosses import hurt
                    hurt(self,min(40,strength/30))
                toughness = collision_mass_multiplier(self.stats_for(other), "defend", other.injury_turns > 0) * self.toughness(other)
                other.vx += dx / dist * strength / max(.1, toughness)
                other.vy += dy / dist * strength / max(.1, toughness)
        self.events.append(Event("cola_explosion", e.x, e.y, e.team, 1.0))
        if len(self.living(e.team)) > 1:
            e.alive = False
            e.vx = e.vy = 0.0
            self.events.append(Event("cola_sacrifice", e.x, e.y, e.team, 1.0))
        self.check_survivors()
        return True

    def step(self, dt: float) -> None:
        """Advance by ONE small fixed step (recommended dt = 1/240).

        Caller is responsible for repeated fixed steps, independent of render FPS.
        """
        if dt <= 0:
            return
        if dt > 1 / 90:
            # Disallow very large integration steps that might tunnel through eggs.
            count = int(dt / (1 / 240)) + 1
            for _ in range(count):
                self.step(dt / count)
            return
        for egg in self.living():self.limit_velocity(egg)
        # Bound travel by the smallest collider, including boosted Tiger/Rat shots.
        max_speed = max((e.speed for e in self.living()), default=0)
        min_radius = min((e.r for e in self.living()), default=19)
        if max_speed * dt > min_radius * .45:
            pieces = ceil(max_speed * dt / (min_radius * .45))
            for _ in range(pieces): self.step(dt/pieces)
            return
        self.elapsed += dt
        if self.drag_override is not None:
            drag = self.drag_override
        elif self.floor == "mud" and self.mud_variance:
            period = int((self.elapsed + 1e-8) / 0.30)
            if period != self._mud_period:
                self._mud_period = period
                self.mud_drag = self.rng.uniform(2.4, 5.0)
            drag = self.mud_drag
        else:
            drag = DRAG[self.floor]
        self.update_combat(dt)
        eggs = self.living()
        for e in eggs:
            if e.brickwall or e.defense=="infinity" or self.counter_locked(e):
                e.vx = e.vy = 0.0
                continue
            if e.vx or e.vy:
                if e.curve:
                    angle=e.curve*dt
                    co,si=cos(angle),sin(angle)
                    e.vx,e.vy=e.vx*co-e.vy*si,e.vx*si+e.vy*co
                    e.curve *= exp(-1.2*dt)
                resistance = drag_resistance_multiplier(self.stats_for(e), e.injury_turns > 0)
                local_floor=self.terrain_at(e.x,e.y)
                local_drag=drag if local_floor==self.floor or self.drag_override is not None else DRAG[local_floor]
                damp = exp(-local_drag * resistance * dt)
                e.vx *= damp
                e.vy *= damp
                if e.speed < STOP_SPEED:
                    e.vx = e.vy = 0.0
                e.x += e.vx * dt
                e.y += e.vy * dt

        self.resolve_edges()

        active = self.living()
        # Tiger pressure field: hits neighbours once per firing segment, even
        # without direct contact. Brickwall is immune to pressure.
        shooter = next((e for e in active if e.id == self.active_shooter_id and e.tiger), None)
        if shooter is not None and shooter.speed >= 100:
            for other in active:
                if other.id == shooter.id or other.brickwall or self.invulnerable(other) or self.counter_locked(other) or other.id in self._wind_seen:
                    continue
                dx, dy = other.x - shooter.x, other.y - shooter.y
                dist = hypot(dx, dy)
                if shooter.r + other.r < dist < shooter.r + other.r + 69.0:
                    if dist > 1e-6:
                        other.vx += dx / dist * 97.5 / self.toughness(other)
                        other.vy += dy / dist * 97.5 / self.toughness(other)
                        self._wind_seen.add(other.id)
                        self.events.append(Event("tiger_wind", other.x, other.y, other.team, .55))
        # Resolve positional contacts iteratively to avoid stacked-overlap artefacts.
        for iteration in range(2):
            for i, a in enumerate(active):
                for b in active[i + 1:]:
                    self._egg_collision(a, b, emit=(iteration == 0))
            for e in active:
                for obstacle in self.obstacles:
                    if obstacle.alive:
                        self._obstacle_collision(e, obstacle, emit=(iteration == 0))

        self.update_combat(0)
        self.resolve_edges()

    @staticmethod
    def limit_velocity(egg):
        speed=egg.speed
        if not isfinite(speed):
            # Defensive guard for externally corrupted/debug state.
            egg.vx=egg.vy=0.
        elif speed>MAX_SPEED:
            egg.vx*=MAX_SPEED/speed;egg.vy*=MAX_SPEED/speed

    def _egg_collision(self, a: Egg, b: Egg, emit: bool) -> None:
        dx, dy = b.x - a.x, b.y - a.y
        min_dist = a.r + b.r
        dist2 = dx * dx + dy * dy
        if dist2 >= min_dist * min_dist:
            return
        if self.pre_collision_guard(a,b):return
        dist = dist2 ** 0.5
        if dist <= 1e-8:
            nx, ny, dist = 1.0, 0.0, 0.0
        else:
            nx, ny = dx / dist, dy / dist

        inv_a = 1 / self._effective_mass(a)
        inv_b = 1 / self._effective_mass(b)
        penetration = min_dist - dist
        # 0.8 instead of 1.0 helps stability when three discs touch.
        if inv_a + inv_b <= 1e-12:
            return
        correction = max(penetration - 0.015, 0) * 0.86 / (inv_a + inv_b)
        a.x -= nx * correction * inv_a
        a.y -= ny * correction * inv_a
        b.x += nx * correction * inv_b
        b.y += ny * correction * inv_b

        rvx, rvy = b.vx - a.vx, b.vy - a.vy
        vn = rvx * nx + rvy * ny
        if vn >= 0:
            return
        # Capture before the impulse: the attacker can slow to near zero
        # immediately after colliding with a stationary target.
        approach_speed = (a if a.team == self.attacking_team else b).speed
        j = -(1 + RESTITUTION_EGGS) * vn / (inv_a + inv_b)
        a.vx -= j * nx * inv_a
        a.vy -= j * ny * inv_a
        b.vx += j * nx * inv_b
        b.vy += j * ny * inv_b
        # After the ordinary collision, scale ONLY the victim's portion of
        # outgoing impulse. This makes POWER noticeably stronger at knocking
        # opponents away while SPEED primarily determines travel distance.
        # One attacker must be the currently active team's disc. Comparing
        # projected velocities avoids incorrectly boosting a disc struck by an
        # enemy marble bouncing back from another collision.
        striker, victim = None, None
        a_forward = a.vx * nx + a.vy * ny + j * inv_a  # pre-impulse velocity
        b_forward = b.vx * nx + b.vy * ny - j * inv_b
        if a.team == self.attacking_team and a_forward > b_forward and a_forward > 80:
            striker, victim = a, b
        elif b.team == self.attacking_team and b_forward < a_forward and b_forward < -80:
            striker, victim = b, a
        key=tuple(sorted((a.id,b.id)))
        if striker is not None and self.elapsed-self._power_contacts.get(key,-1e8)>=.08:
            self._power_contacts[key]=self.elapsed
            transfer = power_transfer_multiplier(self.stats_for(striker), striker.injury_turns > 0) * self.mult_for(striker, "power")
            if striker.bull:transfer *= 1.5
            if striker.tiger:
                transfer *= 1.8  # v0.8 +80% power
            if striker.chain:
                transfer *= 0.78 ** striker.chain_followups
            extra = (transfer - 1.0) * j * (inv_b if victim is b else inv_a)
            direction = 1.0 if victim is b else -1.0
            victim.vx += nx * extra * direction
            victim.vy += ny * extra * direction
        if emit and (a.boss or b.boss):
            from bosses import contact
            contact(self,a if a.boss else b,b if a.boss else a,-vn)
        self.limit_velocity(a);self.limit_velocity(b)
        if emit and -vn > 65:
            if a.brickwall or b.brickwall:
                self.events.append(Event("brickwall_hit", (a.x+b.x)/2, (a.y+b.y)/2,
                                         strength=min(-vn/1000,1.0)))
            else:
                self.events.append(Event("hit", (a.x + b.x) / 2, (a.y + b.y) / 2,
                                         strength=min(-vn / 1000, 1.0)))
        if emit and a.team != b.team and self.attacking_team is not None and -vn > 85:
            chain_striker = a if (a.id == self.active_shooter_id and a.chain) else (
                b if (b.id == self.active_shooter_id and b.chain) else None)
            if chain_striker and chain_striker.chain_hit_segment != chain_striker.chain_segment:
                chain_striker.chain_hit_segment = chain_striker.chain_segment
                chain_striker.chain_ready = True
                self.events.append(Event("chain_hit", chain_striker.x, chain_striker.y, chain_striker.team, 1.0))
            striker = a if a.team == self.attacking_team else b
            victim = b if striker is a else a
            key = tuple(sorted((a.id, b.id)))
            cooldown = self._contact_cooldowns.get(key, -1e8)
            if self.elapsed - cooldown >= 0.20 and approach_speed >= 85:
                self._contact_cooldowns[key] = self.elapsed
                chance = min(1.0, critical_chance(self.stats_for(striker), striker.injury_turns > 0) * self.mult_for(striker, "critical"))
                if not victim.brickwall and victim.injury_turns == 0 and self.rng.random() < chance:
                    self.injure(victim.id)


    def _obstacle_collision(self, e: Egg, box: Obstacle, emit: bool) -> None:
        closest_x = min(max(e.x, box.x), box.x + box.w)
        closest_y = min(max(e.y, box.y), box.y + box.h)
        dx, dy = e.x - closest_x, e.y - closest_y
        dist2 = dx * dx + dy * dy
        if dist2 >= e.r * e.r:
            return
        dist = dist2 ** 0.5
        if dist > 1e-8:
            nx, ny = dx / dist, dy / dist
            overlap = e.r - dist
        else:
            # Centre INSIDE box: resolve to the nearest face, not random direction.
            options = [
                (e.x - box.x, -1.0, 0.0),
                (box.x + box.w - e.x, 1.0, 0.0),
                (e.y - box.y, 0.0, -1.0),
                (box.y + box.h - e.y, 0.0, 1.0),
            ]
            nearest, nx, ny = min(options, key=lambda t: t[0])
            overlap = nearest + e.r
        vn = e.vx * nx + e.vy * ny
        impact = max(0.0, -vn)

        if emit and box.material == "wood" and (e.tiger or e.bull):
            box.alive = False
            self.events.append(Event("wood_break", closest_x, closest_y, strength=1.0))
            return
        if emit and box.material == "wood" and impact > 130:
            box.hp -= impact / 630.0
            if box.hp <= 0:
                box.alive = False
                # The wood breaks and the egg continues through at reduced speed.
                e.vx *= 0.79
                e.vy *= 0.79
                self.events.append(Event("wood_break", closest_x, closest_y,
                                         strength=min(impact / 1000, 1.0)))
                return
            self.events.append(Event("wood_hit", closest_x, closest_y,
                                     strength=min(impact / 1000, 1.0)))
        if e.brickwall:
            # Immovable expanded concrete disc: it cannot be displaced.
            return
        e.x += nx * overlap
        e.y += ny * overlap
        if vn < 0:
            rebound = 0.68 if box.material == "wood" else 0.83
            e.vx -= (1 + rebound) * vn * nx
            e.vy -= (1 + rebound) * vn * ny
            if emit and impact > 65 and box.material == "steel":
                self.events.append(Event("hit", closest_x, closest_y,
                                         strength=min(impact / 1000, 1.0)))


def make_match(count: int = 10, floor: str = "normal", obstacle_mode: str = "none") -> Arena:
    if count not in (1, 4, 5, 6, 7, 8, 9, 10):
        raise ValueError("Team size must be 1 or between 4 and 10")
    if floor not in DRAG:
        raise ValueError("Unknown floor")
    if obstacle_mode not in ("none", "wood", "steel", "mixed"):
        raise ValueError("Unknown obstacle mode")
    arena = Arena(floor=floor)

    # Two armies always face each other VERTICALLY: red at top, blue at bottom.
    # The front line is closer to the centre. All formations are symmetric.
    if count == 1:
        columns = [(0, 1)]
    elif count <= 5:
        columns = [(0, count)]
    else:
        columns = [(0, 5), (1, count - 5)]

    next_id = 0
    for team in (0, 1):
        for row, amount in columns:
            spacing = 92.0
            xs = [arena.left + arena.width / 2 + (j-(amount-1)/2)*spacing
                  for j in range(amount)]
            # row 0 = front line, row 1 = rear line
            advance = 205.0 if count == 1 else (188.0 if count <= 5 else 202.0)
            offset = advance - 92.0 * row
            y = arena.bottom - offset if team == 0 else arena.top + offset
            for x in xs:
                arena.eggs.append(Egg(id=next_id, team=team, x=x, y=y))
                next_id += 1

    # The middle corridor has wooden blocks and a fixed steel obstacle.
    midx, midy = arena.left + arena.width / 2, arena.top + arena.height / 2
    possible = [
        (midx - 146, midy - 30, 42, 61, "wood"),
        (midx + 104, midy - 30, 42, 61, "wood"),
        (midx - 17, midy - 25, 34, 50, "steel"),
    ]
    if obstacle_mode == "wood":
        possible = [(x, y, w, h, "wood") for x, y, w, h, _ in possible]
    elif obstacle_mode == "steel":
        possible = [(x, y, w, h, "steel") for x, y, w, h, _ in possible]
    elif obstacle_mode == "none":
        possible = []
    arena.obstacles = [Obstacle(i, *v) for i, v in enumerate(possible)]
    return arena
