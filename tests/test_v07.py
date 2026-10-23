"""v0.7 regression coverage: combat interactions, maps, UI, migration and launch selection."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import math
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
import pygame
from physics import Arena,Egg,Obstacle,make_match,MAX_PULL,BASE_POWER_SCALE,Event
from maps import Zone,MAPS,apply_map,music_for
from abilities import SKILLS,PreparedSkill,SkillLoadout,can_prepare
from save_data import SaveStore,default_profile
from inventory import active,equip_slot
from economy import draw
from skins import SKINS
try:
    from tests.test_game_phases import build_game
except ModuleNotFoundError:
    from test_game_phases import build_game


def duel(drag=0):
    a=Arena(left=0,top=0,width=2000,height=1200,drag_override=drag)
    a.eggs=[Egg(0,0,300,600),Egg(1,1,500,600)]
    return a

class CombatTests(unittest.TestCase):
    def test_bull_attack_speed_and_wood(self):
        a=duel();a.obstacles=[Obstacle(0,350,575,30,50,'wood')]
        a.shoot(0,100,0,ability='bull')
        self.assertAlmostEqual(a.eggs[0].speed,100*BASE_POWER_SCALE*1.5)
        for _ in range(40):a.step(1/240)
        self.assertFalse(a.obstacles[0].alive)
    def test_bull_power_bonus_at_equal_impact_speed(self):
        speeds=[]
        for skill in ('','bull'):
            a=duel();a.eggs[1].x=400;a.shoot(0,100,0,ability=skill);a.eggs[0].vx=800
            for _ in range(200):
                a.step(1/480)
                if a.eggs[1].speed>0:break
            speeds.append(a.eggs[1].speed)
        self.assertAlmostEqual(speeds[1]/speeds[0],1.5,places=5)

    def test_bull_half_power_counter_choreography_and_injury(self):
        a=duel();guard,enemy=a.eggs;enemy.x=380
        a.activate_defense(guard.id,'bull');enemy.vx=-500
        a.step(.01)
        self.assertEqual(enemy.speed,0);self.assertTrue(a.counters);self.assertTrue(a.moving())
        origin=guard.x
        for _ in range(22):a.step(.01)
        self.assertLess(guard.x,origin);self.assertEqual(enemy.speed,0)
        for _ in range(32):a.step(.01)
        self.assertFalse(a.counters);self.assertGreater(enemy.vx,0)
        self.assertEqual(enemy.injury_turns,3)
        kinds=[e.kind for e in a.events]
        self.assertLess(kinds.index('bull_freeze'),kinds.index('bull_impact'))
        self.assertEqual(kinds.count('bull_impact'),1)
    def test_bull_cannot_counter_through_wall(self):
        a=duel();guard,enemy=a.eggs;enemy.x=390
        a.obstacles=[Obstacle(0,340,570,10,60,'steel')]
        a.activate_defense(0,'bull');enemy.vx=-500
        for _ in range(50):a.step(.005)
        self.assertFalse(guard.guard_used);self.assertFalse(a.counters)
    def test_infinity_blocks_high_speed_and_is_immune_to_injury(self):
        a=duel();guard,enemy=a.eggs
        a.activate_defense(0,'infinity');enemy.vx=-9000
        for _ in range(400):
            a.step(1/480)
            self.assertGreaterEqual(math.hypot(enemy.x-guard.x,enemy.y-guard.y),guard.r+enemy.r+7.99)
        self.assertEqual((guard.x,guard.y),(300,600));self.assertEqual(guard.speed,0)
        self.assertLess(enemy.speed,17);self.assertFalse(a.injure(0))
    def test_infinity_immune_to_cola_and_tiger_wind(self):
        for ability in ('cola','tiger'):
            a=duel(drag=3);guard,enemy=a.eggs;enemy.x=guard.x+100
            a.activate_defense(0,'infinity');a.shoot(1,-16,0,ability=ability)
            for _ in range(1000):
                a.step(1/240);a.trigger_cola_if_stopped()
            self.assertEqual((guard.x,guard.y),(300,600));self.assertEqual(guard.speed,0)
    def test_ankle_sidestep_attacker_continues_and_invulnerability_expires(self):
        a=duel();guard,enemy=a.eggs;enemy.x=350
        a.activate_defense(0,'ankle_breaker');enemy.vx=-700
        for _ in range(15):a.step(1/240)
        self.assertNotEqual(guard.y,600);self.assertEqual(guard.speed,0)
        self.assertLess(enemy.vx,0);self.assertTrue(a.invulnerable(guard));self.assertFalse(a.injure(0))
        a.step(.8);self.assertFalse(a.invulnerable(guard));self.assertTrue(a.injure(0))
    def test_ankle_near_edge_causes_attacker_ringout(self):
        a=duel();a.eggs[0].x=25;a.eggs[1].x=100
        a.activate_defense(0,'ankle_breaker');a.eggs[1].vx=-900
        for _ in range(100):a.step(.005)
        self.assertTrue(a.eggs[0].alive);self.assertFalse(a.eggs[1].alive)
    def test_curse_unlock_and_once_survives_clutch_reset(self):
        g=build_game();g.loadouts[0]=SkillLoadout(['curse','bull'])
        self.assertFalse(g.loadouts[0].ready('curse',10));self.assertTrue(g.loadouts[0].ready('curse',11))
        g.loadouts[0].commit('curse',11)
        g.arena.events.append(Event('clutch',300,400,0,1));g.process_clutch()
        self.assertFalse(g.loadouts[0].ready('curse',50));self.assertTrue(g.loadouts[0].ready('bull',50))
    def test_curse_random_full_pull_clears_old_attack_flags_and_respects_immunity(self):
        a=make_match(4);a.rng=random.Random(42)
        targets=a.living(1);a.activate_defense(targets[0].id,'infinity')
        targets[1].tiger=True;targets[1].curve=1.5
        a.cast_curse(0)
        self.assertEqual(targets[0].speed,0)
        for e in targets[1:]:self.assertAlmostEqual(e.speed,MAX_PULL*BASE_POWER_SCALE)
        self.assertFalse(targets[1].tiger);self.assertEqual(targets[1].curve,0)
        angles={round(math.atan2(e.vy,e.vx),3) for e in targets[1:]};self.assertEqual(len(angles),3)
    def test_new_defenses_consumed_even_on_miss_and_cleared(self):
        for skill in ('bull','ankle_breaker','infinity'):
            g=build_game();g.loadouts[1]=SkillLoadout([skill]);red=g.arena.living(1)[0];blue=g.arena.living(0)[-1]
            g.prepared[1]=PreparedSkill(skill,red.id);g.locked_attack=(blue.id,16,0)
            self.assertEqual(red.defense,'')
            g._launch_revealed();self.assertEqual(red.defense,skill)
            self.assertGreater(g.loadouts[1].remaining(skill,1),0)
            g._finish_turn();self.assertEqual(red.defense,'')
    def test_cpu_only_chooses_correct_role(self):
        from types import SimpleNamespace
        g=build_game('hard');g.loadouts[1]=SkillLoadout(['ankle_breaker','infinity'])
        g._cpu_defense();self.assertIn(g.prepared[1].name,('ankle_breaker','infinity'))
        g.turn=1;g.prepared[1]=None;g.locked_attack=None
        e=g.arena.living(1)[0];g._cpu_prepare_attack(SimpleNamespace(egg_id=e.id,dx=0,dy=100))
        self.assertIsNone(g.prepared[1])

class MapTests(unittest.TestCase):
    def test_local_ice_normal_mud_drag_order(self):
        speeds=[]
        for floor in ('ice','normal','mud'):
            a=duel();a.drag_override=None;a.zones=[Zone(250,500,300,200,floor)]
            a.eggs=a.eggs[:1];a.eggs[0].vx=200;a.step(.1);speeds.append(a.eggs[0].speed)
        self.assertGreater(speeds[0],speeds[1]);self.assertGreater(speeds[1],speeds[2])
    def test_local_terrain_changes_accuracy(self):
        a=duel();e=a.eggs[0];normal=a.cone(e)
        a.zones=[Zone(280,580,40,40,'mud')]
        self.assertNotEqual(a.cone(e),normal);e.x=600;self.assertEqual(a.cone(e),normal)
    def test_steel_walls_bounce_then_open(self):
        a=make_match(4);apply_map(a,'steel_ring');e=a.eggs[0]
        e.x=a.left-20;e.vx=-500;a.resolve_edges()
        self.assertTrue(e.alive);self.assertGreater(e.vx,0)
        a.turn_number=13;e.x=a.left-20;a.resolve_edges()
        self.assertTrue(a.walls_open);self.assertFalse(e.alive)
        self.assertEqual(sum(ev.kind=='walls_open' for ev in a.events),1)
    def test_all_maps_large_passives_finite_nonoverlap_spawns(self):
        for key in MAPS:
            for perks in (['juggernaut','heavenly','friendship'],['rat','sniper','curve']):
                a=make_match(10);apply_map(a,key);a.configure_perks({0:perks,1:perks},10)
                for e in a.living():self.assertTrue(a.can_place(e,e.x,e.y),(key,perks,e.id))
                a.shoot(a.living(0)[0].id,0,-180,ability='tiger')
                for _ in range(250):a.step(1/240)
                self.assertTrue(all(math.isfinite(e.x+e.y+e.vx+e.vy) for e in a.eggs))
                self.assertTrue(all(e.speed<=18000.001 for e in a.living()))
    def test_barricade_continuous_breakable_wall(self):
        a=make_match(4);apply_map(a,'barricade')
        self.assertEqual(len(a.obstacles),8);self.assertTrue(all(o.material=='wood' for o in a.obstacles))
        self.assertLessEqual(a.obstacles[0].x,a.left)
        self.assertGreaterEqual(a.obstacles[-1].x+a.obstacles[-1].w,a.right)
        for one,two in zip(a.obstacles,a.obstacles[1:]):self.assertGreaterEqual(one.x+one.w,two.x)
    def test_map_and_clutch_music(self):
        a=make_match(4)
        for key in MAPS:
            apply_map(a,key);self.assertEqual(music_for(a),MAPS[key][3]);self.assertEqual(music_for(a,True),'clutch')

class ProfileAndLauncherTests(unittest.TestCase):
    def test_v1_migration_preserves_currency_items_stats_red(self):
        raw={'version':1,'coins':70,'owned_skills':['brickwall','tiger','cola','chain'],'owned_perks':['heavy','eyes'],
             'loadouts':{'default':{'skills':['cola','chain'],'perks':['eyes'],'stats':{'power':30}}},
             'red_loadout':{'skills':['brickwall'],'perks':['heavy'],'stats':{'speed':20}}}
        new=SaveStore.sanitize(raw)
        self.assertEqual(new['coins'],70);self.assertEqual(new['version'],3)
        self.assertEqual(active(new)['skills'],['cola','chain']);self.assertEqual(active(new)['stats']['power'],30)
        self.assertEqual(new['red_loadout']['stats']['speed'],20);self.assertEqual(new['settings']['language'],'ko')
    def test_skin_draw_100_duplicate_40_and_roundtrip(self):
        p=default_profile();rng=Mock();rng.choices.return_value=['Epic'];rng.choice.return_value='rainbow'
        result=draw(p,'skin',rng);self.assertEqual(p['coins'],400);self.assertFalse(result['duplicate'])
        result=draw(p,'skin',rng);self.assertEqual(p['coins'],340);self.assertEqual(result['refund'],40)
        equip_slot(p,'skin','rainbow',0);p['settings']['language']='en';p['settings']['window_shake']=True
        with tempfile.TemporaryDirectory() as tmp:
            store=SaveStore(Path(tmp)/'p.json');store.save(p);saved=store.load()
        self.assertEqual(active(saved)['skin'],'rainbow');self.assertEqual(saved['settings']['language'],'en');self.assertTrue(saved['settings']['window_shake'])
    def test_slot_replaces_swaps_and_rejects_exclusive_perks_atomically(self):
        p=default_profile();p['owned_skills']=list(SKILLS);p['owned_perks']+=['juggernaut']
        equip_slot(p,'skill','bull',1);self.assertEqual(active(p)['skills'],['brickwall','bull'])
        equip_slot(p,'skill','bull',0);self.assertEqual(active(p)['skills'],['bull','brickwall'])
        equip_slot(p,'passive','heavy',0)
        with self.assertRaises(ValueError):equip_slot(p,'passive','juggernaut',1)
        self.assertEqual(active(p)['perks'],['heavy'])
    def test_launcher_prefers_any_working_pygame_over_new_install(self):
        import bootstrap
        options=[['wrong-python'],['python313'],['python312']]
        def probe(command,code):return command==['python313'] and 'import pygame' in code
        with patch.object(bootstrap,'check',side_effect=probe):self.assertEqual(bootstrap.find_runtime(options),(['python313'],True))
    def test_launcher_install_only_supported_64bit_fallback(self):
        import bootstrap
        def probe(command,code):return command==['python312'] and 'struct' in code
        with patch.object(bootstrap,'check',side_effect=probe):self.assertEqual(bootstrap.find_runtime([['python314'],['python312']]),(['python312'],False))

class V07SDLTests(unittest.TestCase):
    def setUp(self):
        from main import Game
        self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'MARBLE_SAVE_PATH':str(Path(self.tmp.name)/'p.json')});self.env.start();self.g=Game()
    def tearDown(self):self.g.fx.restore_window();pygame.quit();self.env.stop();self.tmp.cleanup()
    def test_language_and_f10_pause_resume_persists(self):
        g=self.g;g.start_match();g.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F10))
        self.assertEqual(g.state,'menu');self.assertEqual(g.menu.page,'settings');time=g.turn_left
        g.update(.5);self.assertEqual(g.turn_left,time)
        g.menu.perform('language','en');g.draw_menu();g.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
        self.assertEqual(g.state,'aim');self.assertEqual(g.store.load()['settings']['language'],'en')
    def test_eyes_precise_target_sound_and_overlay_once(self):
        g=self.g;g.cpu_mode='off';g.start_match();g.arena.team_perks[0]=['eyes'];e=g.arena.living(1)[2]
        g.prepared[1]=PreparedSkill('bull',e.id);g.detect_defense();self.assertFalse(g.eyes_targets)
        g.defense_ready=True;g.detect_defense();g.detect_defense()
        self.assertEqual(g.eyes_targets[0],e.id);self.assertEqual(g.eyes_notice[0],'BULL')
        self.assertEqual(g.sound.play_counts['eyes_activate'],1);self.assertGreater(g.eyes_flash,0);g.draw_hud()
    def test_curse_cast_trembles_visually_then_releases(self):
        g=self.g;g.cpu_mode='off';g.start_match();g.turn_number=11;g.arena.turn_number=11
        g.loadouts[0]=SkillLoadout(['curse']);e=g.arena.living(0)[0]
        g._set_prepared(0,e);g.lock_shot(e.id,(e.x,e.y+50));g.ready_defense();g._launch_revealed()
        self.assertEqual(g.state,'curse');before=[(e.x,e.y) for e in g.arena.eggs]
        g.draw_hud();self.assertEqual(before,[(e.x,e.y) for e in g.arena.eggs]);self.assertFalse(g.arena.moving())
        g.update(1);self.assertEqual(g.state,'curse');g.update(1);self.assertEqual(g.state,'moving')
        self.assertTrue(g.arena.moving());self.assertEqual(g.sound.play_counts['curse_release'],1)
        self.assertFalse(g.loadouts[0].ready('curse',100))
    def test_curse_optional_image_and_fallback(self):
        g=self.g;g.start_match();g.state='curse';g.menu.assets.images['themes/노곡빈.png']=None;self.assertIsNone(g.curse_background((560,675)))
        g.menu.assets.images['themes/노곡빈.png']=pygame.Surface((64,64));g.menu.assets.images['themes/노곡빈.png'].fill((100,0,200))
        self.assertEqual(g.curse_background((560,675)).get_size(),(560,675));g.draw_hud()
    def test_every_menu_tab_language_map_and_assets_render(self):
        from perks import PERKS
        g=self.g
        for lang in ('ko','en'):
            g.profile['settings']['language']=lang
            for page in ('home','setup','shop','settings','inventory'):
                g.menu.go(page);g.draw_menu()
            for kind,items in [('skill',SKILLS),('passive',PERKS),('skin',SKINS)]:
                g.menu.tab=kind
                for key in items:g.menu.selected=(kind,key);g.draw_menu()
        for key in MAPS:g.map_key=key;g.start_match();g.draw_hud()
        for file in ('skills_a','skills_b','perks_a','perks_b','perks_c','gui_panels','skill_frames'):
            self.assertIsNotNone(g.menu.assets.image('gui/'+file+'.png'))
        self.assertIsNotNone(g.menu.assets.image('vfx/eyes_of_heaven.png'))
    def test_unique_selected_frame_and_render_does_not_move_world(self):
        g=self.g;g.start_match();before=[(e.x,e.y) for e in g.arena.eggs]
        for skill in SKILLS:
            g.loadouts[0]=SkillLoadout([skill]);g.draw_hud()
        self.assertEqual(before,[(e.x,e.y) for e in g.arena.eggs])
    def test_window_shake_restores_position_and_defaults_off(self):
        from effects import ImpactFX
        fx=ImpactFX();self.assertFalse(self.g.profile['settings']['window_shake'])
        window=Mock();window.position=(100,200);fx.window=window;fx.settings={'window_shake':True};fx.shake=.3
        with patch('effects.sys.platform','win32'):fx.move_window()
        self.assertEqual(fx.window_origin,(100,200));fx.configure({'window_shake':False})
        self.assertEqual(window.position,(100,200));self.assertIsNone(fx.window_origin)
    def test_window_motion_disabled_during_aim_and_menus(self):
        g=self.g;g.start_match();g.profile['settings']['window_shake']=True
        window=Mock();window.position=(100,200);g.fx.window=window;g.fx.shake=.3
        with patch('effects.sys.platform','win32'):g.update(.01)
        self.assertFalse(g.fx.allow_window_motion);self.assertEqual(window.position,(100,200))
        g.state='moving';g.chain_window=1.;g.chain_target=g.arena.living(0)[0].id;g.fx.shake=.3
        with patch('effects.sys.platform','win32'):g.update(.01)
        self.assertFalse(g.fx.allow_window_motion);self.assertEqual(window.position,(100,200))

    def test_effects_off_and_particle_sprite_bounds(self):
        g=self.g;g.start_match();g.state='moving';g.profile['settings'].update(screen_shake=False,flash=False,hit_stop=False)
        for _ in range(80):g.spawn_effect(Event('bull_impact',600,400,0,1.4))
        g.update(.01);self.assertLessEqual(len(g.particles),400);self.assertLessEqual(len(g.fx.rings),32)
        g.draw_hud();self.assertFalse(g.fx.settings['screen_shake'])
    def test_wav_mislabeled_mp3_loads_using_signature(self):
        import shutil
        from audio import SoundBox
        root=Path(self.tmp.name)/'audio';(root/'music').mkdir(parents=True)
        # Pygame's supplied Ogg sample is not guaranteed; construct a WAV stream
        # with an .mp3 name to exercise the same container-sniffing branch.
        import wave
        with wave.open(str(root/'music/main_menu.mp3'),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(44100);f.writeframes(b'\0\0'*44100)
        sound=SoundBox(root);sound.music('main_menu');sound.update(.4)
        self.assertTrue(pygame.mixer.music.get_busy())

if __name__=='__main__':unittest.main()
