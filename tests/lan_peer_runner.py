"""Separate-process LAN smoke peer. Invoked by test_v08; no personal saves."""
import os,sys,time,json,logging
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
role,folder=sys.argv[1:];folder=Path(folder)
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';os.environ['MARBLE_SAVE_PATH']=str(folder/(role+'.json'))
logging.disable(logging.CRITICAL)
import pygame
from main import Game
G=Game();G.count=4;N=G.net
if role=='host':
 N.host(0);(folder/'port').write_text(str(N.link.port))
else:
 end=time.monotonic()+10
 while not (folder/'port').exists() and time.monotonic()<end:time.sleep(.01)
 N.ip='127.0.0.1:'+(folder/'port').read_text();N.join()
end=time.monotonic()+15;ready=False;frames=0;observed=set();seen_motion=False;completed=False
while time.monotonic()<end:
 G.update(.02);frames+=1
 if N.peer_load is not None and not ready:N.set_ready();ready=True
 if N.playing:
  observed.add(G.turn_number)
  if G.state=='moving':seen_motion=True
  if G.state=='aim':
   team=G._input_team()
   if team==G.turn:
    e=next(e for e in G.arena.living(team) if N.owns(e))
    G.lock_shot(e.id,(e.x+55,e.y))
   elif team is not None:G.ready_defense()
  if frames%8==0:G.draw_hud()
  if G.turn_number>=4:
   (folder/(role+'.done')).write_text(json.dumps(dict(turns=sorted(observed),motion=seen_motion,frames=frames)))
   completed=True;break
 time.sleep(.002)
# Keep both sockets alive until each peer has received the final snapshot.
if completed:
 grace=time.monotonic()+2
 while time.monotonic()<grace and not all((folder/(r+'.done')).exists() for r in ('host','guest')):
  N.poll(.01);N.publish(.05);time.sleep(.005)
N.stop();pygame.quit()
if not completed:raise SystemExit('Separate peer timed out: '+N.notice)
