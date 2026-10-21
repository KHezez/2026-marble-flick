"""Transparent rarity-first draws; duplicates refund 40% of draw price."""
import random
from perks import PERKS
from abilities import SKILLS
RATES={'Common':60,'Rare':25,'Epic':12,'Legendary':3}
PRICES={'passive':150,'skill':200}
SKILL_RARITIES={'brickwall':'Common','tiger':'Rare','chain':'Epic','cola':'Legendary'}

def draw(profile,kind,rng=None):
    if kind not in PRICES:raise ValueError('Unknown banner')
    price=PRICES[kind]
    if profile['coins']<price:raise ValueError('Not enough Coins. Finish a match to earn more!')
    rng=rng or random.SystemRandom()
    rarity=rng.choices(list(RATES),weights=list(RATES.values()),k=1)[0]
    pool=[k for k,p in PERKS.items() if p.rarity==rarity] if kind=='passive' else [k for k in SKILLS if SKILL_RARITIES[k]==rarity]
    key=rng.choice(pool); field='owned_perks' if kind=='passive' else 'owned_skills'
    duplicate=key in profile[field]; refund=int(price*.4) if duplicate else 0
    profile['coins']-=price-refund
    if not duplicate:profile[field].append(key)
    result={'kind':kind,'item':key,'rarity':rarity,'duplicate':duplicate,'refund':refund}
    profile['history']=(profile['history']+[result])[-100:]
    return result

def reward(profile,winner):
    amount=100 if winner==0 else 50
    profile['coins']+=amount
    return amount
