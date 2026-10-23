"""Ownership and pre-match loadout changes, shared by every UI entry point."""
from perks import validate
from stats import TeamStats

def active(profile):return profile['loadouts'][profile['active_loadout']]

def toggle(profile,kind,key,count=None):
    load=active(profile); field='perks' if kind=='passive' else 'skills'
    owned='owned_perks' if kind=='passive' else 'owned_skills'
    if key not in profile[owned]:raise ValueError('Item is not owned. Try the shop!')
    items=list(load[field])
    if key in items:items.remove(key)
    else:items.append(key)
    if field=='perks': validate(items,count)
    elif len(items)>2:raise ValueError('Unequip a skill first (maximum 2).')
    load[field]=items

def allocate(profile,name,delta):
    load=active(profile); stats=TeamStats(**load['stats'])
    stats.set(name,getattr(stats,name)+delta); load['stats']=vars(stats)


def equip_slot(profile,kind,key,slot,count=None):
    from abilities import SKILLS
    load=active(profile)
    if kind=='skin':
        if key not in profile['owned_skins']:raise ValueError('Item is not owned. Try the shop!')
        load['skin']=key;return
    field='skills' if kind=='skill' else 'perks'
    owned='owned_skills' if kind=='skill' else 'owned_perks'
    limit=2 if kind=='skill' else 3
    if key not in profile[owned]:raise ValueError('Item is not owned. Try the shop!')
    if not 0<=slot<limit:raise ValueError('Invalid slot')
    items=list(load[field])
    # Move an already equipped item to the selected slot without duplication.
    if key in items:
        previous=items.index(key)
        if slot<len(items):items[previous],items[slot]=items[slot],items[previous]
        else:items.remove(key);items.append(key)
    elif slot<len(items):items[slot]=key
    else:items.append(key)
    if field=='perks':validate(items,count)
    load[field]=items
