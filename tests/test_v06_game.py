"""Exercise the real SDL/Pygame menu, audio, input and turn loop headlessly."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame
from main import Game
from abilities import PreparedSkill,SkillLoadout,FUTURE_SKILLS,can_prepare
from perks import PERKS
from inventory import active
from audio import SoundBox

class GameIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'MARBLE_SAVE_PATH':str(Path(self.tmp.name)/'profile.json')})
        self.env.start();self.g=Game()
    def tearDown(self):
        pygame.quit();self.env.stop();self.tmp.cleanup()
    def click(self,action,value=None):
        g=self.g;g.draw_menu()
        rect=next(r for r,a,v in g.menu.widgets if a==action and v==value)
        g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=rect.center))
    def test_real_menu_navigation_shop_inventory_stats_and_match(self):
        g=self.g
        self.click('page','shop');self.click('draw','passive')
        self.assertGreater(g.menu.draw_time,0);g.update(1.5);g.draw_menu()
        self.assertEqual(len(g.profile['history']),1)
        self.click('page','home');self.click('page','inventory')
        self.click('slot',('passive',0));self.click('item',('passive','heavy'));self.click('equip',('passive','heavy'))
        self.click('tab','stats');self.click('stat',('power',5));self.assertEqual(active(g.profile)['stats']['power'],5)
        self.click('page','home');self.click('page','setup');self.click('count',4);self.click('start')
        self.assertEqual(g.state,'aim');g.draw_hud()
        self.assertEqual(g._stat_sliders,[]);self.assertEqual(g.arena.team_perks[0],['heavy'])
        self.assertEqual(g.arena.living(0)[0].r,23.75)
    def test_reward_once_and_red_profile_persists(self):
        g=self.g;g.red_loadout['stats']['toughness']=20;g.start_match()
        before=g.profile['coins']
        for e in g.arena.living(1):e.alive=False
        g._finish_turn();self.assertEqual(g.state,'over');self.assertEqual(g.profile['coins'],before+100)
        g._finish_turn();self.assertEqual(g.profile['coins'],before+100)
        self.assertEqual(g.store.load()['red_loadout']['stats']['toughness'],20)
        g.draw_hud()
    def test_local_test_currency_always_enabled_and_tab_pass(self):
        g=self.g;before=g.profile['coins'];g.development=False
        ev=pygame.event.Event(pygame.KEYDOWN,key=pygame.K_p)
        g.handle_event(ev);self.assertEqual(g.profile['coins'],before+1000)
        g.development=True;g.handle_event(ev);self.assertEqual(g.profile['coins'],before+2000)
        g.start_match();g.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_TAB))
        self.assertEqual(g.turn_number,2)
    def test_curve_controls_only_equipped_and_curve_locked(self):
        g=self.g;g.start_match();ev=pygame.event.Event(pygame.KEYDOWN,key=pygame.K_c)
        g.handle_event(ev);self.assertEqual(g.curve,0)
        g.arena.team_perks[0]=['curve'];g.handle_event(ev);self.assertEqual(g.curve,.75)
        e=g.arena.living(0)[0];g.lock_shot(e.id,(e.x,e.y+40))
        g.defense_ready=True;g._start_reveal();g._launch_revealed()
        self.assertEqual(e.curve,.75)
    def test_eyes_reveals_only_at_defense_lock_and_eight_turn_cooldown(self):
        g=self.g;g.start_match();g.arena.team_perks[0]=['eyes']
        red=g.arena.living(1)[0];g.prepared[1]=PreparedSkill('brickwall',red.id)
        g.detect_defense();self.assertFalse(g.eyes_notice)
        g.defense_ready=True;g.detect_defense();self.assertEqual(g.eyes_notice[0],'BRICKWALL')
        self.assertEqual(g.eyes_ready[0],9)
        g.eyes_notice={};g.turn_number=8;g.detect_defense();self.assertFalse(g.eyes_notice)
        g.turn_number=9;g.detect_defense();self.assertTrue(g.eyes_notice)
    def test_clutch_resets_once_not_one_v_one(self):
        g=self.g;g.count=4;g.start_match();g.loadouts[0].ready_at['tiger']=50
        for e in g.arena.living(0)[:-1]:e.alive=False
        g.arena.check_survivors();g.process_clutch()
        self.assertEqual(g.loadouts[0].remaining('tiger',1),0)
        g.loadouts[0].ready_at['tiger']=50;g.arena.check_survivors();g.process_clutch()
        self.assertEqual(g.loadouts[0].ready_at['tiger'],50)
        g.count=1;g.start_match();g.loadouts[0].ready_at['tiger']=50
        g.arena.check_survivors();g.process_clutch();self.assertEqual(g.loadouts[0].ready_at['tiger'],50)
    def test_cola_actual_game_launch_and_single_explosion_sound(self):
        g=self.g;g.cpu_mode='off';g.start_match();g.loadouts[0]=SkillLoadout(['cola','tiger'])
        e=g.arena.living(0)[0];g._set_prepared(0,e);g.lock_shot(e.id,(e.x,e.y+16))
        g.ready_defense();g._start_reveal();g._launch_revealed()
        self.assertEqual(g.sound.play_counts['cola_charge'],1)
        for _ in range(1200):
            g.update(1/120)
            if g.sound.play_counts.get('cola_explosion'):break
        self.assertEqual(g.sound.play_counts.get('cola_explosion'),1)
        self.assertFalse(e.alive)
    def test_existing_and_missing_audio_channels_mute_volume(self):
        g=self.g
        for key in ('cola_charge','cola_explosion'):
            self.assertIn('decoded',g.sound.diagnostics[key]);self.assertIsNotNone(g.sound.samples[key])
        for _ in range(45):g.sound.play('clack')
        charge=g.sound.play('cola_charge');explosion=g.sound.play('cola_explosion')
        self.assertTrue(charge.get_busy());self.assertTrue(explosion.get_busy())
        g.sound.muted=True;self.assertIsNone(g.sound.play('cola_charge'))
        g.sound.update(.01);self.assertEqual(charge.get_volume(),0)
        g.sound.muted=False;g.sound.sfx_volume=.3;g.sound.update(.01)
        self.assertAlmostEqual(charge.get_volume(),.3,delta=.01)
        audio=SoundBox(Path(self.tmp.name)/'missing')
        self.assertIsNotNone(audio.fallback['cola_explosion']);self.assertTrue(audio.play('cola_explosion').get_busy())
    def test_badly_named_mp4_logs_fallback(self):
        root=Path(self.tmp.name)/'assets';(root/'sfx').mkdir(parents=True)
        (root/'sfx'/'cola_charge.mp3').write_bytes(b'\x00\x00\x00\x18ftypmp42'+b'\x00'*100)
        with self.assertLogs('marble.audio',level='WARNING') as log:audio=SoundBox(root)
        self.assertIsNone(audio.samples['cola_charge']);self.assertIsNotNone(audio.fallback['cola_charge'])
        self.assertTrue(any('cola_charge' in s for s in log.output))
    def test_backgrounds_missing_and_valid_png(self):
        g=self.g
        for page in ('home','shop','inventory','setup'):
            g.menu.go(page);g.draw_menu();g.update(.02)
        # Exercise optional PNG decoder without writing into user assets.
        image=pygame.Surface((32,32));image.fill((255,220,190))
        path=Path(self.tmp.name)/'theme.png';pygame.image.save(image,path)
        g.menu.themes['main_menu']=pygame.transform.smoothscale(pygame.image.load(str(path)),(1280,900))
        g.menu.go('home');g.draw_menu()
    def test_all_eight_planned_skills_released(self):
        from abilities import SKILLS
        from economy import SKILL_RARITIES
        self.assertEqual(len(SKILLS),8);self.assertFalse(FUTURE_SKILLS)
        self.assertEqual(set(SKILLS),set(SKILL_RARITIES))
        for key in SKILLS:
            self.assertTrue(can_prepare(key,True) or can_prepare(key,False))

    def test_cpu_and_local_full_turn_paths(self):
        g=self.g
        for mode in ('easy','normal','hard','off'):
            g.cpu_mode=mode;g.count=4;g.start_match();g._finish_turn(passed=True)
            g.ready_defense()
            if mode=='off':
                e=g.arena.living(1)[0];g.lock_shot(e.id,(e.x,e.y-80));g.ready_defense()
            for _ in range(1800):
                g.update(1/60)
                if g.turn_number>=3 or g.state=='over':break
            self.assertGreaterEqual(g.turn_number,3,mode)
            g.draw_hud()
    def test_animated_effects_do_not_change_coordinates(self):
        from physics import Event
        g=self.g;g.start_match();g.state='moving'
        before=[(e.x,e.y) for e in g.arena.eggs]
        g.spawn_effect(Event('cola_explosion',640,450,0,1));g.draw_hud()
        self.assertEqual(before,[(e.x,e.y) for e in g.arena.eggs])
        self.assertLessEqual(len(g.particles),400)
    def test_zero_skills_allowed_and_persisted(self):
        g=self.g;active(g.profile)['skills']=[]
        g.start_match()
        for key in (pygame.K_1,pygame.K_2,pygame.K_e):
            g.handle_event(pygame.event.Event(pygame.KEYDOWN,key=key))
        e=g.arena.living(0)[0];g._set_prepared(0,e)
        self.assertIsNone(g.prepared[0])
        self.assertEqual(active(g.store.load())['skills'],[])
    def test_music_load_fade_switch_and_mute(self):
        import shutil
        root=Path(self.tmp.name)/'assets';(root/'music').mkdir(parents=True)
        sample=Path(__file__).resolve().parents[1]/'assets'/'sfx'/'cola_charge.mp3'
        for scene in ('main_menu','shop','inventory','match'):
            shutil.copy2(sample,root/'music'/(scene+'.mp3'))
        audio=SoundBox(root)
        for scene in ('main_menu','shop','inventory','match'):
            audio.music(scene);audio.update(.31)
            self.assertEqual(audio.current_music,scene)
            self.assertIsNone(audio.pending_music)
            self.assertTrue(pygame.mixer.music.get_busy())
        audio.muted=True;audio.update(.02)
        self.assertEqual(pygame.mixer.music.get_volume(),0)
    def test_hidden_defense_not_rendered_until_reveal(self):
        g=self.g;g.start_match();e=g.arena.living(1)[0]
        g.prepared[1]=PreparedSkill('brickwall',e.id);g.defense_ready=True
        with patch.object(g,'draw_egg_disc') as draw:
            g.draw_board()
            enemy_calls=[c for c in draw.call_args_list if c.args[3]==1]
            self.assertTrue(all(c.kwargs['skill'] is None for c in enemy_calls))
        g.state='reveal'
        with patch.object(g,'draw_egg_disc') as draw:
            g.draw_board()
            self.assertTrue(any(c.kwargs['skill']=='brickwall' for c in draw.call_args_list))

    def test_actual_run_loop_exit(self):
        pygame.event.post(pygame.event.Event(pygame.QUIT));self.g.run()
        self.assertFalse(pygame.get_init())
