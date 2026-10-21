"""Skill loadouts and countdowns for Marble Flick v0.5, no Pygame dependency.

Cooldowns count completed attack turns (both colours), not wall-clock seconds.
This makes them predictable in the 25-second simultaneous planning phase.
"""
from dataclasses import dataclass, field

SKILLS = ("brickwall", "tiger", "chain", "cola")
SKILL_NAMES = {"brickwall": "BRICKWALL", "tiger": "TIGER SHOT", "chain": "CHAIN", "cola": "COCA COLA ESPUMA"}
COOLDOWNS = {"brickwall": 6, "tiger": 7, "chain": 10, "cola": 7}


@dataclass
class SkillLoadout:
    slots: list[str] = field(default_factory=lambda: ["brickwall", "tiger"])
    selected: int = 0
    ready_at: dict[str, int] = field(default_factory=lambda: {k: 1 for k in SKILLS})

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
        return skill in self.slots and self.remaining(skill, turn_number) == 0

    def commit(self, skill: str, turn_number: int):
        if not self.ready(skill, turn_number):
            raise ValueError("Skill on cooldown or not equipped")
        self.ready_at[skill] = turn_number + COOLDOWNS[skill]


@dataclass(frozen=True)
class PreparedSkill:
    name: str
    egg_id: int


def can_prepare(skill: str, is_attacker: bool) -> bool:
    return skill in SKILLS and (skill == "brickwall" or is_attacker)

# Declarative extension points: future entries are excluded from equip and draws.
FUTURE_SKILLS = {
    'bull': {'name':'Bull','roles':('attack','defense'),'cooldown':8,'attack_speed':1.5,'attack_power':1.5,'counter_power':.5,'injury_turns':3,'breaks_wood':True,'implemented':False},
    'ankle_breaker': {'name':'Ankle Breaker','roles':('defense',),'cooldown':5,'implemented':False},
    'curse': {'name':'Nogokbin Curse','roles':('attack',),'unlock_turn':11,'uses_per_match':1,'implemented':False},
    'infinity': {'name':'Infinity','roles':('defense',),'cooldown':8,'implemented':False},
}
SKILL_DESCRIPTIONS = {
 'brickwall':'Concrete anchor: size +75%, immobile, injury immune. Attack 2 turns / defense 1.',
 'tiger':'One shot: speed/power +200%, zero aim error, wood break and wind pressure.',
 'chain':'Hit an enemy then E to redirect. Up to 5 weaker follow-ups.',
 'cola':'Explode on stop. Sacrifice shooter unless it is your last marble.',
}
