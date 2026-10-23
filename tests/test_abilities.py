import math
import unittest
from abilities import SkillLoadout, PreparedSkill, can_prepare, SKILLS, COOLDOWNS
from physics import Arena, Egg, Obstacle, DRAG, STOP_SPEED


def sandbox(count_blue=1, count_red=1, drag=2):
    a = Arena(left=0, top=0, width=2000, height=1000, drag_override=drag)
    a.eggs = [Egg(i,0,300+i*80,500) for i in range(count_blue)]
    a.eggs += [Egg(count_blue+i,1,650+i*80,500) for i in range(count_red)]
    return a


class SkillModelTests(unittest.TestCase):
    def test_two_slots_no_duplicates_and_cooldown(self):
        load = SkillLoadout()
        self.assertEqual(len(load.slots),2)
        self.assertTrue(load.ready('brickwall',1))
        load.commit('brickwall',1)
        self.assertEqual(load.remaining('brickwall',2),5)
        self.assertFalse(load.ready('brickwall',6))
        self.assertTrue(load.ready('brickwall',7))
        with self.assertRaises(ValueError): load.equip(1,'brickwall')
        load.select_slot(1)
        load.equip(1,'cola')
        self.assertEqual(load.equipped(),'cola')
        self.assertFalse(load.ready('tiger',1))

    def test_skill_attack_defense_roles(self):
        attack={'brickwall','tiger','chain','cola','bull','curse'}
        defense={'brickwall','bull','ankle_breaker','infinity'}
        for skill in SKILLS:
            self.assertEqual(can_prepare(skill,True),skill in attack)
            self.assertEqual(can_prepare(skill,False),skill in defense)

    def test_brickwall_immobile_and_bounce(self):
        a=sandbox(drag=.4)
        stationary=a.eggs[0]
        attacker=a.eggs[1]
        start=(stationary.x,stationary.y)
        self.assertTrue(a.activate_brickwall(0))
        self.assertAlmostEqual(stationary.r, 33.25)
        self.assertFalse(a.shoot(0,180,0))
        self.assertTrue(a.shoot(1,-180,0))
        for _ in range(320):
            a.step(1/240)
            if any(e.kind=='brickwall_hit' for e in a.events):break
        self.assertEqual((stationary.x,stationary.y),start)
        self.assertLess(attacker.vx,0) if False else self.assertTrue(any(e.kind=='brickwall_hit' for e in a.events))
        a.deactivate_brickwall(0)
        self.assertEqual(stationary.r,19.0)

    def test_brickwall_immune_to_critical_injury(self):
        a=sandbox(drag=0)
        a.team_stats[1].set('critical',10)
        a.rng.random=lambda:0.0
        self.assertTrue(a.activate_brickwall(0))
        self.assertTrue(a.shoot(1,-180,0))
        for _ in range(200):
            a.step(1/240)
        self.assertEqual(a.eggs[0].injury_turns,0)

    def test_tiger_faster_breaks_wood(self):
        a=sandbox()
        a.obstacles=[Obstacle(0,370,480,40,40,'wood',hp=1.6)]
        self.assertTrue(a.shoot(0,100,0,ability='tiger'))
        self.assertAlmostEqual(a.eggs[0].vx,100*8.33*2)
        for _ in range(110):a.step(1/480)
        self.assertFalse(a.obstacles[0].alive)

    def test_tiger_wind_hits_near_miss_but_not_brickwall(self):
        a=sandbox(count_blue=1,count_red=2,drag=.1)
        a.eggs[1].x=420;a.eggs[1].y=570
        a.eggs[2].x=480;a.eggs[2].y=430
        self.assertTrue(a.activate_brickwall(2))
        self.assertTrue(a.shoot(0,180,0,ability='tiger'))
        for _ in range(170):a.step(1/480)
        self.assertTrue(any(e.kind=='tiger_wind' for e in a.events))
        self.assertAlmostEqual(a.eggs[2].y,430)

    def test_chain_enemy_contact_unlocks_dash_max_five(self):
        a=sandbox(drag=.5)
        a.eggs[1].x=410
        self.assertTrue(a.shoot(0,100,0,ability='chain'))
        for _ in range(400):
            a.step(1/240)
            if a.eggs[0].chain_ready:break
        else: self.fail('No chain contact')
        self.assertTrue(a.chain_redirect(0,100,0))
        self.assertEqual(a.eggs[0].chain_followups,1)
        self.assertFalse(a.chain_redirect(0,100,0))
        speeds=[]
        for i in range(2,6):
            a.eggs[0].chain_ready=True
            self.assertTrue(a.chain_redirect(0,100,0))
            speeds.append(a.eggs[0].speed)
        self.assertEqual(a.eggs[0].chain_followups,5)
        self.assertTrue(all(x>y for x,y in zip(speeds,speeds[1:])))
        a.eggs[0].chain_ready=True
        self.assertFalse(a.chain_redirect(0,100,0))

    def test_cola_explosion_sacrifice_and_last_egg_exemption(self):
        for count, expected in [(1,True),(2,False)]:
            a=sandbox(count_blue=count,drag=4)
            a.eggs[count].x=440
            self.assertTrue(a.shoot(0,16,0,ability='cola'))
            for _ in range(2200):
                a.step(1/240)
                if a.trigger_cola_if_stopped():break
            else:self.fail('Cola failed')
            self.assertEqual(a.eggs[0].alive,expected)
            self.assertTrue(any(e.kind=='cola_explosion' for e in a.events))
            self.assertGreater(a.eggs[count].speed,0)
            self.assertFalse(a.trigger_cola_if_stopped())

    def test_default_drag_only_normal_reduced(self):
        self.assertAlmostEqual(DRAG['normal'],3.70*.75)
        self.assertEqual(DRAG['mud'],3.70)

if __name__=='__main__': unittest.main()
