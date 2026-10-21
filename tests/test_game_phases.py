"""Game logic smoke checks even on build machines without an SDL display."""
import random
import sys
import types
import unittest

try:
    import pygame  # type: ignore
except ImportError:
    pygame = types.ModuleType('pygame')
    class Rect:
        def __init__(self,*args):
            if len(args)==1: args=tuple(args[0])
            self.x,self.y,self.w,self.h=args
            self.size=(self.w,self.h)
            self.left,self.top,self.right,self.bottom=self.x,self.y,self.x+self.w,self.y+self.h
            self.centerx,self.centery=self.x+self.w//2,self.y+self.h//2
        def collidepoint(self,p):return self.left<=p[0]<self.right and self.top<=p[1]<self.bottom
    pygame.Rect=Rect
    pygame.mouse=types.SimpleNamespace(get_pos=lambda:(640,450))
    sys.modules['pygame']=pygame

from abilities import PreparedSkill, SkillLoadout
from main import Game
from physics import make_match


def build_game(cpu='off'):
    g=Game.__new__(Game)
    g.state='aim';g.arena=make_match(4);g.turn=0;g.turn_number=1;g.turn_left=25
    g.cpu_mode=cpu;g.rng=random.Random(3);g.count=4;g.floor='normal'
    g.dragging_id=None;g.brick_expiry={};g.prepared={0:None,1:None}
    g.locked_attack=None;g.defense_ready=False;g.e_armed=False
    g.loadouts={0:SkillLoadout(['brickwall','tiger']),1:SkillLoadout(['brickwall','cola'])}
    g.sound=types.SimpleNamespace(play=lambda name: None)
    g.status='';g.status_life=0;g.last_deviation=0
    g.speed_factor=1;g.travel_time=0;g.settle_time=0;g.accumulator=0
    g.chain_window=0;g.chain_target=None;g.cpu_planner=None;g.cpu_delay=0;g.frame=0
    g.particles=[];g.trails={e.id:[] for e in g.arena.eggs};g.mouse=(640,450)
    g.hit_count=0;g.debug=False
    return g


class TurnStateTests(unittest.TestCase):
    def test_two_locks_required_before_shooting(self):
        g=build_game()
        blue=g.arena.living(0)[0];red=g.arena.living(1)[0]
        g.lock_shot(blue.id,(blue.x,blue.y+130))
        self.assertEqual(g.state,'aim')
        self.assertFalse(g.arena.moving())
        self.assertEqual(g._input_team(),1)
        g._set_prepared(1,red)
        g.update(.1)
        self.assertEqual(g.state,'aim')
        self.assertFalse(g.arena.moving())
        g.ready_defense()
        g.update(.1)
        self.assertEqual(g.state,'reveal')
        self.assertFalse(g.arena.moving())
        g.update(.7)
        self.assertEqual(g.state,'moving')
        self.assertTrue(g.arena.moving())
        self.assertTrue(red.brickwall)
        self.assertEqual(g.brick_expiry[red.id],1)
        self.assertEqual(g.loadouts[1].remaining('brickwall',1),6)

    def test_attack_brickwall_survives_enemy_turn(self):
        g=build_game()
        bricks=g.arena.living(0)
        g._set_prepared(0,bricks[0])
        e=bricks[1]
        g.lock_shot(e.id,(e.x,e.y+120))
        g.ready_defense();g._start_reveal();g._launch_revealed()
        self.assertTrue(bricks[0].brickwall)
        self.assertEqual(g.brick_expiry[bricks[0].id],2)
        g._finish_turn()
        self.assertTrue(bricks[0].brickwall)
        g._finish_turn()
        self.assertFalse(bricks[0].brickwall)

    def test_tiger_lock_zero_aim_error_and_cooldown(self):
        g=build_game()
        blue=g.arena.living(0)[0]
        g.loadouts[0].selected=1
        g._set_prepared(0,blue)
        g.lock_shot(blue.id,(blue.x,blue.y+100))
        g.ready_defense();g._start_reveal();g._launch_revealed()
        self.assertTrue(blue.tiger)
        self.assertEqual(g.last_deviation,0)
        self.assertEqual(g.loadouts[0].remaining('tiger',1),7)

    def test_human_can_defend_when_cpu_attacks(self):
        g=build_game(cpu='easy')
        g.turn=1
        self.assertEqual(g._input_team(),0)
        g._set_prepared(0,g.arena.living(0)[0])
        self.assertEqual(g.prepared[0].name,'brickwall')
        g.ready_defense()
        self.assertTrue(g.defense_ready)

    def test_timeout_passes_without_spending(self):
        g=build_game()
        g.turn_left=.01
        g.update(.1)
        self.assertEqual(g.turn,1)
        self.assertEqual(g.turn_number,2)
        self.assertEqual(g.state,'aim')
        self.assertEqual(g.loadouts[0].remaining('brickwall',2),0)

if __name__=='__main__': unittest.main()
