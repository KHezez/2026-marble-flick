import unittest
from physics import Arena, Egg
from stats import drag_resistance_multiplier, power_transfer_multiplier, TeamStats


def simulate(speed=0,power=0,toughness=0,contact=False):
    a=Arena(left=0,top=0,width=3000,height=600)
    a.team_stats[0].set('speed',speed)
    a.team_stats[0].set('power',power)
    a.team_stats[1].set('toughness',toughness)
    shooter=Egg(0,0,150,250)
    target=Egg(1,1,310,250)
    a.eggs=[shooter,target] if contact else [shooter]
    a.shoot(0,180,0)
    max_v=0
    for _ in range(900):
        a.step(1/240)
        if contact:max_v=max(max_v,target.speed)
        if not a.moving():break
    return (shooter.x-150,target.x-310,max_v)

class SplitTests(unittest.TestCase):
    def test_speed_is_mostly_distance(self):
        base=simulate()
        fast=simulate(speed=30)
        self.assertGreater(fast[0],base[0]*1.4)
        self.assertLess(fast[0],base[0]*1.75)

    def test_power_is_knockback_not_travel(self):
        base=simulate(contact=True)
        strong=simulate(power=30,contact=True)
        self.assertGreater(strong[1],base[1]*1.6)
        self.assertAlmostEqual(strong[0],base[0],delta=1)
        self.assertGreater(strong[2],base[2]*1.65)

    def test_power_doesnt_change_unopposed_travel(self):
        self.assertAlmostEqual(simulate(power=30)[0],simulate(power=0)[0],delta=.1)

    def test_toughness_reduces_knockback(self):
        self.assertLess(simulate(toughness=30,contact=True)[1],simulate(toughness=0,contact=True)[1])

    def test_resistance_and_injury(self):
        s=TeamStats(speed=30,power=30)
        self.assertAlmostEqual(drag_resistance_multiplier(s),.7)
        self.assertAlmostEqual(drag_resistance_multiplier(s,True),.85)
        self.assertAlmostEqual(power_transfer_multiplier(s),1.8)
        self.assertAlmostEqual(power_transfer_multiplier(s,True),.9)

if __name__=='__main__':unittest.main()
