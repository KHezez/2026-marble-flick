"""v0.8 media, boss progression, ownership and real TCP integration regressions."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import json,math,random,socket,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import pygame
from main import Game
from physics import make_match,Event
from save_data import SaveStore,default_profile
from skins import SKINS,photo,paint
from economy import draw
from net_transport import Link,encode
from network_game import checked_loadout
from abilities import PreparedSkill
from inventory import active
import bosses

class BossTests(unittest.TestCase):
    def test_three_distinct_patterns_and_actual_forces(self):
        patterns=[]
        for key in bosses.BOSSES:
            a=make_match(4);b=bosses.install(a,key);found=[]
            for _ in range(3):
                for e in a.eggs:e.vx=e.vy=0
                a.living(0)[0].x=b.x+150;a.living(0)[0].y=b.y
                bosses.plan(a);found.append(a.boss_state['pattern']);bosses.fire(a)
                self.assertTrue(any(e.speed>0 for e in a.living()))
                self.assertTrue(all(math.isfinite(e.vx) and math.isfinite(e.vy) for e in a.eggs))
            patterns.append(found)
        self.assertEqual(len({tuple(p) for p in patterns}),3)
    def test_two_phases_and_reward_is_exclusive_idempotent(self):
        a=make_match(4);boss=bosses.install(a,'gokbin');p=default_profile()
        bosses.hurt(a,9999);self.assertTrue(boss.alive);self.assertEqual(boss.skin,'gokbin_curse')
        self.assertEqual(a.boss_state['phase'],2);self.assertFalse(bosses.grant(p,a.boss_state))
        bosses.hurt(a,9999);self.assertFalse(boss.alive);self.assertTrue(bosses.grant(p,a.boss_state))
        self.assertFalse(bosses.grant(p,a.boss_state));self.assertEqual(p['owned_skins'].count('gokbin_curse'),1)
        self.assertEqual(SaveStore.sanitize(p)['boss_clears']['gokbin'],2)
        p['coins']=1000000;rng=random.Random(6)
        for _ in range(3000):self.assertNotEqual(draw(p,'skin',rng)['item'],'gokbin_curse')
    def test_boss_collision_and_ringout_damage(self):
        a=make_match(4);b=bosses.install(a,'warden');e=a.living(0)[0]
        e.x=b.x;e.y=b.y+b.r+e.r-1;e.vy=-500;a.attacking_team=0
        hp=a.boss_state['hp'];a._egg_collision(e,b,True);self.assertLess(a.boss_state['hp'],hp)
        hp=a.boss_state['hp'];b.x=a.left-10;a.resolve_edges();self.assertTrue(b.alive);self.assertLess(a.boss_state['hp'],hp)
    def test_coop_hp_scaling_and_final_no_extra_phase(self):
        a=make_match(4);bosses.install(a,'gokbin',True);self.assertEqual(a.boss_state['hp'],1044)
        bosses.hurt(a,9999);self.assertEqual(a.boss_state['hp'],1336)
        bosses.hurt(a,9999);bosses.hurt(a,9999);self.assertTrue(a.boss_state['defeated'])
    def test_locked_reward_sanitization_and_old_save_migration(self):
        p=default_profile();p['coins']=123;p['owned_skins'].append('gokbin_curse')
        self.assertNotIn('gokbin_curse',SaveStore.sanitize(p)['owned_skins'])
        p['boss_clears']={'gokbin':2};self.assertIn('gokbin_curse',SaveStore.sanitize(p)['owned_skins'])
        self.assertEqual(SaveStore.sanitize({'version':2,'coins':78})['coins'],78)

class GameTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,MARBLE_SAVE_PATH=self.temp.name+'/host.json');self.env.start()
        self.h=Game();self.h.count=4;self.c=None
    def tearDown(self):
        self.h.net.stop()
        if self.c:self.c.net.stop()
        pygame.quit();self.env.stop();self.temp.cleanup()
    def pump(self,condition=lambda:False,limit=2):
        end=time.monotonic()+limit
        while time.monotonic()<end:
            for g in (self.h,self.c):
                if g:g.net.poll(.01);g.net.publish(.05)
            if condition():return
            time.sleep(.001)
        self.assertTrue(condition(), 'LAN condition timed out: '+self.h.net.notice+' / '+(self.c.net.notice if self.c else ''))
    def connect(self,mode='pvp'):
        self.h.net.mode=mode;self.h.net.host(0)
        os.environ['MARBLE_SAVE_PATH']=self.temp.name+'/client.json';self.c=Game()
        self.c.net.ip='127.0.0.1:'+str(self.h.net.link.port);self.c.net.join()
        self.pump(lambda:self.h.net.peer_load is not None and self.c.net.peer_load is not None)
        self.h.net.set_ready();self.c.net.set_ready()
        self.pump(lambda:self.h.net.playing and self.c.net.playing)
    def test_photo_skins_same_hitbox_original_alpha_crop_and_pages(self):
        g=self.h;g.start_match();before=[(e.r,e.mass,e.x,e.y) for e in g.arena.eggs]
        for key in ('cheeky','verity','gubby','man_face','gokbin','gokbin_curse'):
            active(g.profile)['skin']=key;g.draw_hud();self.assertEqual(before,[(e.r,e.mass,e.x,e.y) for e in g.arena.eggs])
            self.assertIsNotNone(photo(key,80));self.assertEqual(max(photo(key,80).get_size()),80)
        raw=pygame.image.load('assets/skins/gubby.png');self.assertLess(raw.get_bounding_rect().w,raw.get_width())
        for lang in ('ko','en'):
            g.profile['settings']['language']=lang
            for page in ('home','boss','lan','inventory'):
                g.menu.go(page);g.menu.tab='skin'
                for index in (0,1):g.menu.skin_page=index;g.draw_menu()
    def test_solo_boss_full_runtime_and_reward_persistence(self):
        g=self.h;g.boss_kind='gokbin';g.start_match();g.draw_hud()
        g._finish_turn(passed=True);g.update_cpu(1);self.assertTrue(g.arena.boss_state['telegraphs'])
        g.ready_defense();g._start_reveal();g._launch_revealed();self.assertEqual(g.state,'boss_windup')
        g.draw_hud();g.update(1);self.assertEqual(g.state,'moving')
        bosses.hurt(g.arena,9999);g.update(.01);g.draw_hud();self.assertEqual(g.arena.boss_state['phase'],2)
        bosses.hurt(g.arena,9999);g._finish_turn();self.assertEqual(g.winner,0)
        self.assertIn('gokbin_curse',g.store.load()['owned_skins'])
        coins=g.profile['coins'];g._finish_turn();self.assertEqual(g.profile['coins'],coins)
    def test_pvp_real_tcp_private_preparation_and_shot_sync(self):
        self.connect();h,c=self.h,self.c
        blue=h.arena.living(0)[0];red=c.arena.living(1)[0]
        c._set_prepared(1,red);c.ready_defense()
        self.pump(lambda:h.defense_ready)
        self.assertIsNone(h.locked_attack);self.assertEqual(h.prepared[1].name,'brickwall')
        # Host preparations are absent from guest JSON until reveal.
        h.loadouts[0].selected=1;h._set_prepared(0,blue)
        snap=h.net.snapshot();self.assertIsNone(snap['prepared']['0'])
        h.lock_shot(blue.id,(blue.x,blue.y+100));snap=h.net.snapshot()
        self.assertEqual(snap['locked'],(-1,0,0));self.assertEqual(snap['game']['locked_curve'],0)
        h.update(.01);h.update(.7);self.assertEqual(h.state,'moving')
        self.pump(lambda:c.state=='moving')
        self.assertEqual(c.arena.living(0)[0].vy,h.arena.living(0)[0].vy)
        self.assertTrue(next(e for e in c.arena.eggs if e.id==red.id).brickwall)
        c.draw_hud();h.draw_hud()
    def test_remote_attack_validation_and_replay(self):
        self.connect();h,c=self.h,self.c;h._finish_turn(passed=True)
        self.pump(lambda:c.turn==1)
        red=c.arena.living(1)[0];blue=c.arena.living(0)[0]
        c.lock_shot(blue.id,(blue.x,blue.y-100));self.pump(lambda:h.net.last_seq>=1)
        self.assertIsNone(h.locked_attack)
        c.lock_shot(red.id,(red.x,red.y-100));self.pump(lambda:h.locked_attack is not None)
        old=h.locked_attack
        h.net.command(1,dict(type='command',action='shot',match=h.net.match_id,turn=h.turn_number,seq=1,args={'egg':red.id,'pos':[0,0]}))
        self.assertEqual(old,h.locked_attack)
        h.ready_defense();h.update(.01);h.update(.7);self.pump(lambda:c.state=='moving')
    def test_coop_ownership_rotation_stats_and_debug_restriction(self):
        self.connect('coop');h,c=self.h,self.c
        self.assertEqual([e.owner for e in h.arena.living(0)],[0,0,1,1]);self.assertIsNone(c._input_team())
        foreign=next(e for e in h.arena.living(0) if e.owner==1)
        h.lock_shot(foreign.id,(foreign.x,foreign.y+100));self.assertIsNone(h.locked_attack)
        h._finish_turn(passed=True);h._finish_turn(passed=True);self.pump(lambda:c.turn_number==3)
        self.assertEqual(c._input_team(),0);self.assertIsNone(h._input_team())
        c.lock_shot(foreign.id,(foreign.x,foreign.y+100));self.pump(lambda:h.locked_attack is not None)
        coins=h.profile['coins'];h.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_p));self.assertEqual(h.profile['coins'],coins)
        h.net.stop();h.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_p));self.assertEqual(h.profile['coins'],coins+1000)
    def test_coop_individual_passives_and_no_same_family(self):
        self.connect('coop');h=self.h
        h.net.loads[0]['perks']=['heavenly','heavy'];h.net.peer_load['perks']=['rat']
        active(h.profile)['perks']=['heavenly','heavy'];h.net.configure_arena()
        a=h.arena;first=next(e for e in a.living(0) if e.owner==0);second=next(e for e in a.living(0) if e.owner==1)
        self.assertAlmostEqual(first.r,23.75);self.assertAlmostEqual(second.r,13.3)
        self.assertEqual(len([e for e in a.living(0) if e.owner==0]),1)
        self.assertAlmostEqual(a.mult_for(first,'power'),2.5);self.assertAlmostEqual(a.mult_for(second,'power'),1.15)
        raw=active(h.profile).copy();raw['perks']=['heavy','juggernaut']
        with self.assertRaises(ValueError):checked_loadout(raw,4)
        raw['perks']=[];raw['stats']={k:30 for k in raw['stats']}
        with self.assertRaises(ValueError):checked_loadout(raw,4)
    def test_coop_boss_reward_both_peers_only_after_phase2(self):
        self.connect('boss');h,c=self.h,self.c
        bosses.hurt(h.arena,9999);self.pump(lambda:c.arena.boss_state['phase']==2)
        self.assertNotIn('gokbin_curse',c.profile['owned_skins'])
        bosses.hurt(h.arena,9999);h._finish_turn();self.pump(lambda:c.state=='over')
        self.assertIn('gokbin_curse',h.store.load()['owned_skins']);self.assertIn('gokbin_curse',c.store.load()['owned_skins'])
        coins=c.profile['coins'];c.net.receive_state(json.loads(encode(h.net.snapshot())))
        self.assertEqual(c.profile['coins'],coins)
    def test_disconnect_returns_to_lobby_without_reward(self):
        self.connect();coins=self.h.profile['coins'];self.c.net.stop()
        self.pump(lambda:not self.h.net.playing);self.assertEqual(self.h.state,'menu');self.assertEqual(self.h.profile['coins'],coins)
    def test_online_timeout_and_opponent_eye_information_is_private(self):
        self.connect();h,c=self.h,self.c
        h.turn_left=.001;h.update(.02);self.assertEqual(h.turn,1)
        self.pump(lambda:c.turn==1)
        h.arena.team_perks[1]=['eyes'];blue=h.arena.living(0)[0]
        h._set_prepared(0,blue);h.ready_defense()
        self.assertEqual(h.eyes_targets[1],blue.id)
        self.pump(lambda:c.eyes_targets.get(1)==blue.id)
        self.assertIn('BRICKWALL',c.eyes_notice[1])
        h.loadouts[0].selected=1
        snap=h.net.snapshot();self.assertEqual(snap['books']['0']['selected'],0)
        h._set_prepared(0,blue);self.assertEqual(h.prepared[0].name,'brickwall')
        c.draw_hud();h.draw_hud()
    def test_pvp_guest_reward_is_for_red_and_not_repeated(self):
        self.connect();h,c=self.h,self.c
        for e in h.arena.living(0):e.alive=False
        h._finish_turn();self.pump(lambda:c.state=='over')
        self.assertEqual(h.reward_amount,50);self.assertEqual(c.reward_amount,100)
        coins=c.profile['coins'];c.net.receive_state(json.loads(encode(h.net.snapshot())))
        self.assertEqual(c.profile['coins'],coins)
    def test_online_chain_only_shooter_owner_redirects(self):
        self.connect('coop');h,c=self.h,self.c
        e=next(e for e in h.arena.living(0) if e.owner==0)
        h.arena.shoot(e.id,0,-100,ability='chain');e.chain_ready=True
        h.state='moving';h.chain_target=e.id;h.chain_window=1.75
        self.pump(lambda:c.chain_target==e.id)
        c.mouse=(800,400);c._chain_redirect();self.pump(lambda:h.net.last_seq>=1)
        self.assertEqual(e.chain_followups,0)
        h.mouse=(800,400);h._chain_redirect();self.assertEqual(e.chain_followups,1)
    def test_real_game_loop_can_open_boss_menu_and_exit(self):
        g=self.h;original=g.update;frames=[]
        def update(dt):
            original(dt);frames.append(g.state)
            if len(frames)==1:g.menu.perform('page','boss')
            elif len(frames)==2:g.menu.perform('boss_start','warden')
            elif len(frames)==4:pygame.event.post(pygame.event.Event(pygame.QUIT))
        g.update=update;g.run();self.assertGreaterEqual(len(frames),4);self.assertIn('aim',frames)

    def test_all_provided_mp3_decode(self):
        from audio import SoundBox,MUSIC
        s=self.h.sound
        for name,filename in s.FILES.items():
            if (s.root/'sfx'/filename).exists():self.assertTrue(s.diagnostics[name].startswith('decoded'),filename)
        for path in (s.root/'music').glob('*.mp3'):
            pygame.mixer.music.load(str(path));pygame.mixer.music.play();self.assertTrue(pygame.mixer.music.get_busy(),str(path))
        pygame.mixer.music.stop()

class TransportTests(unittest.TestCase):
    def test_malformed_and_nonfinite_packets_disconnect(self):
        for payload in (b'{bad}\n',b'{"x":NaN}\n',b'['*1500+b'\n'):
            host=Link.host(0,'127.0.0.1');client=socket.create_connection(('127.0.0.1',host.port));host.poll()
            client.sendall(payload)
            end=time.monotonic()+1
            while not host.closed and time.monotonic()<end:host.poll();time.sleep(.001)
            self.assertTrue(host.closed);client.close();host.close()
    def test_two_independent_processes_play_three_turns(self):
        import subprocess,sys
        with tempfile.TemporaryDirectory() as folder:
            script=Path(__file__).with_name('lan_peer_runner.py')
            processes=[subprocess.Popen([sys.executable,str(script),role,folder],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for role in ('host','guest')]
            try:
                for proc in processes:
                    out,err=proc.communicate(timeout=22);self.assertEqual(proc.returncode,0,err+out)
                for role in ('host','guest'):
                    result=json.loads((Path(folder)/(role+'.done')).read_text())
                    self.assertTrue(result['motion']);self.assertGreaterEqual(max(result['turns']),4)
            finally:
                for proc in processes:
                    if proc.poll() is None:proc.kill();proc.wait()

    def test_encode_rejects_nonfinite(self):
        with self.assertRaises(ValueError):encode({'x':float('nan')})

if __name__=='__main__':unittest.main()
