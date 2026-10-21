"""Passive definitions. Order: stat output × passive factors × injury × skills.
Size is physical radius, not a cosmetic scale. Friendship is sampled live.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Perk:
    name: str
    rarity: str
    description: str
    size: float = 1
    speed: float = 1
    power: float = 1
    toughness: float = 1
    accuracy: float = 1
    critical: float = 1

PERKS = {
 'heavenly': Perk('Heavenly Restricted','Legendary','Half marbles (rounded up); 2x combat stats. Not in 1v1.',speed=2,power=2,toughness=2,accuracy=2,critical=2),
 'heavy': Perk('Heavy','Common','Size/power/toughness +25%, speed -25%.',1.25,.75,1.25,1.25),
 'juggernaut': Perk('Juggernaut','Rare','Size/power/toughness +50%, speed -50%.',1.5,.5,1.5,1.5),
 'sniper': Perk('Sniper','Rare','Accuracy +50% (cone /1.5), speed +20%.',speed=1.2,accuracy=1.5),
 'last_resort': Perk('Last Resort','Epic','Last survivor bounces off edges for the current turn, once per match.'),
 'metal': Perk('Metal','Common','Toughness +30%, speed -20%.',speed=.8,toughness=1.3),
 'tungsten': Perk('Tungsten','Rare','Toughness +60%, speed -35%; injury one turn shorter.',speed=.65,toughness=1.6),
 'rat': Perk('Rat','Common','Size/toughness -30%, power +15%, speed +30%.',.7,1.3,1.15,.7),
 'sleeper': Perk('Sleeper Build','Rare','Size/toughness -15%, power +30%.',.85,1,1.3,.85),
 'curve': Perk('Curve Shot','Epic','While aiming: C cycles bend; C + wheel adjusts strength/direction.'),
 'eyes': Perk('Eyes of Heaven','Legendary','Detect confirmed defense skill on attack. Cooldown: 8 turns.'),
 'friendship': Perk('Power of Friendship','Epic','2+ clustered allies: +5% toughness per marble incl. self (max 25%, 95px).'),
}

def validate(perks, count=None):
    if len(perks)>3 or len(set(perks))!=len(perks) or any(p not in PERKS for p in perks):
        raise ValueError('Equip up to 3 different passives.')
    if 'heavy' in perks and 'juggernaut' in perks:
        raise ValueError('Heavy and Juggernaut cannot be equipped together.')
    if count==1 and 'heavenly' in perks:
        raise ValueError('Heavenly Restricted is unavailable in 1v1.')

def factor(perks, stat):
    result=1.0
    for key in sorted(perks): result *= getattr(PERKS[key],stat)
    return result
