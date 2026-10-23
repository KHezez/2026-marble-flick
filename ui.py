"""v0.7 large, localized, illustrated inventory and settings screens."""
import math
from pathlib import Path
import pygame
from perks import PERKS,validate
from abilities import SKILLS,SKILL_NAMES,COOLDOWNS
from stats import STAT_CAPS
from inventory import active,equip_slot,allocate
from economy import draw,PRICES,RATES,SKILL_RARITIES
from skins import SKINS
from maps import MAPS
from localization import tr,item_name,description,STAT_KO
from gui_assets import Assets,SKILL_COLORS
INK=(238,245,255);BLUE=(48,157,255);WHITE=(255,255,255);GOLD=(255,209,45)
BG=(14,19,43);PANEL=(24,33,65);LINE=(67,89,142)
RARITY={'Common':(175,193,220),'Rare':(55,175,255),'Epic':(214,107,255),'Legendary':(255,193,40)}

class MenuUI:
    def __init__(self,game):
        self.g=game;self.page='home';self.widgets=[];self.hover=None;self.selected=None
        self.draw_time=0.;self.result=None;self.notice='';self.themes={}
        self.inventory_team=0;self.tab='skill';self.slot=0;self.assets=Assets()
    @property
    def lang(self):return self.g.profile['settings']['language']
    def say(self,ko,en):return ko if self.lang=='ko' else en
    def background(self,key):
        g=self.g;g.screen.fill(BG)
        # Retain existing menu art as a restrained background under strong panels.
        if key not in self.themes:
            image=self.assets.image('themes/'+key+'.png')
            self.themes[key]=pygame.transform.smoothscale(image,(1280,900)) if image else None
        if self.themes[key]:
            g.screen.blit(self.themes[key],(0,0));overlay=pygame.Surface((1280,900),pygame.SRCALPHA);overlay.fill((6,12,35,225));g.screen.blit(overlay,(0,0))
        for i,color in enumerate(SKILL_COLORS):pygame.draw.rect(g.screen,color,(i*160,0,160,5))
    def box(self,rect):
        pygame.draw.rect(self.g.screen,PANEL,rect,border_radius=16);pygame.draw.rect(self.g.screen,LINE,rect,2,border_radius=16)
    def button(self,rect,text,action,value=None,selected=False,disabled=False,color=0):
        g=self.g;rect=pygame.Rect(rect);hover=rect.collidepoint(g.mouse)
        shown=rect.inflate(-4,-4) if hover and pygame.mouse.get_pressed()[0] else rect.move(0,-2 if hover else 0)
        self.assets.panel(g.screen,shown,3 if selected else color)
        if disabled:
            fog=pygame.Surface(shown.size,pygame.SRCALPHA);fog.fill((8,15,35,175));g.screen.blit(fog,shown)
        if selected:pygame.draw.rect(g.screen,GOLD,shown,3,border_radius=10)
        g.label(text,*shown.center,'body_b',WHITE,'center')
        if not disabled:self.widgets.append((rect,action,value))
    def go(self,page):
        self.page=page;self.notice='';self.selected=None
        self.g.sound.play('shop' if page=='shop' else 'menu' if page=='home' else 'transition')
        self.g.sound.music({'home':'main_menu','setup':'main_menu','shop':'shop','inventory':'inventory','settings':'settings'}.get(page,'main_menu'))
    def persist(self):
        try:self.g.store.save(self.g.profile)
        except OSError:self.notice=self.say('저장하지 못했습니다. 게임 폴더 쓰기 권한을 확인하세요.','Save failed. Check folder write permission.')
    def profile_for_edit(self):
        if self.inventory_team==0:return self.g.profile
        p=dict(self.g.profile);p['loadouts']={'red':self.g.red_loadout};p['active_loadout']='red';return p
    def perform(self,action,value):
        g=self.g
        try:
            if action=='page':self.go(value)
            elif action in ('count','floor','obstacles','cpu_mode','map_key'):
                if action=='count' and value==1:
                    for load in (active(g.profile),g.red_loadout):validate(load['perks'],1)
                setattr(g,action,value)
            elif action=='start':g.start_match()
            elif action=='item':self.selected=value
            elif action=='tab':self.tab=value;self.slot=0;self.selected=None
            elif action=='slot':self.tab,self.slot=value;self.selected=None
            elif action=='equip':
                equip_slot(self.profile_for_edit(),*value,self.slot,count=g.count);g.sound.play('equip');self.persist()
            elif action=='unequip':
                load=active(self.profile_for_edit());field='skills' if self.tab=='skill' else 'perks'
                if self.slot<len(load[field]):load[field].pop(self.slot)
                self.persist()
            elif action=='stat':allocate(self.profile_for_edit(),*value);self.persist()
            elif action=='team':self.inventory_team=value;self.selected=None
            elif action=='draw' and self.draw_time<=0:
                self.result=draw(g.profile,value);self.draw_time=1.4;g.sound.play('draw_start');self.persist()
            elif action=='volume':
                key,delta=value;field='sfx_volume' if key=='sfx' else 'music_volume'
                setattr(g.sound,field,max(0,min(1,getattr(g.sound,field)+delta)))
                g.profile['audio'][key]=getattr(g.sound,field);self.persist()
            elif action=='mute':g.sound.muted=not g.sound.muted;g.profile['audio']['muted']=g.sound.muted;self.persist()
            elif action=='language':g.profile['settings']['language']=value;self.persist()
            elif action=='option':
                g.profile['settings'][value]=not g.profile['settings'][value];self.persist()
                if value=='window_shake' and not g.profile['settings'][value]:g.fx.restore_window()
            elif action=='resume':
                g.state=g._settings_return_state;g._settings_return_state=None;g.sync_music()
        except ValueError as exc:self.notice=str(exc)
    def event(self,event):
        if event.type==pygame.KEYDOWN and event.key==pygame.K_F10:self.go('settings');return True
        if event.type==pygame.KEYDOWN and event.key==pygame.K_m:self.perform('mute',None);return True
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
            if getattr(self.g,'_settings_return_state',None):self.perform('resume',None)
            else:self.go('home')
            return True
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            for rect,action,value in self.widgets:
                if rect.collidepoint(event.pos):self.g.sound.play('click');self.perform(action,value);break
        return True
    def update(self,dt):
        if self.draw_time>0:
            self.draw_time=max(0,self.draw_time-dt)
            if self.draw_time==0:self.g.sound.play('skin_draw' if self.result['kind']=='skin' else 'rare' if self.result['rarity'] in ('Epic','Legendary') else 'draw_result')
        hit=next((str((a,v)) for r,a,v in self.widgets if r.collidepoint(self.g.mouse)),None)
        if hit!=self.hover and hit:self.g.sound.play('hover')
        self.hover=hit
    def render(self):
        g=self.g;self.widgets=[];self.background({'shop':'shop','inventory':'inventory'}.get(self.page,'main_menu'))
        g.label('MARBLE FLICK',35,22,'title',WHITE);g.label('v0.7',360,35,'body',GOLD)
        self.button((990,20,250,58),f"{g.profile['coins']:,} Coins",'noop',selected=True)
        if self.page!='home':
            self.button((35,105,140,50),'BACK','resume' if getattr(g,'_settings_return_state',None) else 'page',None if getattr(g,'_settings_return_state',None) else 'home')
        {'home':self.home,'setup':self.setup,'shop':self.shop,'inventory':self.inventory,'settings':self.settings}[self.page]()
        if self.notice:
            self.box((35,820,1210,42));g.label(self.notice,50,827,'body',GOLD)
        g.label('P: +1000 Coins',35,870,'small',GOLD)
        g.label(self.say('F10 설정 · M 음소거','F10 Settings · M Mute'),1235,870,'small',INK,'topright')
    def home(self):
        g=self.g;g.label(self.say('한 방에 뒤집어라!','MAKE YOUR MOVE!'),640,170,'hero',WHITE,'center')
        for i,key in enumerate(('tiger','bull','infinity')):
            rect=pygame.Rect(130+i*390,260,240,240);self.assets.icon(g.screen,key,'skill',rect);self.assets.frame(g.screen,key,rect,g.frame)
        for i,(text,page) in enumerate((('START','setup'),('SHOP','shop'),('INVENTORY','inventory'),('SETTINGS','settings'))):
            self.button((150+i*250,600,230,86),text,'page',page,color=i%4)
        g.label(self.say('스킬 8종 · 패시브 12종 · 다양한 전장','8 skills · 12 passives · New battlegrounds'),640,750,'heading',INK,'center')
    def setup(self):
        g=self.g;g.label(self.say('경기 설정','MATCH SETUP'),640,120,'title',WHITE,'center')
        groups=[('TEAM SIZE','count',(1,4,5,6,7,8,9,10)),('OPPONENT','cpu_mode',('off','easy','normal','hard'))]
        for row,(title,action,values) in enumerate(groups):
            y=200+row*90;g.label(title,45,y+15,'heading',INK)
            for i,value in enumerate(values):
                width=100 if len(values)>4 else 210
                self.button((320+i*(width+12),y,width,55),'LOCAL 2P' if value=='off' else str(value).upper(),action,value,getattr(g,action)==value)
        g.label('MAP',45,398,'heading',INK)
        for i,(key,info) in enumerate(MAPS.items()):
            self.button((320+i%3*290,385+i//3*70,270,55),info[0 if self.lang=='ko' else 1],'map_key',key,g.map_key==key,color=i%4)
        g.label('SURFACE',45,555,'heading',INK)
        for i,f in enumerate(('normal','ice','mud')):self.button((320+i*190,540,175,50),f.upper(),'floor',f,g.floor==f,disabled=g.map_key!='classic')
        g.label('OBSTACLES',45,625,'heading',INK)
        for i,o in enumerate(('none','wood','steel','mixed')):self.button((320+i*190,610,175,50),o.upper(),'obstacles',o,g.obstacles==o,disabled=g.map_key!='classic')
        self.box((35,690,1205,120));load=active(g.profile)
        g.wrap_label(' / '.join(item_name(s,'skill',self.lang) for s in load['skills']) or self.say('스킬 없음','No skills'),pygame.Rect(55,700,805,38),'body_b',WHITE)
        g.wrap_label(' / '.join(item_name(s,'passive',self.lang) for s in load['perks']) or self.say('패시브 없음','No passives'),pygame.Rect(55,740,805,34),'small',INK)
        g.label(self.say('강철 링: 12턴까지 경계벽, 13턴부터 장외 개방','Steel Ring: walls retract on turn 13'),55,774,'small',GOLD)
        self.button((880,720,335,65),'CONFIRM & START','start',selected=True)
    def shop(self):
        g=self.g;g.label(self.say('캡슐 상점','CAPSULE SHOP'),640,130,'title',WHITE,'center')
        for i,kind in enumerate(('passive','skill','skin')):
            x=40+i*410;self.box((x,215,380,335))
            g.label({'passive':'PASSIVES','skill':'SKILLS','skin':'SKINS'}[kind],x+190,240,'title',WHITE,'center')
            key={'passive':'heavenly','skill':'bull','skin':'rainbow'}[kind]
            self.assets.icon(g.screen,key,kind,(x+130,285,120,120))
            self.button((x+30,455,320,65),self.say(f'뽑기 · {PRICES[kind]} 코인',f'DRAW · {PRICES[kind]} Coins'),'draw',kind,disabled=self.draw_time>0,color=i)
        g.label(self.say('일반 60%   희귀 25%   영웅 12%   전설 3%','Common 60%   Rare 25%   Epic 12%   Legendary 3%'),640,590,'heading',INK,'center')
        g.label(self.say('등급 내 동일 확률 · 중복 시 가격의 40% 환급','Equal odds within rarity · Duplicate refunds 40%'),640,628,'body',INK,'center')
        if self.result:
            r=self.result
            if self.draw_time>0:
                pygame.draw.circle(g.screen,GOLD,(640,735),int(40+10*math.sin(g.frame*.3)),7);g.label('OPENING...',640,795,'body_b',GOLD,'center')
            else:
                self.assets.icon(g.screen,r['item'],r['kind'],(260,690,100,100))
                g.label(item_name(r['item'],r['kind'],self.lang),650,712,'title',RARITY[r['rarity']],'center')
                g.label(f"DUPLICATE: +{r['refund']} Coins" if r['duplicate'] else 'NEW! Added to your inventory',650,760,'body_b',INK,'center')
    def inventory(self):
        g=self.g;p=self.profile_for_edit();load=active(p)
        for i,(key,title) in enumerate((('skill','SKILLS'),('passive','PASSIVES'),('skin','SKINS'),('stats','STATS'))):
            self.button((200+i*155,105,145,50),title,'tab',key,self.tab==key)
        self.button((855,105,175,50),'BLUE','team',0,self.inventory_team==0)
        self.button((1045,105,175,50),'RED / CPU','team',1,self.inventory_team==1)
        self.box((35,185,790,495));self.box((845,185,395,495))
        if self.tab=='stats':
            g.label(self.say(f"스탯 포인트 {sum(load['stats'].values())} / 50",f"POINTS {sum(load['stats'].values())} / 50"),65,205,'heading',GOLD)
            for i,(key,cap) in enumerate(STAT_CAPS.items()):
                y=265+i*76;title=STAT_KO[key] if self.lang=='ko' else key.upper()
                g.label(f"{title}  {load['stats'][key]} / {cap}",65,y+12,'heading',INK)
                for j,delta in enumerate((-5,-1,1,5)):self.button((390+j*95,y,80,52),f'{delta:+}','stat',(key,delta),color=0 if delta<0 else 1)
        else:
            keys=list(SKILLS if self.tab=='skill' else PERKS if self.tab=='passive' else SKINS)
            owned=p[{'skill':'owned_skills','passive':'owned_perks','skin':'owned_skins'}[self.tab]]
            for i,key in enumerate(keys):
                x=50+i%4*192;y=200+i//4*153;rect=pygame.Rect(x,y,178,140)
                pygame.draw.rect(g.screen,(36,47,85),rect,border_radius=12)
                self.assets.icon(g.screen,key,self.tab,(x+46,y+7,86,86))
                selected=self.selected==(self.tab,key)
                pygame.draw.rect(g.screen,GOLD if selected else LINE,rect,3 if selected else 1,border_radius=12)
                if key not in owned:
                    shade=pygame.Surface((86,86),pygame.SRCALPHA);shade.fill((0,0,0,140));g.screen.blit(shade,(x+46,y+7))
                    g.label('LOCKED',x+89,y+45,'small',WHITE,'center')
                name=item_name(key,self.tab,self.lang)
                g.fit_label(name,pygame.Rect(x+3,y+100,172,38),'small',WHITE)
                self.widgets.append((rect,'item',(self.tab,key)))
        g.label('SELECT SLOT',1040,202,'heading',GOLD,'center')
        for i in range(2):
            rect=pygame.Rect(870+i*180,245,155,155)
            key=load['skills'][i] if i<len(load['skills']) else None
            pygame.draw.rect(g.screen,(10,16,36),rect,border_radius=10)
            if key:self.assets.icon(g.screen,key,'skill',rect.inflate(-12,-12))
            else:g.label('EMPTY',*rect.center,'body',INK,'center')
            if self.tab=='skill' and self.slot==i:
                if key:self.assets.frame(g.screen,key,rect,g.frame)
                else:pygame.draw.rect(g.screen,GOLD,rect,4,border_radius=10)
            g.label(str(i+1),rect.x+8,rect.y+5,'heading',GOLD)
            self.widgets.append((rect,'slot',('skill',i)))
        for i in range(3):
            rect=pygame.Rect(870+i*118,435,100,100);key=load['perks'][i] if i<len(load['perks']) else None
            pygame.draw.rect(g.screen,(10,16,36),rect,border_radius=10)
            if key:self.assets.icon(g.screen,key,'passive',rect.inflate(-8,-8))
            else:g.label('+',*rect.center,'title',INK,'center')
            pygame.draw.rect(g.screen,GOLD if self.tab=='passive' and self.slot==i else LINE,rect,3,border_radius=10)
            self.widgets.append((rect,'slot',('passive',i)))
        self.assets.icon(g.screen,load.get('skin','classic'),'skin',(870,570,75,75))
        g.label(item_name(load.get('skin','classic'),'skin',self.lang),965,590,'body_b',INK)
        if self.tab in ('skill','passive'):self.button((965,625,245,42),'UNEQUIP','unequip',color=2)
        self.box((35,700,1205,115))
        if self.selected:
            kind,key=self.selected;rarity=PERKS[key].rarity if kind=='passive' else SKILL_RARITIES[key] if kind=='skill' else SKINS[key].rarity
            title=item_name(key,kind,self.lang)+'  ·  '+tr(rarity,self.lang)
            if kind=='skill':title+=self.say(f' · 재사용 {COOLDOWNS[key]}턴',f' · CD {COOLDOWNS[key]} turns') if key!='curse' else self.say(' · 경기당 1회',' · ONCE PER MATCH')
            g.label(title,55,710,'body_b',RARITY[rarity])
            g.wrap_label(description(key,kind,self.lang),pygame.Rect(55,748,920,60),'small',INK)
            self.button((1000,735,215,60),'EQUIP','equip',self.selected,color=1)
        else:g.label(self.say('오른쪽 슬롯 → 아이템 그림 → 장착 순서로 선택하세요.','Choose a slot, choose an item, then EQUIP.'),55,742,'heading',INK)
    def settings(self):
        g=self.g;self.button((900,105,270,50),'UNMUTE' if g.sound.muted else 'MUTE','mute',color=2); g.label('OPTIONS',640,125,'title',WHITE,'center');self.box((160,200,960,610))
        g.label('LANGUAGE',195,235,'heading',INK)
        self.button((630,220,200,55),'KOREAN','language','ko',self.lang=='ko')
        self.button((855,220,200,55),'ENGLISH','language','en',self.lang=='en')
        for i,(key,title) in enumerate((('screen_shake','SCREEN SHAKE'),('hit_stop','HIT STOP'),('flash','FLASH EFFECTS'),('window_shake','WINDOW SHAKE (EXPERIMENTAL)'))):
            y=305+i*75;g.label(title,195,y+15,'body_b',INK)
            on=g.profile['settings'][key];self.button((855,y,200,55),'ON' if on else 'OFF','option',key,on,color=2)
        for i,(key,title,volume) in enumerate((('sfx','SFX VOLUME',g.sound.sfx_volume),('music','MUSIC VOLUME',g.sound.music_volume))):
            y=620+i*70;g.label(title,195,y+13,'heading',INK);g.label(f'{volume:.0%}',665,y+13,'heading',GOLD)
            self.button((820,y,100,50),'-','volume',(key,-.1));self.button((950,y,100,50),'+','volume',(key,.1))


def battle_panel(g):
    g._stat_sliders.clear();g._lab_widgets.clear();a=g.menu.assets;lang=g.profile['settings']['language']
    for team in (0,1):
        x=25 if team==0 else 950
        pygame.draw.rect(g.screen,PANEL,(x,150,305,665),border_radius=18)
        g.label('BLUE' if team==0 else 'RED',x+20,170,'title',WHITE)
        g.label(f"{len(g.arena.living(team))}"+('개 생존' if lang=='ko' else ' MARBLES'),x+20,220,'heading',INK)
        for i,key in enumerate(g.arena.team_perks[team]):
            a.icon(g.screen,key,'passive',(x+16,280+i*80,65,65))
            g.fit_label(item_name(key,'passive',lang),pygame.Rect(x+90,290+i*80,200,45),'body',INK)
        if 'curve' in g.arena.team_perks[team] and team==g._input_team():
            g.label(f'C: CURVE {g.curve:+.2f}',x+18,530,'body_b',GOLD)
        # Square skill tray stays at the bottom corners, separate from the arena.
        for i,key in enumerate(g.loadouts[team].slots):
            rect=pygame.Rect(x+15+i*145,625,130,130)
            a.icon(g.screen,key,'skill',rect)
            cooldown=g.loadouts[team].remaining(key,g.turn_number)
            if key=='curse':cooldown=max(cooldown,11-g.turn_number)
            if cooldown>0 or key in g.loadouts[team].used_once:
                fog=pygame.Surface(rect.size,pygame.SRCALPHA);fog.fill((4,6,16,185));g.screen.blit(fog,rect)
                g.label('USED' if key in g.loadouts[team].used_once else str(cooldown),*rect.center,'title',WHITE,'center')
            if team==g._input_team() and g.loadouts[team].selected==i:a.frame(g.screen,key,rect,g.frame)
            g.label(str(i+1),rect.x+7,rect.y+3,'heading',GOLD)
            g.fit_label(item_name(key,'skill',lang),pygame.Rect(rect.x-3,rect.bottom+7,136,40),'small',WHITE)
            if team==g._input_team():g._lab_widgets.append((rect,'slot',i))
        if team==g._input_team() and team!=g.turn and not g.defense_ready:
            rect=pygame.Rect(x+15,562,275,47);g.action_button(rect,'READY [SPACE]',tint=BLUE);g._lab_widgets.append((rect,'ready',None))
