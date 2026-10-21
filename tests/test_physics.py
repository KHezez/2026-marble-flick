import math
import unittest
from physics import Arena, Egg, Obstacle, make_match, BASE_POWER_SCALE, MAX_PULL, DRAG, vector_from_pull

class PhysicsTests(unittest.TestCase):
    def test_game_counts(self):
        for count in (1,4,5,6,7,8,9,10):
            a = make_match(count, obstacle_mode='none')
            self.assertEqual(len(a.living(0)),count)
            self.assertEqual(len(a.living(1)),count)
            for i,e in enumerate(a.eggs):
                for f in a.eggs[i+1:]:
                    self.assertGreaterEqual(math.hypot(e.x-f.x,e.y-f.y), e.r+f.r)

    def test_all_team_compositions_face_vertically(self):
        for count in (1,4,5,6,7,8,9,10):
            with self.subTest(count=count):
                arena=make_match(count)
                blue=arena.living(0)
                red=arena.living(1)
                self.assertTrue(all(e.y > arena.top + arena.height/2 for e in blue))
                self.assertTrue(all(e.y < arena.top + arena.height/2 for e in red))
                self.assertAlmostEqual(sum(e.x for e in blue)/len(blue),
                                       arena.left + arena.width/2)
                self.assertAlmostEqual(sum(e.x for e in red)/len(red),
                                       arena.left + arena.width/2)

    def test_slingshot_direction_is_reversed(self):
        x,y = vector_from_pull(650,600,650,750)
        self.assertEqual((x,y),(0,-150))
        x,y = vector_from_pull(650,300,540,300)
        self.assertEqual((x,y),(110,0))

    def test_friction_order_and_distance(self):
        self.assertLess(DRAG['ice'], DRAG['normal'])
        self.assertLess(DRAG['normal'], DRAG['mud'])
        distances = {}
        for floor in ('normal','ice','mud'):
            arena = Arena(left=0,top=0,width=10000,height=10000,floor=floor, mud_variance=False)
            e=Egg(0,0,500,500)
            arena.eggs=[e]
            arena.shoot(e.id, MAX_PULL, 0)
            for _ in range(1800):
                arena.step(1/240)
                if not arena.moving():
                    break
            distances[floor]=e.x-500
        self.assertGreater(distances['ice'],distances['normal'])
        self.assertGreater(distances['normal'],distances['mud'])
        self.assertTrue(400 < distances['normal'] < 600, distances)

    def test_hit_transfers_momentum(self):
        a = Arena(left=0,top=0,width=500,height=300,drag_override=0.0)
        a.eggs = [Egg(0,0,90,150,vx=600),Egg(1,1,165,150)]
        for _ in range(90):
            a.step(1/240)
        self.assertLess(a.eggs[0].speed,90)
        self.assertGreater(a.eggs[1].speed,450)
        self.assertTrue(any(e.kind=='hit' for e in a.events))

    def test_out_of_bounds_is_fall_not_reflection(self):
        a = Arena(left=0,top=0,width=300,height=300,drag_override=0.0)
        e = Egg(0,0,299,150,vx=500)
        a.eggs.append(e)
        a.step(1/240)
        self.assertFalse(e.alive)
        self.assertEqual(a.events[-1].kind,'fall')

    def test_shoot_requires_live_idle_egg(self):
        a = make_match(1)
        self.assertFalse(a.shoot(0,0,0))
        self.assertTrue(a.shoot(0,180,0))
        self.assertFalse(a.shoot(1,180,0))
        self.assertAlmostEqual(a.eggs[0].vx, MAX_PULL * BASE_POWER_SCALE)

    def test_steel_bounces(self):
        a = Arena(left=0,top=0,width=500,height=400,drag_override=0.0)
        a.obstacles = [Obstacle(0,240,150,40,90,'steel')]
        e = Egg(0,0,180,185,vx=900)
        a.eggs = [e]
        for _ in range(30):
            a.step(1/240)
        self.assertLess(e.vx,0)
        self.assertTrue(a.obstacles[0].alive)

    def test_wood_can_break(self):
        a = Arena(left=0,top=0,width=600,height=400,drag_override=0.0)
        a.obstacles = [Obstacle(0,240,150,40,90,'wood',hp=.4)]
        e = Egg(0,0,180,185,vx=900)
        a.eggs=[e]
        for _ in range(30):
            a.step(1/240)
        self.assertFalse(a.obstacles[0].alive)
        self.assertTrue(any(ev.kind=='wood_break' for ev in a.events))

    def test_normal_surface_stops(self):
        a = Arena(left=0,top=0,width=2000,height=400)
        e = Egg(0,0,100,150,vx=800)
        a.eggs=[e]
        for _ in range(1000):
            a.step(1/240)
        self.assertEqual(e.speed,0)

if __name__=='__main__':
    unittest.main()
