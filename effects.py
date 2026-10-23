"""Bounded sprite bursts and optional camera/window motion; world coordinates stay fixed."""
import math
import logging
import sys
import pygame
from gui_assets import Assets

BURSTS={'hit':0,'brickwall_hit':0,'tiger_wind':1,'bull_impact':2,'bull_counter':2,
        'ankle_dodge':3,'curse_launch':4,'infinity_ready':5,'infinity_stop':5,
        'cola_explosion':6,'clutch':7,'last_resort':7,'wood_break':0,'chain_hit':1,'brickwall_on':0}

BURSTS.update(boss_hit=2,boss_attack=6,boss_phase=4,boss_defeat=7)

class ImpactFX:
    def __init__(self):
        self.rings=[];self.shake=0.;self.freeze=0.;self.zoom=0.;self.flash=0.
        self.settings={};self.allow_window_motion=True;self.assets=Assets();self.window=None;self.window_origin=None;self.window_failed=False
    def configure(self,settings):
        self.settings=settings
        if not settings.get('window_shake',False):self.restore_window()
    def emit(self,event):
        if event.kind not in BURSTS:return
        strength=max(.1,min(2,event.strength))
        if event.kind in ('cola_explosion','clutch','last_resort','bull_impact','curse_launch'):strength=1.4
        self.rings.append([event.x,event.y,0.,strength,event.kind]);self.rings=self.rings[-32:]
        if strength>.65:
            self.shake=max(self.shake,.18*strength);self.freeze=max(self.freeze,.025*strength)
            self.zoom=max(self.zoom,.012*strength);self.flash=.07
    def restore_window(self):
        if self.window is not None and self.window_origin is not None:
            try:self.window.position=self.window_origin
            except (pygame.error,AttributeError,RuntimeError):pass
        self.window_origin=None
    def move_window(self):
        if not self.allow_window_motion or not self.settings.get('window_shake',False) or self.shake<=0:
            self.restore_window();return
        # SDL exposes the native window without changing game/world coordinates.
        if sys.platform!='win32' or self.window_failed:return
        try:
            if self.window is None:
                from pygame._sdl2.video import Window
                self.window=Window.from_display_module()
            if self.window_origin is None:self.window_origin=tuple(self.window.position)
            tick=pygame.time.get_ticks();amount=min(8,round(self.shake*28))
            self.window.position=(self.window_origin[0]+round(math.sin(tick*.05)*amount),self.window_origin[1]+round(math.cos(tick*.06)*amount))
        except (pygame.error,ImportError,AttributeError,RuntimeError) as exc:
            logging.warning('Experimental window shake unavailable: %s',exc);self.restore_window();self.window_failed=True
    def update(self,dt):
        self.shake=max(0,self.shake-dt);self.freeze=max(0,self.freeze-dt)
        self.zoom=max(0,self.zoom-dt*.08);self.flash=max(0,self.flash-dt)
        for ring in self.rings:ring[2]+=dt
        self.rings=[r for r in self.rings if r[2]<.6]
        self.move_window()
    def draw(self,surface):
        for x,y,age,strength,kind in self.rings:
            color=(255,214,72) if kind in ('clutch','chain_hit') else (135,220,255)
            radius=max(1,int(12+age*190*strength))
            pygame.draw.circle(surface,color,(round(x),round(y)),radius,max(1,int(6*(1-age/.6))))
            # Quantized sizes keep the sprite cache bounded over long matches.
            size=min(288,max(48,int((60+age*200)*strength)//16*16))
            sprite=self.assets.sprite('vfx/vfx_burst.png',BURSTS[kind],4,2,(size,size))
            if sprite and self.settings.get('flash',True):
                faded=sprite.copy();faded.set_alpha(int(255*(1-age/.6)));surface.blit(faded,(round(x-size/2),round(y-size/2)))
    def camera(self,surface,rect,frame):
        if not self.settings.get('screen_shake',True):return
        if self.shake<=0 and self.zoom<=0:return
        board=surface.subsurface(rect).copy()
        if self.zoom:board=pygame.transform.smoothscale(board,(int(rect.w*(1+self.zoom)),int(rect.h*(1+self.zoom))))
        offset=(int(math.sin(frame*2.7)*self.shake*24),int(math.cos(frame*3.1)*self.shake*20))
        old=surface.get_clip();surface.set_clip(rect)
        surface.blit(board,(rect.x+offset[0]-(board.get_width()-rect.w)//2,rect.y+offset[1]-(board.get_height()-rect.h)//2))
        surface.set_clip(old)
