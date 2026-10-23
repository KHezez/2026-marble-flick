"""Cached PNG sprite atlases, rendered as separate per-item artwork."""
from pathlib import Path
import pygame
from abilities import SKILLS
from perks import PERKS
ROOT=Path(__file__).resolve().parent/'assets'
SKILL_COLORS=[(140,170,195),(255,137,25),(194,85,255),(255,55,85),(255,85,40),(40,235,220),(182,70,240),(60,160,255)]

class Assets:
    def __init__(self):self.images={};self.scaled={}
    def image(self,relative):
        if relative not in self.images:
            p=ROOT/relative
            try:self.images[relative]=pygame.image.load(str(p)).convert_alpha() if p.is_file() else None
            except (pygame.error,OSError):self.images[relative]=None
        return self.images[relative]
    def sprite(self,file,index,cols,rows,size):
        cache=(file,index,cols,rows,tuple(size))
        if cache not in self.scaled:
            src=self.image(file)
            if src is None:return None
            x,y=index%cols,index//cols
            rect=pygame.Rect(x*src.get_width()//cols,y*src.get_height()//rows,src.get_width()//cols,src.get_height()//rows)
            self.scaled[cache]=pygame.transform.smoothscale(src.subsurface(rect),size)
        return self.scaled[cache]
    def icon(self,surface,key,kind,rect):
        rect=pygame.Rect(rect)
        if kind=='skin':
            from skins import paint
            paint(surface,rect,key);return
        keys=list(SKILLS if kind=='skill' else PERKS)
        if key not in keys:return
        i=keys.index(key);prefix='skills' if kind=='skill' else 'perks'
        tile=self.sprite(f'gui/{prefix}_{chr(97+i//4)}.png',i%4,2,2,rect.size)
        if tile:surface.blit(tile,rect)
        else:pygame.draw.rect(surface,SKILL_COLORS[i%8],rect,border_radius=14)
    def frame(self,surface,skill,rect,tick=0):
        rect=pygame.Rect(rect);i=list(SKILLS).index(skill);color=SKILL_COLORS[i]
        frame=self.sprite('gui/skill_frames.png',i,4,2,rect.size)
        # A strong base outline remains visible even with a missing PNG.
        pygame.draw.rect(surface,color,rect,4,border_radius=5)
        if frame:surface.blit(frame,rect)
        # Each identity retains a distinct geometric silhouette at tiny sizes.
        if skill=='brickwall':
            for x in range(rect.left,rect.right,18):pygame.draw.rect(surface,(185,191,205),(x,rect.top-3,12,8))
        elif skill=='tiger':
            for x in range(rect.left+5,rect.right,14):
                pygame.draw.polygon(surface,(255,194,25),[(x,rect.top),(x+5,rect.top-7-(tick//4%3)),(x+10,rect.top)])
        elif skill in ('chain','infinity'):
            for x in range(rect.left+8,rect.right,20):pygame.draw.circle(surface,color,(x,rect.top),5,2)
        elif skill=='bull':
            pygame.draw.polygon(surface,color,[(rect.left,rect.top+25),(rect.left-9,rect.top-9),(rect.left+12,rect.top)])
            pygame.draw.polygon(surface,color,[(rect.right,rect.top+25),(rect.right+9,rect.top-9),(rect.right-12,rect.top)])
    def panel(self,surface,rect,index=0):
        rect=pygame.Rect(rect);src=self.image('gui/gui_panels.png')
        if src:
            # Buttons are centered inside equal atlas cells with ~8% margins.
            cellw,cellh=src.get_width()//2,src.get_height()//2
            crop=pygame.Rect((index%2)*cellw+int(cellw*.08),(index//2)*cellh+int(cellh*.08),int(cellw*.84),int(cellh*.84))
            cache=('panel',index,rect.size)
            if cache not in self.scaled:self.scaled[cache]=pygame.transform.smoothscale(src.subsurface(crop),rect.size)
            surface.blit(self.scaled[cache],rect)
        else:pygame.draw.rect(surface,[(30,110,230),(20,158,95),(146,48,202),(210,121,16)][index%4],rect,border_radius=13)
