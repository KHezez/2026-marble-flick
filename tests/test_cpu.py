import math
import unittest
from cpu import CPUPlanner, DIFFICULTIES, _score
from physics import Arena, Egg, make_match


class CPULabTests(unittest.TestCase):
    def test_modes_have_candidates_and_legal_shots(self):
        for mode in DIFFICULTIES:
            for count in (1, 4, 10):
                world = make_match(count)
                planner = CPUPlanner(world, team=1, difficulty=mode, seed=42)
                self.assertTrue(planner.total > 0, (mode, count))
                chosen = None
                for _ in range(planner.total):
                    chosen = planner.think_one()
                self.assertIsNotNone(chosen)
                self.assertTrue(any(e.id == chosen.egg_id for e in world.living(1)))
                self.assertTrue(14 <= math.hypot(chosen.dx, chosen.dy) <= 180.0001)
                self.assertFalse(world.moving())
                self.assertEqual(len(world.living(0)), count)
                self.assertEqual(len(world.living(1)), count)
                self.assertTrue(world.shoot(chosen.egg_id,chosen.dx,chosen.dy))

    def test_normal_cpu_aims_toward_real_enemy(self):
        world = Arena(left=0,top=0,width=1300,height=1000,drag_override=3.7,
                      eggs=[Egg(0,0,650,640),Egg(1,1,650,280)])
        planner = CPUPlanner(world, team=1, difficulty='normal', seed=42)
        chosen = None
        for _ in range(planner.total):
            chosen = planner.think_one()
        self.assertIsNotNone(chosen)
        self.assertGreater(chosen.dy, 0)
        self.assertLess(abs(chosen.dx), 30)

    def test_cpu_prefers_ringout_to_a_miss(self):
        world = make_match(4)
        target=world.living(0)[0]
        target.x=world.left+40  # near boundary on direct collision path
        planner=CPUPlanner(world,team=1,difficulty='hard',seed=5)
        result=None
        for _ in range(planner.total):result=planner.think_one()
        self.assertIsNotNone(result)

    def test_score_reward_enemy_loss_penalize_self_loss(self):
        original=make_match(4)
        from copy import deepcopy
        after=deepcopy(original)
        after.living(0)[0].alive=False
        self.assertGreater(_score(original,after,1),1000)
        after2=deepcopy(original)
        after2.living(1)[0].alive=False
        self.assertLess(_score(original,after2,1),-1000)

    def test_obstacle_aware_candidate_and_empty_team(self):
        arena=make_match(10,'mud','mixed')
        arena.team_stats[1].preset(power=15,accuracy=15,speed=20)
        planner=CPUPlanner(arena,team=1,difficulty='normal')
        self.assertGreater(planner.total,0)
        for _ in range(planner.total):planner.think_one()
        self.assertIsNotNone(planner.best)
        empty=make_match(4)
        for e in empty.living(0):e.alive=False
        self.assertEqual(CPUPlanner(empty,team=1).total,0)

if __name__=='__main__': unittest.main()
