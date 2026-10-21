"""Render-only impact camera; never changes world or input coordinates."""
import math
import pygame

class ImpactFX:
    def __init__(self):
        self.rings=[]; self.shake=0.; self.freeze=0.; self.zoom=0.; self.flash=0.
    def emit(self,event):
        strength=max(.1,event.strength)
        special=event.kind in ('cola_explosion','clutch','last_resort')
        if special:strength=1.4
        if event.kind in ('hit','brickwall_hit','chain_hit','cola_explosion','clutch','last_resort','wood_break','brickwall_on'):
            self.rings.append([event.x,event.y,0.,strength,event.kind])
            self.rings=self.rings[-32:]
            if strength>.65:
                self.shake=max(self.shake,.18*strength)
                self.freeze=max(self.freeze,.025*strength)
                self.zoom=max(self.zoom,.012*strength)
                self.flash=.07
    def update(self,dt):
        self.shake=max(0,self.shake-dt); self.freeze=max(0,self.freeze-dt)
        self.zoom=max(0,self.zoom-dt*.08);self.flash=max(0,self.flash-dt)
        for ring in self.rings:ring[2]+=dt
        self.rings=[r for r in self.rings if r[2]<.6]
    def draw(self,surface):
        for x,y,age,strength,kind in self.rings:
            color=(255,214,72) if kind in ('clutch','chain_hit') else (255,255,255)
            radius=max(1,int(12+age*190*strength))
            pygame.draw.circle(surface,color,(round(x),round(y)),radius,max(1,int(6*(1-age/.6))))
            if age<.08:pygame.draw.circle(surface,(255,245,185),(round(x),round(y)),int(9+strength*6))
    def camera(self,surface,rect,frame):
        if self.shake<=0 and self.zoom<=0:return
        board=surface.subsurface(rect).copy()
        if self.zoom:
            board=pygame.transform.smoothscale(board,(int(rect.w*(1+self.zoom)),int(rect.h*(1+self.zoom))))
        offset=(int(math.sin(frame*2.7)*self.shake*24),int(math.cos(frame*3.1)*self.shake*20))
        old=surface.get_clip();surface.set_clip(rect)
        surface.blit(board,(rect.x+offset[0]-(board.get_width()-rect.w)//2,rect.y+offset[1]-(board.get_height()-rect.h)//2))
        surface.set_clip(old)
