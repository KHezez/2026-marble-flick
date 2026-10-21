import math
import unittest
from copy import deepcopy
from physics import Arena,Egg,Obstacle,make_match
from perks import PERKS,validate,factor
from stats import TeamStats,critical_chance

class PassiveTests(unittest.TestCase):
    def arena(self,perks=(),count=4):
        a=make_match(count);a.configure_perks({0:list(perks),1:[]},count);return a
    def test_all_twelve_registered(self):self.assertEqual(len(PERKS),12)
    def test_invalid_loadouts(self):
        for perks in (['heavy','juggernaut'],['rat']*2,['bogus'],list(PERKS)[:4]):
            with self.assertRaises(ValueError):validate(perks)
        with self.assertRaises(ValueError):self.arena(['heavenly'],1)
    def test_heavenly_odd_and_probability(self):
        a=self.arena(['heavenly'],5)
        self.assertEqual(len(a.living(0)),3);self.assertEqual(len(a.living(1)),5)
        a.team_stats[0].critical=10
        self.assertAlmostEqual(critical_chance(a.team_stats[0])*a.mult(0,'critical'),.4)
        self.assertEqual(a.mult(0,'power'),2)
    def test_all_static_factors_actual_launch_mass_and_radius(self):
        for key in ('heavy','juggernaut','sniper','metal','tungsten','rat','sleeper','heavenly'):
            with self.subTest(key=key):
                a=self.arena([key]);e=a.living(0)[0];p=PERKS[key]
                self.assertAlmostEqual(e.r,19*p.size)
                self.assertAlmostEqual(a._effective_mass(e),p.toughness)
                self.assertTrue(a.shoot(e.id,0,-100))
                self.assertAlmostEqual(e.speed,833*p.speed)
                self.assertAlmostEqual(a.cone(e),5/p.accuracy)
    def test_stacking_order_and_injury(self):
        perks=['heavenly','rat','metal'];a=self.arena(perks)
        b=self.arena(list(reversed(perks)))
        self.assertAlmostEqual(a.mult(0,'speed'),b.mult(0,'speed'))
        e=a.living(0)[0];a.injure(e.id)
        a.shoot(e.id,0,-100)
        self.assertAlmostEqual(e.speed,833*2*1.3*.8*.5)
        self.assertAlmostEqual(a.cone(e),5)
    def test_tungsten_shortens_nonstacking_injury(self):
        a=self.arena(['tungsten']);e=a.living(0)[0]
        self.assertTrue(a.injure(e.id));self.assertEqual(e.injury_turns,1)
        self.assertFalse(a.injure(e.id,4));self.assertEqual(e.injury_turns,1)
        a.finish_team_turn(0);self.assertEqual(e.injury_turns,0)
    def test_brickwall_preserves_passive_radius_and_immunity(self):
        a=self.arena(['juggernaut']);e=a.living(0)[0]
        a.injure(e.id);a.activate_brickwall(e.id)
        self.assertEqual(e.r,19*1.5*1.75);self.assertEqual(e.injury_turns,0)
        self.assertFalse(a.injure(e.id));a.deactivate_brickwall(e.id)
        self.assertEqual(e.r,19*1.5)
    def test_simultaneous_falls_keep_last_survivor_both_orders(self):
        for reverse in (False,True):
            a=self.arena(['last_resort']);members=a.living(0)
            for e in members[:2]:e.alive=False
            a.check_survivors()
            for e in members[2:]:e.x=a.right+40;e.vx=100
            if reverse:a.eggs.reverse()
            a.resolve_edges()
            self.assertEqual(len(a.living(0)),1)
            e=a.living(0)[0];self.assertLess(e.vx,0);self.assertLess(e.x,a.right)
            self.assertTrue(a.protected(e))
            a.turn_number+=1;e.x=a.right+1;a.resolve_edges()
            self.assertEqual(len(a.living(0)),0)
            self.assertEqual(sum(ev.kind=='clutch' for ev in a.events),1)
    def test_one_v_one_has_shield_but_no_clutch(self):
        a=self.arena(['last_resort'],1);e=a.living(0)[0]
        self.assertTrue(a.protected(e));self.assertNotIn(0,a.clutch_used)
    def test_curve_changes_trajectory_not_speed(self):
        a=self.arena(['curve']);a.drag_override=0
        e=a.living(0)[0];a.shoot(e.id,0,-50,curve=1)
        x=e.x
        for _ in range(40):a.step(1/240)
        self.assertGreater(e.x,x+2);self.assertAlmostEqual(e.speed,416.5,places=6)
        b=self.arena();e=b.living(0)[0];b.shoot(e.id,0,-50,curve=1)
        self.assertEqual(e.curve,0)
    def test_friendship_live_cap_and_isolation(self):
        a=self.arena(['friendship'],10);members=a.living(0);e=members[0]
        for i,other in enumerate(members):other.x=e.x+3*i;other.y=e.y
        self.assertEqual(a.friendship(e),1.25)
        for other in members[1:]:other.x+=500
        self.assertEqual(a.friendship(e),1)
        members[1].x=e.x+60;members[1].y=e.y
        self.assertEqual(a.friendship(e),1.10)
    def test_power_increases_actual_knockback(self):
        velocities=[]
        for perks in ([],['sleeper']):
            a=Arena(left=0,top=0,width=2000,height=1000,drag_override=0)
            a.eggs=[Egg(0,0,300,500),Egg(1,1,400,500)]
            a.configure_perks({0:perks,1:[]},4);a.shoot(0,100,0)
            for _ in range(30):a.step(1/240)
            velocities.append(a.eggs[1].vx)
        # Smaller toughness reduces striker mass to .85; impulse is
        # 1.83 * 833 / (1/.85 + 1), then the target receives 1.3x power.
        self.assertAlmostEqual(velocities[1], 1.83*833/(1/.85+1)*1.3, places=6)
        self.assertGreater(velocities[1],velocities[0])
    def test_fast_rat_heavenly_tiger_cannot_tunnel_thin_steel(self):
        a=Arena(left=0,top=0,width=3000,height=1000,drag_override=0)
        a.eggs=[Egg(0,0,300,500),Egg(1,1,1800,500)]
        a.configure_perks({0:['rat','heavenly','sniper'],1:[]},4)
        a.obstacles=[Obstacle(0,360,450,3,100,'steel')]
        a.shoot(0,180,0,ability='tiger')
        a.step(1/60)
        self.assertLess(a.eggs[0].vx,0)
    def test_cpu_uses_perks_in_simulation_without_mutating_original(self):
        from cpu import CPUPlanner
        a=self.arena(['heavy']);a.configure_perks({0:[],1:['rat']},4)
        before=deepcopy(a.eggs)
        for difficulty in ('easy','normal','hard'):
            planner=CPUPlanner(a,1,difficulty,1)
            self.assertAlmostEqual(planner.world.mult(1,'speed'),1.3)
            while planner.done<planner.total:planner.think_one()
            self.assertIsNotNone(planner.best)
        self.assertEqual(a.eggs,before)

if __name__=='__main__':unittest.main()

class PhysicsStressTests(unittest.TestCase):
    def test_all_team_sizes_surfaces_and_large_small_colliders(self):
        import random
        rng=random.Random(60)
        for count in (1,4,5,6,7,8,9,10):
            for floor in ('normal','ice','mud'):
                a=make_match(count,floor,'mixed')
                a.configure_perks({0:['juggernaut','metal','friendship'],1:['rat','sniper','curve']},count)
                a.shoot(a.living(1)[0].id,30,180,ability='tiger',curve=.4)
                for _ in range(720):a.step(1/240)
                for e in a.eggs:
                    self.assertTrue(all(math.isfinite(v) for v in (e.x,e.y,e.vx,e.vy,e.r)))
                    if e.alive:
                        self.assertLessEqual(a.left,e.x);self.assertLessEqual(e.x,a.right)
    def test_cola_sacrifice_can_activate_clutch_and_last_resort(self):
        a=make_match(4);a.configure_perks({0:['last_resort'],1:[]},4)
        for e in a.living(0)[2:]:e.alive=False
        a.check_survivors();e=a.living(0)[0]
        a.shoot(e.id,0,-16,ability='cola');e.vx=e.vy=0
        a.trigger_cola_if_stopped()
        self.assertEqual(len(a.living(0)),1);self.assertIn(0,a.clutch_used)
        self.assertTrue(a.protected(a.living(0)[0]))
