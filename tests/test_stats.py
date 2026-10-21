import math
import random
import unittest

from stats import (TeamStats, STAT_CAPS, POINT_BUDGET, accuracy_cone, drag_resistance_multiplier, power_transfer_multiplier,
                   apply_shot_error, shot_speed_multiplier,
                   collision_mass_multiplier, critical_chance)
from physics import Arena, Egg, DRAG, make_match, STOP_SPEED


class StatLabTests(unittest.TestCase):
    def test_50_point_cap_and_per_stat_caps(self):
        stats = TeamStats()
        self.assertEqual(stats.set('power',100),30)
        self.assertEqual(stats.set('speed',100),20)
        self.assertEqual(stats.remaining,0)
        self.assertEqual(stats.set('critical',10),0)
        self.assertEqual(stats.set('power',11),11)
        self.assertEqual(stats.set('critical',10),10)
        self.assertEqual(stats.remaining,9)
        stats.preset(power=30,speed=20)
        self.assertEqual(stats.used,50)
        self.assertRaises(ValueError,stats.preset, power=30,speed=30)

    def test_accuracy_cones_and_injury(self):
        stats = TeamStats()
        self.assertEqual(accuracy_cone('normal',stats),5)
        self.assertEqual(accuracy_cone('mud',stats),20)
        stats.set('accuracy',5)
        self.assertEqual(accuracy_cone('normal',stats),0)
        self.assertAlmostEqual(accuracy_cone('mud',stats),16.6666667,places=5)
        stats.set('accuracy',15)
        self.assertEqual(accuracy_cone('mud',stats),10)
        self.assertEqual(accuracy_cone('mud',stats, injured=True),20)
        self.assertEqual(accuracy_cone('ice',stats),0)

    def test_random_error_falls_inside_full_cone(self):
        rng=random.Random(99)
        for cone in (0,5,10,20,40):
            for _ in range(500):
                x,y,delta=apply_shot_error(100,0,cone,rng)
                self.assertAlmostEqual(math.hypot(x,y),100)
                self.assertTrue(-cone/2 <= delta <= cone/2)
                self.assertAlmostEqual(math.degrees(math.atan2(y,x)),delta)

    def test_maxed_stat_differences(self):
        stats=TeamStats()
        self.assertEqual(shot_speed_multiplier(stats),1)
        self.assertEqual(collision_mass_multiplier(stats,'attack'),1)
        self.assertEqual(collision_mass_multiplier(stats,'defend'),1)
        self.assertEqual(critical_chance(stats),0)
        stats.preset(speed=30,critical=10)
        self.assertAlmostEqual(shot_speed_multiplier(stats),1.1)
        self.assertAlmostEqual(shot_speed_multiplier(stats, True),.55)
        self.assertAlmostEqual(critical_chance(stats),.2)
        self.assertAlmostEqual(critical_chance(stats,True),.1)
        stats.preset(power=30)
        self.assertEqual(collision_mass_multiplier(stats,'attack'),1)
        self.assertAlmostEqual(power_transfer_multiplier(stats),1.8)
        self.assertAlmostEqual(power_transfer_multiplier(stats, True),0.9)
        self.assertEqual(collision_mass_multiplier(stats,'attack',True),0.5)
        stats.preset(toughness=30)
        self.assertEqual(collision_mass_multiplier(stats,'defend'),2)
        self.assertEqual(collision_mass_multiplier(stats,'defend',True),1)

    def test_shot_speed_respects_team_stats_and_injury(self):
        a = make_match(1)
        blue=a.living(0)[0]
        a.team_stats[0].set('speed',30)
        self.assertTrue(a.shoot(blue.id,180,0))
        self.assertAlmostEqual(blue.vx,180*8.33*1.1)
        b=make_match(1)
        blue=b.living(0)[0]
        b.team_stats[0].set('speed',30)
        self.assertTrue(b.injure(blue.id))
        self.assertTrue(b.shoot(blue.id,180,0))
        self.assertAlmostEqual(blue.vx,180*8.33*.55)

    def test_injury_is_nonstacking_and_expires_after_two_owner_turns(self):
        a = make_match(4)
        marble=a.living(1)[0]
        self.assertTrue(a.injure(marble.id))
        self.assertFalse(a.injure(marble.id))
        self.assertEqual(marble.injury_turns,2)
        a.finish_team_turn(0)
        self.assertEqual(marble.injury_turns,2)
        a.finish_team_turn(1)
        self.assertEqual(marble.injury_turns,1)
        a.finish_team_turn(0)
        self.assertEqual(marble.injury_turns,1)
        a.finish_team_turn(1)
        self.assertEqual(marble.injury_turns,0)

    def test_physics_offensive_mass_pushes_more(self):
        def collide(power):
            a=Arena(left=0,top=0,width=900,height=300,drag_override=0.0)
            a.team_stats[0].set('power',power)
            a.attacking_team=0
            p=Egg(0,0,150,150,vx=700)
            d=Egg(1,1,230,150)
            a.eggs=[p,d]
            for _ in range(45):
                a.step(1/240)
            return d.x-230
        self.assertGreater(collide(30),collide(0))

    def test_physics_defense_resists_more(self):
        def collide(tough):
            a=Arena(left=0,top=0,width=900,height=300,drag_override=0.0)
            a.team_stats[1].set('toughness',tough)
            a.attacking_team=0
            p=Egg(0,0,150,150,vx=700)
            d=Egg(1,1,230,150)
            a.eggs=[p,d]
            for _ in range(45):
                a.step(1/240)
            return d.x-230
        self.assertLess(collide(30),collide(0))

    def test_mud_friction_variance_is_segmented_in_thirds(self):
        a=Arena(left=0,top=0,width=4000,height=500,floor='mud')
        a.eggs=[Egg(0,0,100,100,vx=300)]
        a.step(1/240)
        first=a.mud_drag
        self.assertGreaterEqual(first,2.4)
        self.assertLessEqual(first,5)
        for _ in range(25): a.step(1/240)
        self.assertEqual(first,a.mud_drag)
        for _ in range(60): a.step(1/240)
        self.assertNotEqual(first,a.mud_drag)
        a.mud_variance=False
        self.assertGreater(DRAG['mud'],DRAG['normal'])

if __name__=='__main__':
    unittest.main()

class CriticalContactTests(unittest.TestCase):
    def test_no_critical_without_points(self):
        a=Arena(left=0,top=0,width=900,height=400,drag_override=0)
        a.attacking_team=0
        blue=Egg(0,0,150,200,vx=500)
        red=Egg(1,1,212,200)
        a.eggs=[blue,red]
        for _ in range(40):a.step(1/240)
        self.assertEqual(red.injury_turns,0)

    def test_critical_contact_injures_target_when_roll_succeeds(self):
        a=Arena(left=0,top=0,width=900,height=400,drag_override=0)
        a.team_stats[0].set('critical',10)
        a.attacking_team=0
        a.rng=random.Random(1)  # First random() is 0.134 < 20%
        blue=Egg(0,0,150,200,vx=500)
        red=Egg(1,1,212,200)
        a.eggs=[blue,red]
        for _ in range(40):a.step(1/240)
        self.assertEqual(red.injury_turns,2)
        self.assertTrue(any(ev.kind=='injury' for ev in a.events))

if __name__=='__main__':
    unittest.main()
