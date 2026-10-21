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
