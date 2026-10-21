"""Bright pre-match menu, collection, shop and read-only battle HUD."""
import math
from pathlib import Path
import pygame
from perks import PERKS, validate
from abilities import SKILLS, SKILL_NAMES, SKILL_DESCRIPTIONS, COOLDOWNS
from stats import STAT_CAPS
from inventory import active, toggle, allocate
from economy import draw, PRICES, RATES, SKILL_RARITIES

INK=(27,65,102); BLUE=(54,153,241); WHITE=(255,255,255); GOLD=(255,213,75)
RARITY={'Common':(115,157,182),'Rare':(71,159,241),'Epic':(179,102,229),'Legendary':(241,171,38)}

class MenuUI:
    def __init__(self,game):
        self.g=game;self.page='home';self.widgets=[];self.hover=None;self.selected=None
        self.draw_time=0.;self.result=None;self.themes={};self.notice=''
        self.inventory_team=0
    def background(self,key):
        g=self.g;g.screen.fill((193,233,255))
        if key not in self.themes:
            path=Path(__file__).resolve().parent/'assets'/'themes'/(key+'.png')
            try:self.themes[key]=pygame.transform.smoothscale(pygame.image.load(str(path)).convert(),(1280,900)) if path.is_file() else None
            except (pygame.error,OSError):self.themes[key]=None
        if self.themes[key]:g.screen.blit(self.themes[key],(0,0))
        else:
            pygame.draw.circle(g.screen,(226,248,255),(180,100),260)
            pygame.draw.circle(g.screen,(163,217,254),(1190,780),330)
            for i in range(12):
                x=80+(i*109)%1180; y=110+(i*163)%720+math.sin(g.frame*.015+i)*18
                pygame.draw.circle(g.screen,(242,253,255),(int(x),int(y)),14+i%4*4)
                pygame.draw.circle(g.screen,(151,204,243),(int(x),int(y)),14+i%4*4,2)
    def button(self,rect,text,action,value=None,selected=False,disabled=False):
        g=self.g;rect=pygame.Rect(rect);hover=rect.collidepoint(g.mouse)
        drawrect=rect.inflate(-5,-5) if hover and pygame.mouse.get_pressed()[0] else rect.move(0,-3 if hover else 0)
        pygame.draw.rect(g.screen,(93,163,210),drawrect.move(0,6),border_radius=20)
        fill=(204,216,227) if disabled else GOLD if selected else WHITE if not hover else (236,250,255)
        pygame.draw.rect(g.screen,fill,drawrect,border_radius=20)
        pygame.draw.rect(g.screen,(116,187,231),drawrect,2,border_radius=20)
        g.label(text,*drawrect.center,'body_b',INK,'center')
        if not disabled:self.widgets.append((rect,action,value))
    def go(self,page):
        self.page=page;self.notice='';self.selected=None
        self.g.sound.play('shop' if page=='shop' else 'menu' if page=='home' else 'transition')
        self.g.sound.music({'home':'main_menu','setup':'main_menu','shop':'shop','inventory':'inventory'}[page])
    def persist(self):
        try:self.g.store.save(self.g.profile)
        except OSError as exc:self.notice='Save failed: '+str(exc)
    def perform(self,action,value):
        g=self.g
        try:
            if action=='page':self.go(value)
            elif action in ('count','floor','obstacles','cpu_mode'):
                if action=='count' and value==1:
                    for load in (active(g.profile),g.red_loadout):validate(load['perks'],1)
                setattr(g,action,value)
            elif action=='start':g.start_match()
            elif action=='item':self.selected=value
            elif action=='equip':
                profile=self.profile_for_edit()
                toggle(profile,*value,count=g.count);g.sound.play('equip');self.persist()
            elif action=='stat':allocate(self.profile_for_edit(),*value);self.persist()
            elif action=='team':self.inventory_team=value;self.selected=None
            elif action=='draw' and self.draw_time<=0:
                self.result=draw(g.profile,value);self.draw_time=1.4;g.sound.play('draw_start');self.persist()
            elif action=='volume':
                key,delta=value;field='sfx_volume' if key=='sfx' else 'music_volume'
                setattr(g.sound,field,max(0,min(1,getattr(g.sound,field)+delta)))
                g.profile['audio'][key]=getattr(g.sound,field);self.persist()
            elif action=='mute':
                g.sound.muted=not g.sound.muted;g.profile['audio']['muted']=g.sound.muted;self.persist()
        except ValueError as exc:self.notice=str(exc)
    def profile_for_edit(self):
        if self.inventory_team==0:return self.g.profile
        # Red is a local opponent/CPU template, using the same unlocked collection.
        p=dict(self.g.profile);p['loadouts']={'red':self.g.red_loadout};p['active_loadout']='red';return p
    def event(self,event):
        if event.type==pygame.KEYDOWN and event.key==pygame.K_m:self.perform('mute',None);return True
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:self.go('home');return True
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            for rect,action,value in self.widgets:
                if rect.collidepoint(event.pos):
                    self.g.sound.play('click');self.perform(action,value);break
        return True
    def update(self,dt):
        if self.draw_time>0:
            self.draw_time=max(0,self.draw_time-dt)
            if self.draw_time==0:self.g.sound.play('rare' if self.result['rarity'] in ('Epic','Legendary') else 'draw_result')
        hit=next((str((a,v)) for r,a,v in self.widgets if r.collidepoint(self.g.mouse)),None)
        if hit!=self.hover and hit:self.g.sound.play('hover')
        self.hover=hit
    def render(self):
        g=self.g;self.widgets=[]
        self.background({'home':'main_menu','setup':'main_menu','shop':'shop','inventory':'inventory'}[self.page])
        g.label('MARBLE FLICK',52,30,'title',INK)
        g.label('v0.6  /  PLAYER BLUE',54,68,'small',INK)
        self.button((990,25,235,58),f"{g.profile['coins']:,} Coins",'noop',selected=True)
        if self.page!='home':self.button((54,106,130,42),'BACK','page','home')
        if self.page=='home':self.home()
        elif self.page=='setup':self.setup()
        elif self.page=='shop':self.shop()
        else:self.inventory()
        if self.notice:
            pygame.draw.rect(g.screen,WHITE,(55,778,1170,45),border_radius=15)
            g.label(self.notice,75,791,'body',INK)
        self.audio_controls()
    def home(self):
        g=self.g
        g.label('READY, AIM...',640,190,'hero',INK,'center')
        g.label('FLICK!',640,272,'hero',BLUE,'center')
        for x,team in ((360,0),(920,1)):
            g.draw_egg_disc(x,350+math.sin(g.frame*.04+team)*15,60,team)
        for i,(name,page) in enumerate((('START','setup'),('SHOP','shop'),('INVENTORY','inventory'))):
            self.button((440,380+i*104,400,80),name,'page',page,selected=i==0)
        g.label('Pull back. Let go. Knock them out!',640,735,'heading',INK,'center')
    def setup(self):
        g=self.g
        g.label('LET\'S PLAY!',640,150,'title',INK,'center')
        groups=[('TEAM SIZE','count',(1,4,5,6,7,8,9,10)),('OPPONENT','cpu_mode',('off','easy','normal','hard')),
                ('SURFACE','floor',('normal','ice','mud')),('OBSTACLES','obstacles',('none','wood','steel','mixed'))]
        for row,(title,action,values) in enumerate(groups):
            y=220+row*100;g.label(title,90,y+16,'heading',INK)
            for i,value in enumerate(values):
                width=100 if len(values)>4 else 190
                self.button((325+i*(width+10),y,width,55),'LOCAL 2P' if value=='off' else str(value).upper(),action,value,getattr(g,action)==value)
        load=active(g.profile)
        g.label('BLUE: '+', '.join(SKILL_NAMES[s] for s in load['skills']),90,625,'body_b',INK)
        g.label('PASSIVES: '+(', '.join(PERKS[p].name for p in load['perks']) or 'None'),90,660,'body',INK)
        g.label(f"STATS: {sum(load['stats'].values())}/50 points | Red loadout can be edited in Inventory",90,695,'body',INK)
        self.button((810,710,360,60),'CONFIRM & START','start',selected=True)
        self.button((90,730,280,42),'EDIT LOADOUT','page','inventory')
    def shop(self):
        g=self.g;g.label('LUCKY MARBLES',640,166,'title',INK,'center')
        for i,kind in enumerate(('passive','skill')):
            x=125+i*545
            pygame.draw.rect(g.screen,WHITE,(x,235,480,275),border_radius=30)
            g.label(kind.upper()+' CAPSULE',x+240,275,'title',INK,'center')
            g.draw_egg_disc(x+240,360,45,i)
            self.button((x+55,430,370,55),f'DRAW  /  {PRICES[kind]} Coins','draw',kind,disabled=self.draw_time>0)
        g.label('ODDS: Common 60%  /  Rare 25%  /  Epic 12%  /  Legendary 3%',640,550,'body_b',INK,'center')
        g.label('Equal odds within each rarity. Duplicates refund 40%. No real-money purchases.',640,580,'small',INK,'center')
        if self.result:
            r=self.result;name=PERKS[r['item']].name if r['kind']=='passive' else SKILL_NAMES[r['item']]
            if self.draw_time>0:
                radius=int(38+12*math.sin(g.frame*.3));pygame.draw.circle(g.screen,GOLD,(640,680),radius)
                g.label('OPENING...',640,750,'heading',INK,'center')
            else:
                g.label(r['rarity'].upper()+'  '+name,640,660,'title',RARITY[r['rarity']],'center')
                g.label(f"DUPLICATE: +{r['refund']} Coins" if r['duplicate'] else 'NEW! Added to your inventory',640,710,'body_b',INK,'center')
    def inventory(self):
        g=self.g;profile=self.profile_for_edit();load=active(profile)
        self.button((850,105,170,42),'BLUE LOADOUT','team',0,self.inventory_team==0)
        self.button((1035,105,170,42),'RED / CPU','team',1,self.inventory_team==1)
        g.label('PASSIVES (MAX 3)',55,175,'heading',INK)
        for i,(key,p) in enumerate(PERKS.items()):
            x=55+(i%3)*245;y=215+(i//3)*63
            owned=key in profile['owned_perks'];eq=key in load['perks']
            self.button((x,y,230,50),('ON  ' if eq else '' if owned else 'LOCK  ')+p.name,'item',('passive',key),eq)
        g.label('SKILLS (MAX 2)',55,485,'heading',INK)
        for i,key in enumerate(SKILLS):
            self.button((55+i%2*365,525+i//2*62,350,49),('ON  ' if key in load['skills'] else '' if key in profile['owned_skills'] else 'LOCK  ')+SKILL_NAMES[key],'item',('skill',key),key in load['skills'])
        g.label(f"STATS  {sum(load['stats'].values())}/50",855,190,'heading',INK)
        for i,(key,cap) in enumerate(STAT_CAPS.items()):
            y=240+i*75
            g.label(f'{key.upper()}  {load["stats"][key]}/{cap}',855,y,'body_b',INK)
            self.button((855,y+25,70,34),'-','stat',(key,-1))
            self.button((940,y+25,70,34),'+','stat',(key,1))
            self.button((1025,y+25,90,34),'+5','stat',(key,5))
        if self.selected:
            kind,key=self.selected
            desc=PERKS[key].description if kind=='passive' else SKILL_DESCRIPTIONS[key]
            rarity=PERKS[key].rarity if kind=='passive' else SKILL_RARITIES[key]
            g.label(rarity+('  /  COOLDOWN '+str(COOLDOWNS[key])+' TURNS' if kind=='skill' else ''),60,670,'body_b',RARITY[rarity])
            # Wrap by font width, not character count.
            lines=['']
            for word in desc.split():
                if g.fonts['body'].size(lines[-1]+word)[0]>850:lines.append('')
                lines[-1]+=word+' '
            for i,line in enumerate(lines):g.label(line,60,700+i*23,'body',INK)
            self.button((955,690,240,55),'EQUIP / UNEQUIP','equip',self.selected,selected=True)
    def audio_controls(self):
        g=self.g
        self.button((55,840,110,36),'UNMUTE' if g.sound.muted else 'MUTE','mute')
        g.label(f'SFX {g.sound.sfx_volume:.0%}',190,850,'small',INK)
        self.button((285,840,44,36),'-','volume',('sfx',-.1));self.button((335,840,44,36),'+','volume',('sfx',.1))
        g.label(f'BGM {g.sound.music_volume:.0%}',410,850,'small',INK)
        self.button((515,840,44,36),'-','volume',('music',-.1));self.button((565,840,44,36),'+','volume',('music',.1))
        g.label('DEV: P +1000 Coins' if g.development else 'ESC Menu  |  M Mute',930,850,'small',INK)


def battle_panel(g):
    g._stat_sliders.clear();g._lab_widgets.clear()
    for team in (0,1):
        x=35 if team==0 else 950
        pygame.draw.rect(g.screen,(239,250,255),(x,170,295,590),border_radius=24)
        g.label('BLUE' if team==0 else 'RED',x+22,193,'title',INK)
        g.label(f'{len(g.arena.living(team))} MARBLES',x+22,238,'heading',INK)
        for i,s in enumerate(g.loadouts[team].slots):
            y=300+i*73; remaining=g.loadouts[team].remaining(s,g.turn_number)
            g.label(f'{i+1}. {SKILL_NAMES[s]}',x+18,y,'body_b',INK)
            g.label(f'{remaining} turns' if remaining else 'READY',x+18,y+28,'small',BLUE)
        g.label('PASSIVES',x+20,467,'heading',INK)
        for i,p in enumerate(g.arena.team_perks[team]):g.label(PERKS[p].name,x+20,505+i*32,'body',INK)
        if 'curve' in g.arena.team_perks[team] and team==g._input_team():
            g.label(f'C: CURVE {g.curve:+.1f}',x+20,620,'body_b',INK)
            g.label('C + wheel: fine adjustment',x+20,650,'small',INK)
        if team==g._input_team() and team!=g.turn and not g.defense_ready:
            rect=pygame.Rect(x+20,690,255,45)
            g.action_button(rect,'READY [SPACE]',tint=BLUE)
            g._lab_widgets.append((rect,'ready',None))
