"""Versioned local profile, atomic replace and recoverable backup; never pickle."""
from pathlib import Path
import json
import os
import shutil
import logging
from stats import TeamStats, STAT_CAPS
from perks import PERKS, validate
from abilities import SKILLS
from skins import SKINS
from runtime_paths import default_save_path

def default_profile():
    load={'skills':['brickwall','tiger'],'perks':[], 'stats':{k:0 for k in STAT_CAPS}, 'skin':'classic'}
    return {'version':3,'boss_clears':{},'coins':500,'owned_skills':['brickwall','tiger'],'owned_perks':['heavy','sniper','metal'],
            'owned_skins':['classic'], 'settings':{'language':'ko','screen_shake':True,'hit_stop':True,'flash':True,'window_shake':False}, 'active_loadout':'default','loadouts':{'default':load},'history':[],
            'audio':{'sfx':.7,'music':.45,'muted':False}}

class SaveStore:
    def __init__(self,path=None):
        self.path=Path(path) if path is not None else default_save_path()
        self.recovered=False
    def load(self):
        for path in (self.path,self.path.with_suffix('.bak')):
            try:
                data=self.sanitize(json.loads(path.read_text(encoding='utf-8')))
                self.recovered=path!=self.path
                return data
            except FileNotFoundError:continue
            except (OSError,ValueError,TypeError,KeyError) as exc:
                logging.warning('Profile cannot be loaded %s: %s',path,exc)
                self.recovered=True
        return default_profile()
    @staticmethod
    def sanitize(raw):
        if not isinstance(raw,dict):raise ValueError('Invalid profile')
        data=default_profile()
        data['coins']=max(0,int(raw.get('coins',500)))
        for field,valid in [('owned_skills',SKILLS),('owned_perks',PERKS),('owned_skins',SKINS)]:
            data[field]=list(dict.fromkeys(x for x in raw.get(field,data[field]) if x in valid))
        if 'classic' not in data['owned_skins']:data['owned_skins'].append('classic')
        data['boss_clears']={k:min(2,max(0,int(v))) for k,v in raw.get('boss_clears',{}).items() if k in ('warden','tempest','gokbin')}
        if data['boss_clears'].get('gokbin',0)<2 and 'gokbin_curse' in data['owned_skins']:data['owned_skins'].remove('gokbin_curse')
        settings=raw.get('settings',{})
        if not isinstance(settings,dict):settings={}
        for key,default in data['settings'].items():
            data['settings'][key]=(settings.get(key,'ko') if settings.get(key,'ko') in ('ko','en') else 'ko') if key=='language' else bool(settings.get(key,default))
        # Keep starter skills available even after a damaged/old save.
        for skill in ('brickwall','tiger'):
            if skill not in data['owned_skills']:data['owned_skills'].append(skill)
        for name,load in raw.get('loadouts',{}).items():
            stats=TeamStats()
            for k in STAT_CAPS: stats.set(k,int(load.get('stats',{}).get(k,0)))
            skills=list(dict.fromkeys(s for s in load.get('skills',[]) if s in data['owned_skills']))[:2]
            perks=[]
            for p in load.get('perks',[]):
                if p not in data['owned_perks']:continue
                try:validate(perks+[p])
                except ValueError:continue
                perks.append(p)
            data['loadouts'][str(name)]={'skills':skills,'perks':perks,'stats':vars(stats),'skin':load.get('skin','classic') if load.get('skin','classic') in data['owned_skins'] else 'classic'}
        active=raw.get('active_loadout','default')
        data['active_loadout']=active if active in data['loadouts'] else 'default'
        data['history']=raw.get('history',[])[-100:]
        audio=raw.get('audio',{})
        data['audio']={'sfx':max(0,min(1,float(audio.get('sfx',.7)))), 'music':max(0,min(1,float(audio.get('music',.45)))), 'muted':bool(audio.get('muted',False))}
        if isinstance(raw.get('red_loadout'),dict):
            red_raw=dict(raw);red_raw.pop('red_loadout',None)
            red_raw['loadouts']={'red':raw['red_loadout']};red_raw['active_loadout']='red'
            data['red_loadout']=SaveStore.sanitize(red_raw)['loadouts']['red']
        return data
    def save(self,data):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix('.tmp')
        with tmp.open('w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
        if self.path.exists() and not self.recovered:shutil.copy2(self.path,self.path.with_suffix('.bak'))
        os.replace(tmp,self.path); self.recovered=False
