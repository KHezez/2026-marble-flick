"""Checks run inside the built EXE on the Windows build runner."""
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback


def headless():
    os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
    logging.disable(logging.CRITICAL)


def lan_peer(role,folder):
    headless();folder=Path(folder);os.environ['MARBLE_SAVE_PATH']=str(folder/(role+'.json'))
    import pygame
    from main import Game
    g=Game();g.count=4;n=g.net
    try:
        if role=='host':
            n.host(0);(folder/'port').write_text(str(n.link.port))
        else:
            end=time.monotonic()+25
            while not (folder/'port').exists() and time.monotonic()<end:time.sleep(.02)
            n.ip='127.0.0.1:'+(folder/'port').read_text();n.join()
        end=time.monotonic()+35;ready=False;frames=0;seen_motion=False
        while time.monotonic()<end:
            g.update(.02);frames+=1
            if n.peer_load is not None and not ready:n.set_ready();ready=True
            if n.playing:
                if g.state=='moving':seen_motion=True
                if g.state=='aim':
                    team=g._input_team()
                    if team==g.turn:
                        e=next(e for e in g.arena.living(team) if n.owns(e));g.lock_shot(e.id,(e.x+55,e.y))
                    elif team is not None:g.ready_defense()
                if frames%12==0:g.draw_hud()
                if g.turn_number>=4:
                    (folder/(role+'.done')).write_text(json.dumps(dict(turn=g.turn_number,motion=seen_motion,frames=frames)))
                    grace=time.monotonic()+4
                    while time.monotonic()<grace and not all((folder/(r+'.done')).exists() for r in ('host','guest')):
                        n.poll(.02);n.publish(.05);time.sleep(.01)
                    return 0
            time.sleep(.004)
        raise RuntimeError('LAN smoke timed out: '+n.notice)
    except Exception:
        (folder/(role+'.error')).write_text(traceback.format_exc(),encoding='utf-8');return 1
    finally:n.stop();pygame.quit()


def self_test(report_path):
    headless();report=Path(report_path).resolve();result={'ok':False,'frozen':bool(getattr(sys,'frozen',False))}
    try:
        import pygame
        from main import Game
        from audio import MUSIC
        from skins import SKINS,photo
        from save_data import SaveStore
        from runtime_paths import default_save_path,app_directory
        import bosses
        os.environ.pop('MARBLE_SAVE_PATH',None)
        save=default_save_path()
        assert '_MEI' not in str(save),str(save)
        result['save_path']=str(save);result['executable']=sys.executable
        with tempfile.TemporaryDirectory(prefix='marble-smoke-') as scratch:
            os.environ['MARBLE_SAVE_PATH']=str(Path(scratch)/'profile.json')
            g=Game();g.count=4
            for lang in ('ko','en'):
                g.profile['settings']['language']=lang
                for page in ('home','setup','inventory','shop','boss','lan','settings'):
                    g.menu.go(page);g.draw_menu()
            for key in ('cheeky','verity','gubby','man_face','gokbin','gokbin_curse'):assert photo(key,96) is not None,key
            assert g.menu.assets.image('themes/노곡빈.png') is not None
            assert len(SKINS)==17
            sfx=0;fallback=[]
            for name,filename in g.sound.FILES.items():
                channel=g.sound.play(name);assert channel and channel.get_busy(),name
                if (g.sound.root/'sfx'/filename).exists():
                    assert g.sound.diagnostics[name].startswith('decoded'),filename;sfx+=1
                else:fallback.append(filename)
            music=0
            for name in MUSIC.values():
                path=g.sound.root/'music'/name
                if path.exists():
                    pygame.mixer.music.load(str(path));pygame.mixer.music.play();assert pygame.mixer.music.get_busy(),name;music+=1
            for kind in bosses.BOSSES:
                g.boss_kind=kind;g.start_match();g.draw_hud()
                assert g.arena.boss_state['hp']==bosses.BOSSES[kind][2]*4
                if kind=='gokbin':
                    bosses.hurt(g.arena,99999);assert g.arena.boss_state['phase']==2
                    assert g.arena.boss_state['hp']==920;g.draw_hud()
                    bosses.hurt(g.arena,99999);g._finish_turn();assert 'gokbin_curse' in g.store.load()['owned_skins']
            g.profile['coins']=12345;g.store.save(g.profile);assert SaveStore().load()['coins']==12345
            # Run the real event loop and exit normally rather than killing it.
            pygame.event.post(pygame.event.Event(pygame.QUIT));g.run()
            result.update(sfx_decoded=sfx,music_decoded=music,fallback_sfx=fallback,skins=17,menus=True,bosses=True,saves=True,event_loop=True)
            if getattr(sys,'frozen',False):
                children=[subprocess.Popen([sys.executable,'--lan-smoke',role,scratch],env={**os.environ,'PYINSTALLER_RESET_ENVIRONMENT':'1'}) for role in ('host','guest')]
                try:
                    for child in children:assert child.wait(timeout=80)==0, 'EXE LAN child failed'
                    for role in ('host','guest'):
                        state=json.loads((Path(scratch)/(role+'.done')).read_text());assert state['motion'] and state['turn']>=4
                    result['two_exe_lan']='passed'
                finally:
                    for child in children:
                        if child.poll() is None:child.kill();child.wait()
            else:result['two_exe_lan']='not frozen; source tests cover this separately'
        result['ok']=True
    except Exception:result['error']=traceback.format_exc()
    report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if result['ok'] else 1
