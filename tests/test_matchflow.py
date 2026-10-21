import unittest
from physics import make_match

class MatchFlowTest(unittest.TestCase):
    def test_six_variations_finish_motion(self):
        for floor in ('normal','ice','mud'):
            for obstacle in ('none','mixed'):
                with self.subTest(floor=floor, obstacle=obstacle):
                    arena = make_match(10,floor,obstacle)
                    start = arena.eggs[2]
                    dest = arena.eggs[12]
                    self.assertTrue(arena.shoot(start.id, dest.x-start.x, dest.y-start.y))
                    for _ in range(3600):
                        arena.step(1/240)
                        if not arena.moving():
                            break
                    self.assertFalse(arena.moving())
                    self.assertLessEqual(len(arena.living(0)),10)
                    self.assertLessEqual(len(arena.living(1)),10)

if __name__ == '__main__':
    unittest.main()
