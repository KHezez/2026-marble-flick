"""Skill loadouts and countdowns for Marble Flick v0.7, no Pygame dependency.

Cooldowns count completed attack turns (both colours), not wall-clock seconds.
This makes them predictable in the 25-second simultaneous planning phase.
"""
from dataclasses import dataclass, field

SKILLS = ("brickwall", "tiger", "chain", "cola", "bull", "ankle_breaker", "curse", "infinity")
SKILL_NAMES = {"brickwall": "BRICKWALL", "tiger": "TIGER SHOT", "chain": "CHAIN", "cola": "COCA COLA ESPUMA"}
SKILL_NAMES.update(bull="BULL",ankle_breaker="ANKLE BREAKER",curse="NOGOKBIN CURSE",infinity="INFINITY")
COOLDOWNS = {"brickwall": 6, "tiger": 7, "chain": 10, "cola": 7, "bull":8, "ankle_breaker":5, "curse":0, "infinity":8}


@dataclass
class SkillLoadout:
    slots: list[str] = field(default_factory=lambda: ["brickwall", "tiger"])
    selected: int = 0
    ready_at: dict[str, int] = field(default_factory=lambda: {k: 1 for k in SKILLS})

    used_once: set[str] = field(default_factory=set)

    def equipped(self) -> str:
        return self.slots[min(self.selected,len(self.slots)-1)] if self.slots else ""

    def select_slot(self, slot: int):
        if slot not in range(len(self.slots)):
            raise ValueError("Only two skill slots")
        self.selected = slot

    def equip(self, slot: int, skill: str):
        if slot not in (0, 1) or skill not in SKILLS:
            raise ValueError("Invalid slot or skill")
        if skill in self.slots and self.slots[slot] != skill:
            raise ValueError("Can't equip duplicate skills")
        self.slots[slot] = skill

    def remaining(self, skill: str, turn_number: int) -> int:
        return max(0, self.ready_at[skill] - turn_number)

    def ready(self, skill: str, turn_number: int) -> bool:
        return skill in self.slots and self.remaining(skill, turn_number) == 0 and (skill != "curse" or turn_number>=11 and skill not in self.used_once)

    def commit(self, skill: str, turn_number: int):
        if not self.ready(skill, turn_number):
            raise ValueError("Skill on cooldown or not equipped")
        self.ready_at[skill] = turn_number + COOLDOWNS[skill]
        if skill=="curse":self.used_once.add(skill)


@dataclass(frozen=True)
class PreparedSkill:
    name: str
    egg_id: int


def can_prepare(skill: str, is_attacker: bool) -> bool:
    return skill in (("brickwall","tiger","chain","cola","bull","curse") if is_attacker else ("brickwall","bull","ankle_breaker","infinity"))

FUTURE_SKILLS = {}  # All eight planned skills are now playable.
SKILL_DESCRIPTIONS = {
 'brickwall':'Concrete anchor: size +75%, immobile, injury immune. Attack 2 turns / defense 1.',
 'tiger':'One shot: speed/power +200%, zero aim error, wood break and wind pressure.',
 'chain':'Hit an enemy then E to redirect. Up to 5 weaker follow-ups.',
 'cola':'Explode on stop. Sacrifice shooter unless it is your last marble.',
}

SKILL_DESCRIPTIONS.update({
 'bull':'Attack: +50% speed/power and breaks wood. Defense: stop enemy, step back, charge; half-power knockback + 3-turn injury.',
 'ankle_breaker':'Defense only: sidestep on contact with brief invulnerability. The attacker keeps travelling.',
 'curse':'Ultimate, once per match after turn 10: enemies tremble, then launch in random directions at full pull.',
 'infinity':'Defense only: slows approaching enemies to a stop before contact; immune to collision and wind.'})
