"""Observable, bounded-channel audio with generated fallbacks and music fades."""
from pathlib import Path
import array
import logging
import math
import pygame

LOG=logging.getLogger('marble.audio')
SFX = {
 'click':('ui_click','버튼 클릭'), 'hover':('ui_hover','버튼에 마우스 진입'),
 'menu':('menu_enter','메인 메뉴 진입'), 'transition':('menu_transition','화면 전환'),
 'shop':('shop_open','상점 열기'), 'draw_start':('gacha_start','뽑기 시작'),
 'draw_result':('gacha_result','뽑기 결과'), 'rare':('gacha_rare','Epic/Legendary 획득'),
 'equip':('inventory_equip','장착/해제'), 'passive':('passive_activate','조건부 패시브 발동'),
 'clutch':('clutch_activate','클러치 발동'), 'match':('match_start','경기 시작'),
 'victory':('victory','승리'), 'defeat':('defeat','패배/무승부'),
 'clack':('marble_hit','구슬 충돌'), 'shoot':('marble_flick','일반 발사'),
 'drop':('marble_fall','장외 탈락'), 'breaker':('wood_break','나무 파괴'),
 'injury':('injury','부상'), 'brickwall_on':('brickwall_activate','콘크리트 굳기'),
 'brickwall_hit':('brickwall_hit','콘크리트 충돌'), 'tiger':('tiger_shot','타이거 발사'),
 'tiger_wind':('tiger_wind','풍압'), 'chain':('chain_start','체인 발사'),
 'chain_hit':('chain_hit','연속 적중'), 'chain_dash':('chain_dash','체인 재가속'),
 'cola_charge':('cola_charge','콜라 충전/발사'), 'cola_explosion':('cola_explosion','콜라 폭발'),
 'lock':('turn_lock','준비 확정'), 'reveal':('reveal','동시 공개'),
 'countdown':('countdown','준비 시간 마지막 5초'),
}
MUSIC={k:k+'.mp3' for k in ('main_menu','shop','inventory','match')}

class SoundBox:
    FILES={k:v[0]+'.mp3' for k,v in SFX.items()}
    def __init__(self, root=None):
        self.root=Path(root) if root else Path(__file__).resolve().parent/'assets'
        self.muted=False; self.sfx_volume=.7; self.music_volume=.45
        self.samples={}; self.fallback={}; self.diagnostics={}; self.play_counts={}
        self.current_music=None; self.pending_music=None; self.fade_left=0
        if pygame.mixer.get_init() is None:
            try: pygame.mixer.init(44100,-16,2,512)
            except pygame.error as exc: LOG.error('Audio device unavailable: %s',exc)
        if pygame.mixer.get_init():
            pygame.mixer.set_num_channels(32)
            pygame.mixer.set_reserved(4)
        for i,(name,filename) in enumerate(self.FILES.items()):
            path=self.root/'sfx'/filename
            try:
                if not path.is_file(): raise FileNotFoundError(filename)
                sound=pygame.mixer.Sound(str(path))
                if sound.get_length()<=0: raise ValueError('empty decoded audio')
                self.samples[name]=sound
                self.diagnostics[name]=f'decoded {sound.get_length():.3f}s'
            except (pygame.error,OSError,ValueError) as exc:
                self.samples[name]=None
                self.diagnostics[name]=f'fallback: {exc}'
                LOG.warning('%s: %s',path,self.diagnostics[name])
            self.fallback[name]=self._tone(160+i*24)
        LOG.info('Mixer=%s; channels=32, reserved=4; SFX volume=%s',pygame.mixer.get_init(),self.sfx_volume)

    def _tone(self,freq):
        init=pygame.mixer.get_init()
        if not init:return None
        sr,fmt,ch=init
        data=array.array('h')
        for i in range(int(sr*.16)):
            v=int(8000*math.sin(2*math.pi*freq*i/sr)*math.exp(-24*i/sr))
            data.extend([v]*ch)
        return pygame.mixer.Sound(buffer=data.tobytes())

    def play(self,name):
        self.play_counts[name]=self.play_counts.get(name,0)+1
        if self.muted or self.sfx_volume<=0 or not pygame.mixer.get_init(): return None
        sound=self.samples.get(name) or self.fallback.get(name)
        if sound is None:
            LOG.error('No sample or fallback: %s',name);return None
        reserved={'cola_charge':0,'cola_explosion':1,'clutch':2,'victory':3,'defeat':3}
        channel=pygame.mixer.Channel(reserved[name]) if name in reserved else next((pygame.mixer.Channel(i) for i in range(4,32) if not pygame.mixer.Channel(i).get_busy()),None)
        if channel is None:
            LOG.warning('SFX channels exhausted: %s; replacing oldest nonreserved channel',name)
            # Never steal a reserved charge/explosion/result channel.
            channel=pygame.mixer.Channel(4)
        channel.set_volume(self.sfx_volume)
        channel.play(sound)
        LOG.debug('play %s volume=%.2f busy=%s',name,self.sfx_volume,channel.get_busy())
        return channel

    def music(self,scene):
        if scene==self.current_music:return
        self.current_music=scene; self.pending_music=scene; self.fade_left=.3
        if pygame.mixer.get_init(): pygame.mixer.music.fadeout(300)

    def update(self,dt):
        if not pygame.mixer.get_init():return
        pygame.mixer.music.set_volume(0 if self.muted else self.music_volume)
        if self.muted:
            for i in range(pygame.mixer.get_num_channels()): pygame.mixer.Channel(i).set_volume(0)
        else:
            for i in range(pygame.mixer.get_num_channels()): pygame.mixer.Channel(i).set_volume(self.sfx_volume)
        if self.pending_music is not None:
            self.fade_left-=dt
            if self.fade_left<=0:
                scene=self.pending_music; self.pending_music=None
                path=self.root/'music'/MUSIC[scene]
                if path.is_file():
                    try:
                        pygame.mixer.music.load(str(path)); pygame.mixer.music.play(-1,fade_ms=500)
                    except (pygame.error,OSError) as exc:LOG.warning('BGM %s: %s',path,exc)
                else: LOG.info('Optional BGM missing: %s',path)
