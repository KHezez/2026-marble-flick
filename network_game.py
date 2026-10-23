"""Host-authoritative LAN play. Only validated commands cross into simulation.

The guest renders snapshots; hidden opponent preparation is stripped before
serialization. Cooperative players alternate blue turns and keep separate builds.
"""
from copy import deepcopy
from dataclasses import asdict
import math
import uuid
from net_transport import Link, PROTOCOL
from physics import Arena,Egg,Obstacle,Event,make_match
from maps import Zone,apply_map
from combat import Counter
from stats import TeamStats,STAT_CAPS
from abilities import SkillLoadout,PreparedSkill,SKILLS
from perks import validate,factor
from skins import SKINS
from inventory import active
import bosses


def checked_loadout(raw,count):
    if not isinstance(raw,dict):raise ValueError('Invalid loadout')
    skills=raw.get('skills',[]);perks=raw.get('perks',[]);stats=raw.get('stats',{})
    if not isinstance(skills,list) or len(skills)>2 or len(set(skills))!=len(skills) or any(s not in SKILLS for s in skills):raise ValueError('Invalid skills')
    if not isinstance(perks,list):raise ValueError('Invalid passives')
    validate(perks,count)
    if not isinstance(stats,dict) or set(stats)!=set(STAT_CAPS):raise ValueError('Invalid stats')
    if any(type(stats[k]) is not int or not 0<=stats[k]<=cap for k,cap in STAT_CAPS.items()) or sum(stats.values())>50:raise ValueError('Invalid points')
    if raw.get('skin') not in SKINS:raise ValueError('Invalid skin')
    return {key:deepcopy(raw[key]) for key in ('skills','perks','stats','skin')}


def book_data(book):
    return dict(slots=book.slots,selected=book.selected,ready_at=book.ready_at,used_once=list(book.used_once))


def read_book(raw):return SkillLoadout(raw['slots'],raw['selected'],raw['ready_at'],set(raw['used_once']))


GAME_FIELDS=('state','turn','turn_number','turn_left','defense_ready','chain_window','chain_target','winner','count',
             'cpu_mode','floor','map_key','reveal_timer','curse_timer','clutch_music','hit_count','locked_curve','travel_time')
ARENA_FIELDS=('left','top','width','height','floor','elapsed','attacking_team','active_shooter_id','boundary_walls',
              'walls_open','map_key','turn_number','boss_state')


class NetworkSession:
    def __init__(self,g):
        self.g=g;self.link=None;self.is_host=False;self.player=0;self.playing=False;self.applying=False
        self.mode='pvp';self.boss='gokbin';self.ip='127.0.0.1';self.ready=False;self.peer_ready=False
        self.peer_load=None;self.peer_config=None;self.notice='';self.match_id='';self.seq=0;self.last_seq=-1
        self.timer=0.;self.coop_owner=0;self.eyes_by_owner={0:1,1:1};self.books={};self.loads={};self.effects=[];self.granted=set();self.connected=False
    @property
    def active(self):return self.link is not None and not self.link.closed
    @property
    def guest(self):return self.active and self.playing and not self.is_host
    def say(self,ko,en):return ko if self.g.profile['settings']['language']=='ko' else en
    def stop(self,reason='연결 종료 / Disconnected'):
        if self.link:self.link.close(reason)
        self.playing=False;self.ready=self.peer_ready=False;self.connected=False
        self.g.state='menu';self.g.dragging_id=None;self.g.menu.go('lan');self.notice=reason
    def host(self,port=24872):
        self.stop();self.link=Link.host(port);self.is_host=True;self.player=0;self.peer_load=None
        self.notice=self.say('친구의 접속을 기다리는 중','Waiting for friend')
    def join(self):
        self.stop();self.link=Link.join(self.ip);self.is_host=False;self.player=1;self.peer_load=None
        self.notice=self.say('접속 중…','Connecting…')
    def config(self):
        g=self.g
        return dict(mode=self.mode,boss=self.boss,count=g.count,map_key=g.map_key,floor=g.floor,obstacles=g.obstacles,cpu_mode=g.cpu_mode)
    def send_hello(self):
        self.link.send(dict(type='hello',protocol=PROTOCOL,load=active(self.g.profile),config=self.config() if self.is_host else None))
    def set_ready(self):
        if not self.active or not self.connected or self.peer_load is None:return
        count=self.g.count if self.is_host else self.peer_config['count']
        checked_loadout(active(self.g.profile),count)
        self.ready=not self.ready;self.link.send(dict(type='ready',value=self.ready,load=active(self.g.profile)))
    def configure_arena(self):
        g=self.g;self.loads={0:checked_loadout(active(g.profile),g.count),1:checked_loadout(self.peer_load,g.count)}
        a=make_match(g.count,g.floor,g.obstacles);apply_map(a,g.map_key);g.arena=a
        self.books={i:SkillLoadout(list(load['skills'])) for i,load in self.loads.items()}
        self.coop_owner=0;self.eyes_by_owner={0:1,1:1}
        if self.mode=='pvp':
            for t,load in self.loads.items():
                a.team_stats[t]=TeamStats(**load['stats'])
                for e in a.living(t):e.owner=t;e.skin=load['skin']
            a.configure_perks({i:load['perks'] for i,load in self.loads.items()},g.count)
            g.loadouts=dict(self.books);g.cpu_mode='off'
        else:
            blue=a.living(0);split=(len(blue)+1)//2
            for i,load in self.loads.items():
                a.owner_stats[i]=TeamStats(**load['stats']);a.owner_perks[i]=list(load['perks'])
                members=blue[:split] if i==0 else blue[split:]
                for e in members:e.owner=i;e.skin=load['skin']
                if 'heavenly' in load['perks']:
                    for e in members[(len(members)+1)//2:]:e.alive=False
                for e in members:e.r=e.base_radius=19*factor(load['perks'],'size')
            red=g.red_loadout;a.team_stats[1]=TeamStats(**red['stats']);a.team_perks[1]=list(red['perks'])
            red_members=a.living(1)
            if 'heavenly' in red['perks']:
                for e in red_members[(len(red_members)+1)//2:]:e.alive=False
            for e in red_members:e.r=e.base_radius=19*factor(red['perks'],'size');e.skin=red['skin'];e.owner=2
            a.previous_counts={i:len(a.living(i)) for i in (0,1)}
            g.cpu_mode=g.cpu_mode if g.cpu_mode!='off' else 'normal'
            g.loadouts={0:self.books[0],1:SkillLoadout(red['skills'])};self.activate_owner()
            if self.mode=='boss':bosses.install(a,self.boss,coop=True);g.loadouts[1]=SkillLoadout([])
        g.trails={e.id:[] for e in a.eggs};g.board=g._make_board(g.floor);g.sync_music()
    def activate_owner(self):
        if self.mode=='pvp':return
        a=self.g.arena
        if not any(e.alive and e.owner==self.coop_owner for e in a.eggs):self.coop_owner=1-self.coop_owner
        load=self.loads[self.coop_owner];a.team_perks[0]=list(load['perks']);a.team_stats[0]=TeamStats(**load['stats'])
        self.g.loadouts[0]=self.books[self.coop_owner];self.g.eyes_ready[0]=self.eyes_by_owner[self.coop_owner]
    def next_turn(self):
        if self.playing and self.is_host and self.mode!='pvp':
            self.eyes_by_owner[self.coop_owner]=self.g.eyes_ready[0]
            if self.g.turn==0:self.coop_owner=1-self.coop_owner
            self.activate_owner()
    def input_team(self,player=None):
        g=self.g;pid=self.player if player is None else player
        if g.state!='aim':return None
        team=pid if self.mode=='pvp' else 0
        if self.mode!='pvp' and pid!=self.coop_owner:return None
        if team==g.turn and g.locked_attack is not None:return None
        if team!=g.turn and g.defense_ready:return None
        return team
    def owns(self,e,player=None):return e.owner==(self.player if player is None else player)
    def dispatch(self,action,**args):
        if not self.active or not self.playing or self.applying:return False
        self.seq+=1
        message=dict(type='command',action=action,args=args,seq=self.seq,match=self.match_id,turn=self.g.turn_number)
        if self.is_host:self.command(0,message)
        else:self.link.send(message)
        return True
    def command(self,pid,m):
        g=self.g
        if not self.playing or g.state=='over' or m.get('match')!=self.match_id or m.get('turn')!=g.turn_number:return
        seq=m.get('seq')
        if type(seq) is not int or (pid==1 and seq<=self.last_seq):return
        if pid==1:self.last_seq=seq
        action=m.get('action');args=m.get('args',{});team=self.input_team(pid)
        if not isinstance(args,dict):return
        def coord(v):return isinstance(v,list) and len(v)==2 and all(type(x) in (int,float) and math.isfinite(x) and abs(x)<10000 for x in v)
        egg=next((e for e in g.arena.living() if e.id==args.get('egg') and self.owns(e,pid)),None)
        self.applying=True;old_status=(g.status,g.status_life)
        try:
            if action=='shot' and team==g.turn and egg and coord(args.get('pos')):
                curve=args.get('curve',0)
                if type(curve) not in (int,float) or not math.isfinite(curve):return
                g.curve=max(-1.5,min(1.5,curve));g.lock_shot(egg.id,args['pos'])
            elif action=='prepare' and team is not None and egg:
                slot=args.get('slot')
                if type(slot) is not int or not 0<=slot<len(g.loadouts[team].slots):return
                g.loadouts[team].select_slot(slot);g._set_prepared(team,egg)
            elif action=='ready' and team is not None and team!=g.turn:g.ready_defense()
            elif action=='pass' and team==g.turn:g._finish_turn(passed=True)
            elif action=='chain' and g.state=='moving' and g.chain_window>0 and coord(args.get('pos')):
                e=next((e for e in g.arena.living() if e.id==g.chain_target),None)
                if e and self.owns(e,pid):
                    old=g.mouse;g.mouse=tuple(args['pos']);g._chain_redirect();g.mouse=old
        finally:
            self.applying=False
            # Localized preparation messages are private to the issuer.
            if pid==1 and action=='prepare':g.status,g.status_life=old_status
    def snapshot(self):
        g=self.g;a=g.arena;team=1 if self.mode=='pvp' else 0
        public=g.state!='aim'
        prepared={str(t):asdict(p) if p and (public or t==team) else None for t,p in g.prepared.items()}
        locked=g.locked_attack
        if not public and g.turn!=team and locked:locked=(-1,0,0)
        ad={k:deepcopy(getattr(a,k)) for k in ARENA_FIELDS}
        ad.update(eggs=[asdict(e) for e in a.eggs],obstacles=[asdict(o) for o in a.obstacles],zones=[asdict(z) for z in a.zones],
                  counters=[asdict(c) for c in a.counters],team_stats={i:asdict(s) for i,s in a.team_stats.items()},team_perks=a.team_perks,
                  owner_stats={i:asdict(s) for i,s in a.owner_stats.items()},owner_perks=a.owner_perks,last_resort_until=a.last_resort_until)
        books={str(t):book_data(b) for t,b in g.loadouts.items()}
        if not public:books[str(1-team)]['selected']=0
        game={k:getattr(g,k) for k in GAME_FIELDS}
        if not public and g.turn!=team:game['locked_curve']=0.
        return dict(type='state',match=self.match_id,game=game,arena=ad,prepared=prepared,
                    locked=locked,books=books,coop_owner=self.coop_owner,mode=self.mode,
                    eyes={str(t):v for t,v in g.eyes_notice.items() if t==team},targets={str(t):v for t,v in g.eyes_targets.items() if t==team},
                    effects=self.effects[-50:])
    def receive_state(self,m):
        g=self.g;new=m['match']!=self.match_id;self.match_id=m['match'];self.playing=True;self.mode=m['mode'];self.coop_owner=m['coop_owner']
        oldstate=g.state;oldturn=g.turn_number
        for k in GAME_FIELDS:setattr(g,k,m['game'][k])
        if new or oldturn!=g.turn_number or g.state!='aim':g.dragging_id=None;g.e_armed=False;g.curve=0.
        raw=m['arena'];a=Arena(**{k:raw[k] for k in ARENA_FIELDS})
        a.eggs=[Egg(**e) for e in raw['eggs']];a.obstacles=[Obstacle(**o) for o in raw['obstacles']]
        a.zones=[Zone(**z) for z in raw['zones']];a.counters=[Counter(**c) for c in raw['counters']]
        for key in ('team_stats','owner_stats'):setattr(a,key,{int(i):TeamStats(**s) for i,s in raw[key].items()})
        for key in ('team_perks','owner_perks','last_resort_until'):setattr(a,key,{int(i):s for i,s in raw[key].items()})
        g.arena=a;g.prepared={int(i):PreparedSkill(**v) if v else None for i,v in m['prepared'].items()}
        # Selection is local UI state; preparation commands carry its index.
        selected={i:b.selected for i,b in g.loadouts.items()}
        g.loadouts={int(i):read_book(v) for i,v in m['books'].items()}
        for i,b in g.loadouts.items():b.selected=min(selected.get(i,0),max(0,len(b.slots)-1))
        oldtargets=g.eyes_targets
        g.locked_attack=m['locked'];g.eyes_notice={int(i):v for i,v in m['eyes'].items()};g.eyes_targets={int(i):v for i,v in m['targets'].items()}
        if g.eyes_targets and oldtargets!=g.eyes_targets:g.eyes_flash=1.15;g.sound.play('eyes_activate')
        if new:
            g.board=g._make_board(g.floor);g.trails={e.id:[] for e in a.eggs};g.particles=[];g.reward_amount=0;g.rewarded=False
            self.notice='';g.sound.play('match')
        for ev in m['effects']:g.spawn_effect(Event(**ev))
        if oldstate!=g.state:
            if g.state=='moving':
                prep=g.prepared[g.turn];skill=prep.name if prep else ''
                cue='curse_release' if oldstate=='curse' else {'tiger':'tiger','chain':'chain','cola':'cola_charge','bull':'bull_charge'}.get(skill,'shoot')
                g.sound.play(cue)
            elif g.state=='reveal':g.sound.play('reveal')
            elif g.state=='curse':g.sound.play('curse_charge')
            elif g.state=='boss_windup':g.sound.play('boss_warning')
        g.sync_music()
        if g.state=='over' and self.match_id not in self.granted:
            self.granted.add(self.match_id);win=g.winner==(1 if self.mode=='pvp' else 0)
            g.reward_amount=100 if win else 50;g.profile['coins']+=g.reward_amount;g.rewarded=True
            if win and bosses.grant(g.profile,a.boss_state):g.sound.play('boss_reward')
            g.store.save(g.profile);g.sound.play('victory' if win else 'defeat')
    def poll(self,dt):
        if self.link is not None and self.link.closed and self.playing:self.stop('연결 종료 / Disconnected')
        if not self.active:return
        try:
            for m in self.link.poll():
                kind=m.get('type')
                if kind=='connected':self.connected=True;self.send_hello();self.g.sound.play('lan_connect')
                elif kind=='closed':self.stop(m['reason']);self.g.sound.play('lan_disconnect');return
                elif kind=='hello':
                    if m.get('protocol')!=PROTOCOL:raise ValueError('Different game version')
                    if not self.is_host:
                        self.peer_config=m['config'];self.mode=self.peer_config['mode'];self.boss=self.peer_config['boss']
                    count=self.g.count if self.is_host else self.peer_config['count']
                    self.peer_load=checked_loadout(m['load'],count);self.notice=self.say('연결됨. 양쪽 준비를 누르세요.','Connected. Both players press READY.')
                elif kind=='ready' and not self.playing:
                    self.peer_load=checked_loadout(m['load'],self.g.count if self.is_host else self.peer_config['count']);self.peer_ready=m.get('value') is True
                elif kind=='command' and self.is_host:self.command(1,m)
                elif kind=='state' and not self.is_host:self.receive_state(m)
            if self.is_host and self.ready and self.peer_ready and not self.playing:
                if self.mode!='pvp' and self.g.count==1:raise ValueError('협동은 4개 이상 / Coop requires 4+ marbles')
                self.playing=True;self.match_id=uuid.uuid4().hex;self.last_seq=-1;self.g.boss_kind=None;self.g.speed_factor=1
                self.g.start_match();self.configure_arena();self.timer=1.
        except (ValueError,TypeError,KeyError,IndexError,AttributeError) as exc:self.stop('LAN: '+str(exc))
    def publish(self,dt):
        if self.active and self.playing and self.is_host:
            self.timer+=dt
            if self.timer>=.05:
                self.timer=0.;self.link.send(self.snapshot());self.effects=[]
    def event(self,event):
        import pygame
        if not self.active:return False
        if event.type==pygame.QUIT:self.stop();return False
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE:self.stop();return True
            if event.key in (pygame.K_p,pygame.K_F10,pygame.K_f,pygame.K_j,pygame.K_k,pygame.K_v,pygame.K_F1,pygame.K_F2,pygame.K_F3):
                self.g.banner(self.say('LAN 연결 중에는 변경할 수 없습니다.','Unavailable during a LAN session.'));return True
        if self.playing and self.g.state=='over' and (event.type==pygame.MOUSEBUTTONDOWN or event.type==pygame.KEYDOWN and event.key==pygame.K_r):
            self.stop(self.say('다시 방을 만들거나 접속하세요.','Create or join a room to play again.'));return True
        return False
