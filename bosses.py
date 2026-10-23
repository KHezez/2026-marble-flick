"""Three telegraphed PvE encounters, including a genuine two-phase Gokbin boss."""
import math
from physics import Egg,Event,MAX_PULL,BASE_POWER_SCALE

BOSSES={
 'warden':('철갑 수호자','Iron Warden',190,'steel_ring','boss_warden'),
 'tempest':('폭풍 정령','Storm Spirit',170,'frozen_delta','boss_tempest'),
 'gokbin':('노곡빈','Gokbin',180,'classic','boss_gokbin'),
}

def install(arena,kind,coop=False):
    if kind not in BOSSES:raise ValueError('Unknown boss')
    arena.eggs=[e for e in arena.eggs if e.team==0]
    hp=round(BOSSES[kind][2]*(1.45 if coop else 1))*4
    boss=Egg(100,1,arena.left+arena.width/2,arena.top+140,r=48,mass=3.8,base_radius=48)
    boss.boss=True;boss.skin='gokbin' if kind=='gokbin' else 'gold' if kind=='warden' else 'ocean'
    from stats import TeamStats
    arena.eggs.append(boss);arena.team_perks[1]=[];arena.team_stats[1]=TeamStats();arena.boundary_walls=False
    arena.previous_counts={0:len(arena.living(0)),1:1}
    arena.boss_state={'kind':kind,'phase':1,'hp':hp,'max_hp':hp,'coop':coop,'action':0,
                      'pattern':'','target':[boss.x,arena.bottom-120],'telegraphs':[], 'defeated':False}
    # Clear a central lane: the large boss must not spawn in terrain geometry.
    arena.obstacles=[] if kind=='gokbin' else [o for o in arena.obstacles if not (o.x-boss.r < boss.x < o.x+o.w+boss.r and o.y-boss.r < boss.y < o.y+o.h+boss.r)]
    return boss

def hurt(arena,amount):
    state=arena.boss_state
    if not state or state['defeated']:return
    boss=next((e for e in arena.eggs if e.boss),None)
    if boss is None:return
    state['hp']=max(0,state['hp']-max(0,amount))
    arena.events.append(Event('boss_hit',boss.x,boss.y,1,min(1.8,amount/20)))
    if state['hp']>0:return
    if state['kind']=='gokbin' and state['phase']==1:
        state['phase']=2;state['max_hp']=round(230*(1.45 if state['coop'] else 1))*4;state['hp']=state['max_hp']
        state['pattern']='';state['telegraphs']=[]
        boss.skin='gokbin_curse';boss.x=arena.left+arena.width/2;boss.y=arena.top+140;boss.vx=boss.vy=0
        boss.injury_turns=0;boss.defense='';boss.brickwall=False;boss.alive=True
        arena.events.append(Event('boss_phase',boss.x,boss.y,1,1.8))
    else:
        state['defeated']=True;boss.alive=False;boss.vx=boss.vy=0
        arena.events.append(Event('boss_defeat',boss.x,boss.y,1,1.8))

def contact(arena,boss,other,speed):
    if not boss.boss or other.team==boss.team or speed<80:return
    key=other.id
    if arena.elapsed-arena.boss_hits.get(key,-100)<.22:return
    arena.boss_hits[key]=arena.elapsed
    power=arena.mult_for(other,'power')
    from stats import power_transfer_multiplier
    power*=power_transfer_multiplier(arena.stats_for(other),other.injury_turns>0)
    if other.tiger:power*=1.8
    if other.bull:power*=1.5
    hurt(arena,min(42,max(4,speed/45*power)))

def plan(arena):
    state=arena.boss_state;boss=next(e for e in arena.living(1) if e.boss)
    targets=arena.living(0)
    if not targets:return
    state['action']+=1;index=(state['action']-1)%3
    target=targets[(state['action']-1)%len(targets)];state['target']=[target.x,target.y]
    kind=state['kind'];phase=state['phase']
    if kind=='warden':pattern=('charge','slam','charge')[index]
    elif kind=='tempest':pattern=('crosswind','vortex','crosswind')[index]
    elif phase==1:pattern=('charge','curse','vortex')[index]
    else:pattern=('red_curse','red_slam','charge')[index]
    state['pattern']=pattern
    state['telegraphs']=[{'kind':pattern,'x':target.x,'y':target.y,'boss_x':boss.x,'boss_y':boss.y}]

def fire(arena):
    state=arena.boss_state;boss=next((e for e in arena.living(1) if e.boss),None)
    if not boss:return
    pattern=state['pattern'];arena.attacking_team=1;arena.active_shooter_id=boss.id
    arena.events.append(Event('boss_attack',boss.x,boss.y,1,1.5))
    if pattern=='charge':
        dx,dy=state['target'][0]-boss.x,state['target'][1]-boss.y;d=max(1,math.hypot(dx,dy))
        arena.shoot(boss.id,dx/d*155,dy/d*155)
    else:
        for e in arena.living(0):
            if e.brickwall or arena.invulnerable(e):continue
            dx,dy=e.x-boss.x,e.y-boss.y;d=max(1,math.hypot(dx,dy));speed=0
            if pattern in ('slam','red_slam'):
                radius=245 if pattern=='slam' else 430
                if d<radius+e.r:speed=850 if pattern=='slam' else 1150
            elif pattern=='vortex':speed=-480
            elif pattern=='crosswind':
                tx,ty=state['target']
                if abs(e.x-tx)<70:dx,dy,d=0,1,1;speed=900
                elif abs(e.y-ty)<70:dx,dy,d=1 if e.x>boss.x else -1,0,1;speed=900
            elif pattern in ('curse','red_curse'):
                angle=arena.rng.uniform(0,math.tau);dx,dy,d=math.cos(angle),math.sin(angle),1
                speed=MAX_PULL*BASE_POWER_SCALE*(.65 if pattern=='curse' else .95)
            e.vx+=dx/d*speed/max(.4,arena.toughness(e));e.vy+=dy/d*speed/max(.4,arena.toughness(e))
        if pattern=='red_slam':
            for box in arena.obstacles:
                if box.material=='wood':box.alive=False
    state['telegraphs']=[]

def grant(profile,state):
    """Called only by the authoritative completed match, never by shop draws."""
    if not state or not state['defeated']:return False
    clears=profile.setdefault('boss_clears',{})
    clears[state['kind']]=max(clears.get(state['kind'],0),state['phase'])
    if state['kind']=='gokbin' and state['phase']==2 and 'gokbin_curse' not in profile['owned_skins']:
        profile['owned_skins'].append('gokbin_curse');return True
    return False

def draw(game):
    import pygame
    a=game.arena;s=a.boss_state
    if not s:return
    ko=game.profile['settings']['language']=='ko';name=BOSSES[s['kind']][0 if ko else 1]
    rect=pygame.Rect(405,88,470,24);pygame.draw.rect(game.screen,(42,23,54),rect,border_radius=10)
    fill=rect.copy();fill.w=round(rect.w*max(0,s['hp'])/s['max_hp'])
    if fill.w:pygame.draw.rect(game.screen,(255,45,80) if s['phase']==2 else (235,170,40),fill,border_radius=10)
    game.label(f"{name} · P{s['phase']} · {math.ceil(s['hp'])}/{s['max_hp']}",640,99,'small',(255,255,255),'center')
    if game.state not in ('aim','reveal','boss_windup'):return
    for t in s['telegraphs']:
        c=(255,70,85);pos=(round(t['boss_x']),round(t['boss_y']));target=(round(t['x']),round(t['y']))
        if t['kind']=='charge':pygame.draw.line(game.screen,c,pos,target,7);pygame.draw.circle(game.screen,c,target,40,3)
        elif t['kind']=='crosswind':
            pygame.draw.rect(game.screen,c,(target[0]-70,a.top,140,a.height),3)
            pygame.draw.rect(game.screen,c,(a.left,target[1]-70,a.width,140),3)
        elif t['kind'] in ('slam','red_slam'):pygame.draw.circle(game.screen,c,pos,245 if t['kind']=='slam' else 430,4)
        else:pygame.draw.rect(game.screen,c,(a.left,a.top,a.width,a.height),4)
    if s['telegraphs']:
        names={'charge':('돌진 예고','CHARGE'),'slam':('충격파 예고','SHOCKWAVE'),'red_slam':('폭주 충격파','ENRAGED WAVE'),
               'crosswind':('십자 돌풍 예고','CROSSWIND'),'vortex':('흡인 예고','VORTEX'),'curse':('저주 예고','CURSE'),'red_curse':('폭주 저주 예고','ENRAGED CURSE')}
        game.label(names.get(s['pattern'],('',''))[0 if ko else 1],640,780,'heading',(255,90,110),'center')
