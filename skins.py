"""Cosmetic-only marble skins. Team ownership is always indicated by an outer ring."""
from dataclasses import dataclass
import math
import pygame

@dataclass(frozen=True)
class Skin:
    ko:str; en:str; color:tuple; pattern:str; rarity:str
    image:str=""
    boss_reward:bool=False

SKINS={
 'classic':Skin('기본','Classic',(75,175,255),'solid','Common'),
 'ruby':Skin('루비','Ruby',(238,47,91),'solid','Common'),
 'sunset':Skin('선셋','Sunset',(255,134,35),'stripe','Common'),
 'lemon':Skin('레몬','Lemon',(250,220,40),'solid','Common'),
 'emerald':Skin('에메랄드','Emerald',(30,205,116),'stripe','Rare'),
 'ocean':Skin('오션','Ocean',(25,145,245),'wave','Rare'),
 'violet':Skin('바이올렛','Violet',(155,74,235),'dots','Rare'),
 'rainbow':Skin('레인보우','Rainbow',(255,100,160),'rainbow','Epic'),
 'galaxy':Skin('갤럭시','Galaxy',(64,32,119),'stars','Epic'),
 'tiger_skin':Skin('타이거','Tiger Stripes',(245,158,25),'tiger','Epic'),
 'gold':Skin('황금','Golden Crown',(255,198,46),'stars','Legendary'),
}

for key,ko,en,rarity in (
 ('cheeky','치키','Cheeky','Common'),('verity','베리티','Verity','Common'),
 ('gubby','구비','Gubby','Rare'),('man_face','남자 얼굴','Man Face','Rare'),
 ('gokbin','노곡빈','Gokbin','Epic'),('gokbin_curse','노곡빈의 저주','Gokbin Curse','Legendary')):
    SKINS[key]=Skin(ko,en,(255,255,255),'photo',rarity,key+'.png',key=='gokbin_curse')
_IMAGES={}
_TILES={}

def photo(key,size):
    from pathlib import Path
    if key not in _IMAGES:
        try:
            original=pygame.image.load(str(Path(__file__).resolve().parent/'assets/skins'/SKINS[key].image))
            bounds=original.get_bounding_rect(min_alpha=10)
            _IMAGES[key]=original.subsurface(bounds).copy() if bounds.w and bounds.h else original
        except (OSError,pygame.error):_IMAGES[key]=None
    original=_IMAGES[key]
    if original is None:return None
    cache=(key,size)
    if cache not in _TILES:
        scale=size/max(original.get_size())
        _TILES[cache]=pygame.transform.smoothscale(original,(max(1,round(original.get_width()*scale)),max(1,round(original.get_height()*scale))))
        if len(_TILES)>160:_TILES.pop(next(iter(_TILES)))
    return _TILES[cache]

def paint(surface,rect,key,team=0):
    key=key if key in SKINS else 'classic';skin=SKINS[key]
    r=max(3,int(min(rect.width,rect.height)/2));size=2*r
    if skin.image:
        tile=photo(key,size)
        if tile is not None:
            surface.blit(tile,tile.get_rect(center=rect.center))
            pygame.draw.circle(surface,(64,174,255) if team==0 else (255,75,99),rect.center,r,2)
            return
    tile=pygame.Surface((size,size),pygame.SRCALPHA)
    color=((52,161,255) if team==0 else (240,65,85)) if key=='classic' else skin.color
    pygame.draw.circle(tile,color,(r,r),r)
    if skin.pattern=='rainbow':
        colors=[(245,50,80),(255,140,30),(255,215,35),(44,205,100),(30,155,245),(95,60,220),(190,65,220)]
        for i,c in enumerate(colors):pygame.draw.rect(tile,c,(i*size/7,0,size/7+1,size))
    elif skin.pattern in ('stripe','tiger','wave'):
        for y in range(-size,size*2,max(5,r//2)):
            pygame.draw.line(tile,(20,35,65,210) if skin.pattern=='tiger' else (255,255,255,130),(0,y),(size,y-r),max(2,r//5))
    elif skin.pattern in ('dots','stars'):
        for i in range(9):
            x=int((i*17+7)%size);y=int((i*29+11)%size)
            pygame.draw.circle(tile,(255,244,180),(x,y),max(1,r//9))
    mask=pygame.Surface((size,size),pygame.SRCALPHA);pygame.draw.circle(mask,(255,255,255,255),(r,r),r)
    tile.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    pygame.draw.circle(tile,(255,255,255,140),(int(r*.7),int(r*.65)),max(2,r//4))
    surface.blit(tile,(rect.centerx-r,rect.centery-r))
    pygame.draw.circle(surface,(64,174,255) if team==0 else (255,75,99),rect.center,r,3)
