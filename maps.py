"""Six layouts with real steel boundaries and mixed surface patches."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Zone:
    x:float; y:float; w:float; h:float; floor:str

MAPS={
 'classic':('클래식','Classic','normal','match'),
 'desert':('사막 유적','Desert Ruins','desert','battle_desert'),
 'jungle':('정글 습지','Jungle Marsh','jungle','battle_jungle'),
 'barricade':('돌파 작전','Breakthrough','desert','battle_barricade'),
 'steel_ring':('강철 링','Steel Ring','normal','battle_steel'),
 'frozen_delta':('빙하 삼각주','Frozen Delta','ice','battle_ice'),
}

def apply_map(arena,key):
    from physics import Obstacle
    if key not in MAPS:raise ValueError('Unknown map')
    arena.map_key=key;arena.zones=[];arena.boundary_walls=False;arena.walls_open=False
    if key=='classic':return
    l,t,w,h=arena.left,arena.top,arena.width,arena.height
    mid=t+h/2;cx=l+w/2
    boxes=[]
    if key=='desert':
        boxes=[(cx-150,mid-50,40,100,'steel'),(cx+110,mid-50,40,100,'steel'),(cx-55,mid-22,110,44,'wood')]
        arena.zones=[Zone(cx-110,mid+60,220,85,'mud')]
    elif key=='jungle':
        boxes=[(cx-135,mid-25,80,50,'wood'),(cx+55,mid-25,80,50,'wood')]
        arena.zones=[Zone(l+25,mid-145,180,105,'mud'),Zone(cx+35,mid+50,200,95,'ice')]
    elif key=='barricade':
        # Continuous wall spans the arena: it must be broken to cross the centre.
        boxes=[(l+i*w/8,mid-22,w/8+.1,44,'wood') for i in range(8)]
        arena.zones=[Zone(l+85,mid+55,w-170,70,'ice'),Zone(l+85,mid-125,w-170,70,'mud')]
    elif key=='steel_ring':
        arena.boundary_walls=True
        boxes=[(cx-120,mid-45,35,90,'steel'),(cx+85,mid-45,35,90,'steel')]
        arena.zones=[Zone(cx-65,mid-120,130,240,'ice')]
    elif key=='frozen_delta':
        boxes=[(cx-25,mid-35,50,70,'steel'),(cx-150,mid-20,65,40,'wood'),(cx+85,mid-20,65,40,'wood')]
        arena.zones=[Zone(l+20,mid-170,w-40,100,'ice'),Zone(l+20,mid+70,w-40,100,'ice'),Zone(cx-70,mid+15,140,50,'mud')]
    arena.floor='normal'
    arena.obstacles=[Obstacle(i,*b,hp=2.2 if key=='barricade' else 1.6) for i,b in enumerate(boxes)]

def music_for(arena,clutch=False):
    return 'clutch' if clutch else MAPS.get(arena.map_key,MAPS['classic'])[3]
