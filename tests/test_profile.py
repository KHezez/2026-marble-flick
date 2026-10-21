import json
import tempfile
import unittest
from pathlib import Path
from save_data import SaveStore,default_profile
from inventory import toggle,allocate,active
from economy import draw,reward,RATES,PRICES
from perks import PERKS

class FixedRNG:
    def __init__(self,rarity):self.rarity=rarity
    def choices(self,*args,**kwargs):return [self.rarity]
    def choice(self,pool):return pool[0]

class ProfileTests(unittest.TestCase):
    def test_save_restart_preserves_both_loadouts_coins_audio_and_history(self):
        with tempfile.TemporaryDirectory() as d:
            store=SaveStore(Path(d)/'profile.json');p=store.load()
            p['coins']=12345;p['red_loadout']=dict(active(p));p['audio']['muted']=True
            allocate(p,'power',30);toggle(p,'passive','heavy');draw(p,'passive',FixedRNG('Legendary'))
            store.save(p);loaded=SaveStore(store.path).load()
            self.assertEqual(loaded,p)
    def test_corrupt_primary_recovers_backup(self):
        with tempfile.TemporaryDirectory() as d:
            store=SaveStore(Path(d)/'p.json');p=store.load();store.save(p)
            p['coins']=999;store.save(p);store.path.write_text('{broken')
            self.assertEqual(store.load()['coins'],500)
    def test_stats_caps_and_budget(self):
        p=default_profile()
        for key in ('accuracy','speed','power','critical'):allocate(p,key,100)
        self.assertEqual(sum(active(p)['stats'].values()),50)
        self.assertEqual(active(p)['stats']['accuracy'],15)
    def test_restrictions_ownership_slots(self):
        p=default_profile()
        with self.assertRaises(ValueError):toggle(p,'passive','heavenly')
        p['owned_perks']=list(PERKS);toggle(p,'passive','heavy')
        with self.assertRaises(ValueError):toggle(p,'passive','juggernaut')
        with self.assertRaises(ValueError):toggle(p,'passive','heavenly',1)
        toggle(p,'passive','sniper');toggle(p,'passive','metal')
        with self.assertRaises(ValueError):toggle(p,'passive','rat')
        with self.assertRaises(ValueError):toggle(p,'skill','cola')
    def test_every_rarity_has_pool_and_duplicate_refund(self):
        for kind in PRICES:
            for rarity in RATES:
                p=default_profile();p['coins']=5000
                r=draw(p,kind,FixedRNG(rarity));before=p['coins']
                r2=draw(p,kind,FixedRNG(rarity))
                self.assertEqual(r['rarity'],rarity);self.assertTrue(r2['duplicate'])
                self.assertEqual(p['coins'],before-int(PRICES[kind]*.6))
    def test_no_money_no_mutation(self):
        p=default_profile();p['coins']=0;before=json.dumps(p)
        with self.assertRaises(ValueError):draw(p,'passive')
        self.assertEqual(before,json.dumps(p))
    def test_match_rewards(self):
        p=default_profile();self.assertEqual(reward(p,0),100);self.assertEqual(reward(p,1),50)
        self.assertEqual(p['coins'],650)
    def test_invalid_save_is_sanitized(self):
        p=default_profile();p['coins']=-5;p['owned_perks']=list(PERKS)
        active(p)['perks']=['heavy','juggernaut','rat','metal','sniper']
        active(p)['stats']={'power':999,'speed':999}
        r=SaveStore.sanitize(p)
        self.assertEqual(r['coins'],0);self.assertLessEqual(sum(active(r)['stats'].values()),50)
        self.assertNotIn('juggernaut',active(r)['perks']);self.assertLessEqual(len(active(r)['perks']),3)
