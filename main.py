"""MARBLE FLICK v0.7 — passives, persistent loadouts, arcade menus.

Controls
--------
LEFT MOUSE: click your disc, pull BACK from your target, release to shoot
TAB: pass turn            F: toggle double-speed physics
F1/F2/F3: floor         D: physics debug overlay
R: rematch              ESC: configuration menu
M: mute/unmute

Version 0.6 preserves the v0.5 physics and turn loop with pre-match loadouts.
P grants 1000 test Coins in this local test version.
"""
from __future__ import annotations

import array
from pathlib import Path
import math
import random
import sys
import os
import logging
from copy import deepcopy
from dataclasses import dataclass

try:
    import pygame  # type: ignore[import-not-found]
except ImportError:
    print("Pygame is not installed. Run: python -m pip install -r requirements.txt")
    raise SystemExit(1)

from physics import Arena, DRAG, Egg, Event, STOP_SPEED, ARENA_BOUNDS, MAX_PULL, MIN_PULL, vector_from_pull, make_match
from stats import STAT_CAPS, POINT_BUDGET, accuracy_cone, apply_shot_error, shot_speed_multiplier, drag_resistance_multiplier, power_transfer_multiplier, critical_chance, collision_mass_multiplier
from cpu import CPUPlanner, DIFFICULTIES
from abilities import SKILLS, SKILL_NAMES, SkillLoadout, PreparedSkill, can_prepare

from audio import SoundBox
from perks import validate
from save_data import SaveStore
from inventory import active
from economy import reward
from effects import ImpactFX
from ui import MenuUI, battle_panel
from stats import TeamStats
from localization import tr
from maps import apply_map, MAPS, music_for
from skins import paint as paint_skin

SCREEN_W, SCREEN_H = 1280, 900
ARENA_RECT = pygame.Rect(*ARENA_BOUNDS)
FPS = 60
FIXED_DT = 1 / 240
TURN_SECONDS = 25.0
DRAG_LENGTH = MAX_PULL

BG = (14, 19, 43)
PANEL = (24, 33, 65)
PANEL_LIGHT = (35, 52, 91)
TEXT = (240, 246, 255)
MUTED = (174, 193, 220)
BLUE = (81, 194, 255)
RED = (255, 118, 116)
GOLD = (255, 206, 115)
GREEN = (139, 225, 159)
WHITE = (255, 255, 255)

FLOOR_OPTIONS = ("normal", "ice", "mud")
OBSTACLE_OPTIONS = ("none", "wood", "steel", "mixed")
COUNT_OPTIONS = (1, 4, 5, 6, 7, 8, 9, 10)


def blend(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def clamp(n, lo, hi):
    return max(lo, min(hi, n))


def make_font(size, bold=False):
    path=Path(__file__).resolve().parent/'assets/fonts'/('NotoSansKR-Bold.ttf' if bold else 'NotoSansKR-Regular.ttf')
    font=pygame.font.Font(str(path),size) if path.is_file() else pygame.font.SysFont('malgungothic,arial',size)
    font.set_bold(False)
    return font


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple
    life: float
    max_life: float
    size: float


class Game:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 256)
        pygame.init()
        pygame.display.set_caption("Marble Flick v0.7")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.fonts = {
            "hero": make_font(64, True),
            "title": make_font(32, True),
            "heading": make_font(24, True),
            "body": make_font(20, False),
            "body_b": make_font(20, True),
            "small": make_font(18, False),
            "micro": make_font(16, True),
        }
        self.sound = SoundBox()
        self.store=SaveStore()
        self.profile=self.store.load()
        self.red_loadout=self.profile.setdefault('red_loadout',deepcopy(active(self.profile)))
        self.development='--dev' in sys.argv or os.environ.get('MARBLE_DEV')=='1'
        self.curve=0.; self.locked_curve=0.; self.eyes_ready={0:1,1:1}
        self.eyes_notice={}; self.rewarded=False; self.reward_amount=0
        self.fx=ImpactFX()
        self.menu=MenuUI(self)
        self.sound.sfx_volume=self.profile['audio']['sfx']
        self.sound.music_volume=self.profile['audio']['music']
        self.sound.muted=self.profile['audio']['muted']
        self.sound.music('main_menu');self.sound.play('menu')
        self.state = "menu"  # menu | aim | moving | over
        self.map_key="classic"; self.curse_timer=0.; self.eyes_targets={}; self.eyes_flash=0.
        self.clutch_music=False; self._settings_return_state=None
        self.count = 10
        self.floor = "normal"
        self.obstacles = "none"
        self.cpu_mode = "normal"  # "off" = local 2-player, otherwise bot difficulty
        self.cpu_planner: CPUPlanner | None = None
        self.cpu_delay = 0.0
        self.arena: Arena | None = None
        self.board = None
        self.turn = 0
        self.turn_left = TURN_SECONDS
        self.turn_number = 1
        self.dragging_id: int | None = None
        self.mouse = (0, 0)
        self.speed_factor = 1
        self.accumulator = 0.0
        self.travel_time = 0.0
        self.settle_time = 0.0
        self.winner = None
        self.particles: list[Particle] = []
        self.trails: dict[int, list[tuple[float,float]]] = {}
        self.frame = 0
        self.hit_count = 0
        self.debug = False
        self.status = ""
        self.status_life = 0.0
        self._menu_widgets: list[tuple[pygame.Rect, str, object]] = []
        self.rng = random.Random()
        self.edit_team = 0
        self.dragging_stat: tuple[int, str] | None = None
        self._stat_sliders: list[tuple[pygame.Rect, int, str]] = []
        self._lab_widgets: list[tuple[pygame.Rect, str, object]] = []
        self.inspect_id: int | None = None
        self.last_deviation = 0.0
        self.loadouts = {0: SkillLoadout(["brickwall", "tiger"]),
                         1: SkillLoadout(["brickwall", "cola"])}
        self.prepared: dict[int, PreparedSkill | None] = {0: None, 1: None}
        self.locked_attack = None  # (egg_id, dx, dy)
        self.defense_ready = False
        self.e_armed = False
        self.reveal_timer = 0.0
        self.chain_window = 0.0
        self.chain_target = None
        self.brick_expiry = {}  # egg_id -> last attack turn on which it is active

    def label(self, text, x, y, font="body", color=TEXT, align="topleft", target=None):
        surf = self.fonts[font].render(tr(str(text),getattr(self,"profile",{}).get("settings",{}).get("language","en")), True, color)
        rect = surf.get_rect(**{align: (round(x), round(y))})
        (target or self.screen).blit(surf, rect)
        return rect

    def fit_label(self,text,rect,font='body',color=TEXT):
        rect=pygame.Rect(rect);text=tr(str(text),self.profile['settings']['language'])
        f=self.fonts[font]
        # Keep legibility: wrap long item names rather than shrinking to tiny type.
        if f.size(text)[0]>rect.w:
            return self.wrap_label(text,rect,font,color,center=True)
        return self.label(text,*rect.center,font,color,'center')

    def wrap_label(self,text,rect,font='body',color=TEXT,center=False):
        rect=pygame.Rect(rect);text=tr(str(text),self.profile['settings']['language'])
        f=self.fonts[font];lines=[];line=''
        for char in text:
            if char=='\n' or (line and f.size(line+char)[0]>rect.w):
                lines.append(line);line='' if char=='\n' else char
            else:line+=char
        if line:lines.append(line)
        step=f.get_linesize()
        old=self.screen.get_clip();self.screen.set_clip(rect)
        for i,line in enumerate(lines):
            self.label(line,rect.centerx if center else rect.x,rect.y+i*step,font,color,'midtop' if center else 'topleft')
        self.screen.set_clip(old)

    def sync_music(self):
        if hasattr(self.sound,'music') and self.arena:
            self.sound.music('curse' if self.state=='curse' else music_for(self.arena,getattr(self,'clutch_music',False)))

    def rounded(self, rect, fill, radius=12, stroke=None, width=1, target=None):
        surface = self.screen if target is None else target
        pygame.draw.rect(surface, fill, rect, border_radius=radius)
        if stroke is not None:
            pygame.draw.rect(surface, stroke, rect, width, border_radius=radius)

    def action_button(self, rect, text, selected=False, disabled=False, small=False, tint=BLUE):
        hovered = rect.collidepoint(self.mouse) and not disabled
        if disabled:
            fill, outline, text_color = (24, 30, 41), (46, 56, 69), (93, 107, 125)
        elif selected:
            fill = blend(PANEL_LIGHT, tint, .23)
            outline, text_color = tint, TEXT
        elif hovered:
            fill, outline, text_color = (216, 242, 255), (113, 145, 173), TEXT
        else:
            fill, outline, text_color = PANEL, (55, 71, 90), MUTED
        self.rounded(rect, fill, 11, outline)
        self.label(text, rect.centerx, rect.centery, "small" if small else "body_b", text_color, "center")

    def menu_button(self, rect, text, action, value, selected=False, tint=BLUE):
        self.action_button(rect, text, selected, tint=tint)
        self._menu_widgets.append((rect, action, value))

    def banner(self, text, seconds=2.3):
        self.status, self.status_life = text, seconds

    def start_match(self):
        if hasattr(self,'profile'):
            for load in (active(self.profile),self.red_loadout):
                validate(load['perks'],self.count)
            self.loadouts={0:SkillLoadout(list(active(self.profile)['skills'])),1:SkillLoadout(list(self.red_loadout['skills']))}
        self.arena = make_match(self.count, self.floor, self.obstacles)
        apply_map(self.arena,getattr(self,"map_key","classic"))
        if hasattr(self,'profile'):
            for team,load in ((0,active(self.profile)),(1,self.red_loadout)):
                self.arena.team_stats[team]=TeamStats(**load['stats'])
            self.arena.configure_perks({0:active(self.profile)['perks'],1:self.red_loadout['perks']},self.count)
            self.store.save(self.profile)
        self.curve=0.;self.locked_curve=0.;self.eyes_ready={0:1,1:1};self.eyes_notice={}
        self.rewarded=False;self.reward_amount=0
        self.eyes_targets={};self.eyes_flash=0.;self.curse_timer=0.;self.clutch_music=False
        if hasattr(self,'fx'):
            self.fx.restore_window();self.fx=ImpactFX()
        self.sound.play('match')
        if hasattr(self.sound,'music'):self.sound.music(music_for(self.arena))
        self.board = self._make_board(self.floor)
        self.state = "aim"
        self.turn = 0
        self.turn_left = TURN_SECONDS
        self.turn_number = 1
        self.dragging_id = None
        self.accumulator = 0.0
        self.travel_time = 0.0
        self.settle_time = 0.0
        self.particles.clear()
        self.trails = {e.id: [] for e in self.arena.eggs}
        self.frame = 0
        self.winner = None
        self.hit_count = 0
        self.edit_team = 0
        self.inspect_id = None
        self.dragging_stat = None
        self.last_deviation = 0.0
        old_slots = {team: list(book.slots) for team, book in self.loadouts.items()}
        self.loadouts = {team: SkillLoadout(old_slots[team]) for team in (0, 1)}
        self.prepared = {0: None, 1: None}
        self.locked_attack = None
        self.defense_ready = False
        self.e_armed = False
        self.reveal_timer = 0.0
        self.chain_window = 0.0
        self.chain_target = None
        self.brick_expiry = {}
        self.cpu_planner = None
        self.cpu_delay = 0.0
        self._stat_sliders.clear()
        self._lab_widgets.clear()
        mode_text = "LOCAL 2P" if self.cpu_mode == "off" else f"CPU {self.cpu_mode.upper()}"
        self.banner(f"BLUE STARTS  |  {mode_text}  |  50 POINTS / TEAM", 2.0)
        self.sound.play("click")

    def _make_board(self, floor):
        w, h = ARENA_RECT.size
        surf = pygame.Surface((w, h)).convert()
        rng = random.Random(73561 + FLOOR_OPTIONS.index(floor) * 100)
        if floor == "normal":
            c1, c2, grid = (205, 237, 214), (171, 218, 199), (159, 204, 185)
        elif floor == "ice":
            c1, c2, grid = (215, 245, 255), (164, 213, 239), (147, 200, 228)
        else:
            c1, c2, grid = (233, 213, 177), (210, 184, 147), (194, 168, 130)
        for y in range(h):
            pygame.draw.line(surf, blend(c1, c2, y / h), (0, y), (w, y))
        for x in range(0, w, 40):
            pygame.draw.line(surf, grid, (x, 0), (x, h), 1)
        for y in range(0, h, 40):
            pygame.draw.line(surf, grid, (0, y), (w, y), 1)
        if floor == "ice":
            for _ in range(45):
                x, y = rng.randrange(w), rng.randrange(h)
                step = rng.randint(16, 62)
                pygame.draw.line(surf, (78, 132, 159), (x, y),
                                 (x + step, y - step // 4), 1)
        elif floor == "mud":
            for _ in range(165):
                x, y = rng.randrange(w), rng.randrange(h)
                pygame.draw.ellipse(surf, (64, 55, 45),
                    pygame.Rect(x, y, rng.randrange(3, 25), rng.randrange(2, 10)))

        # Clash-style coloured halves; perspective is intentionally fixed for
        # this *local* two-player prototype: blue below, red above.
        overlay = pygame.Surface((w,h),pygame.SRCALPHA)
        pygame.draw.rect(overlay, (*RED, 20), (0, 0, w, h//2))
        pygame.draw.rect(overlay, (*BLUE, 21), (0, h//2, w, h-h//2))
        surf.blit(overlay, (0,0))
        pygame.draw.line(surf, (104, 124, 141), (0, h//2), (w, h//2), 2)
        pygame.draw.circle(surf, (89, 113, 128), (w//2, h//2), 66, 2)
        pygame.draw.circle(surf, (89, 113, 128), (w//2, h//2), 5)
        texture=MAPS.get(getattr(self,'map_key','classic'),MAPS['classic'])[2] if getattr(self,'map_key','classic')!='classic' else floor
        path=Path(__file__).resolve().parent/'assets'/'themes'/('arena_'+texture+'.png')
        if path.is_file():
            try: surf=pygame.transform.smoothscale(pygame.image.load(str(path)).convert(),(w,h))
            except (pygame.error,OSError) as exc:logging.warning('Theme %s: %s',path,exc)
        return surf

    def update_floor(self, floor):
        if self.floor == floor:
            return
        self.floor = floor
        if self.arena is not None:
            self.arena.floor = floor
            self.board = self._make_board(floor)
            self.banner(f"SURFACE CHANGED: {floor.upper()}")

    def _input_team(self):
        if self.state != "aim":
            return None
        if self.cpu_mode != "off":
            return 0 if (self.turn == 1 or self.locked_attack is None) else None
        return self.turn if self.locked_attack is None else 1 - self.turn

    def _input_is_attacker(self):
        return self._input_team() == self.turn and self.locked_attack is None

    def _set_prepared(self, team, egg):
        skill = self.loadouts[team].equipped()
        if not skill:return
        if not self.loadouts[team].ready(skill, self.turn_number):
            self.banner("CURSE: TURN 11+, ONCE PER MATCH" if skill=="curse" else "SKILL ON COOLDOWN", 1.8)
            return
        if not can_prepare(skill, team == self.turn):
            self.banner("SKILL NOT AVAILABLE ON THIS TURN", 1.6)
            return
        if egg.team != team or egg.brickwall:
            return
        if self.prepared[team] and self.prepared[team].name == skill and self.prepared[team].egg_id == egg.id:
            self.prepared[team] = None
            self.banner("SKILL CANCELLED", .9)
        else:
            self.prepared[team] = PreparedSkill(skill, egg.id)
            self.banner(f"{SKILL_NAMES[skill]} ARMED: MARBLE #{egg.id % self.count + 1}", 1.2)
        self.sound.play("click")

    def lock_shot(self, egg_id, mouse_release):
        if not self.arena or self.state != "aim" or self.locked_attack is not None:
            return
        egg = next((e for e in self.arena.living(self.turn) if e.id == egg_id), None)
        if egg is None or egg.brickwall:
            return
        attack_skill = self.prepared[self.turn]
        if attack_skill and attack_skill.name == "brickwall" and attack_skill.egg_id == egg_id:
            self.banner("BRICKWALL IS IMMOBILE: SHOOT A DIFFERENT MARBLE", 1.9)
            return
        if attack_skill and attack_skill.name != "brickwall" and attack_skill.egg_id != egg_id:
            self.banner("SHOOT THE MARBLE WITH THE ARMED ATTACK SKILL", 1.9)
            return
        dx, dy = vector_from_pull(egg.x, egg.y, mouse_release[0], mouse_release[1])
        if math.hypot(dx, dy) < MIN_PULL:
            return
        self.locked_attack = (egg_id, dx, dy)
        self.locked_curve=getattr(self,"curve",0.)
        self.dragging_id = None
        self.e_armed = False
        self.banner("ATTACK LOCKED! WAITING FOR DEFENDER READY", 1.8)
        self.sound.play("lock")

    def detect_defense(self):
        if not self.arena or not self.defense_ready:return
        if not hasattr(self,'eyes_ready'):self.eyes_ready={0:1,1:1};self.eyes_notice={}
        team=self.turn; skill=self.prepared[1-team]
        if skill and 'eyes' in self.arena.team_perks.get(team,[]) and self.turn_number>=self.eyes_ready[team]:
            self.eyes_ready[team]=self.turn_number+8
            self.eyes_notice[team]=SKILL_NAMES[skill.name]
            if not hasattr(self,'eyes_targets'):self.eyes_targets={}
            self.eyes_targets[team]=skill.egg_id;self.eyes_flash=1.15
            self.sound.play('eyes_activate')
            if self.cpu_mode=='off' or team==0:self.banner('EYES OF HEAVEN: '+SKILL_NAMES[skill.name],3)

    def ready_defense(self):
        if self.state != "aim" or self.defense_ready:
            return
        if self.cpu_mode != "off" and self.turn == 0:
            return  # CPU automatically readies; humans cannot control RED.
        self.defense_ready = True
        self.e_armed = False
        self.banner("DEFENSE LOCKED", 1.0)
        self.detect_defense()
        self.sound.play("lock")

    def _cpu_defense(self):
        if self.defense_ready or self.cpu_mode == "off" or self.turn != 0 or not self.arena:
            return
        # Choose from publicly available positions, not the concealed human aim.
        candidates = self.arena.living(1)
        options=[s for s in self.loadouts[1].slots if can_prepare(s,False) and self.loadouts[1].ready(s,self.turn_number)]
        skill=self.rng.choice(options) if options else None
        if candidates and skill and self.loadouts[1].ready(skill, self.turn_number):
            risk = sorted(candidates, key=lambda e: (
                min(e.x-self.arena.left, self.arena.right-e.x, e.y-self.arena.top, self.arena.bottom-e.y),
                min(math.hypot(e.x-b.x, e.y-b.y) for b in self.arena.living(0))
                if self.arena.living(0) else 9999))
            if risk and self.rng.random() < (.40 if self.cpu_mode == "easy" else .75):
                self.prepared[1] = PreparedSkill(skill, risk[0].id)
        self.defense_ready = True
        self.detect_defense()

    def _cpu_prepare_attack(self, shot):
        if not self.arena or self.state != "aim" or self.turn != 1 or self.locked_attack:
            return
        selected = next((e for e in self.arena.living(1) if e.id == shot.egg_id), None)
        if selected is None:
            return
        options = [s for s in self.loadouts[1].slots if self.loadouts[1].ready(s, self.turn_number) and can_prepare(s,True)]
        # CPU offensive loadout is editable from the SKILL LAB panel.
        if options and self.rng.random() < .76:
            offensive = [s for s in options if s != "brickwall"]
            if offensive:
                self.prepared[1] = PreparedSkill(self.rng.choice(offensive), selected.id)
            elif "brickwall" in options:
                others = [e for e in self.arena.living(1) if e.id != selected.id]
                if others:
                    self.prepared[1] = PreparedSkill("brickwall", self.rng.choice(others).id)
        self.locked_attack = (selected.id, shot.dx, shot.dy)
        self.cpu_planner = None
        self.sound.play("lock")

    def _finish_turn(self, passed=False):
        self.dragging_id = None
        if not self.arena:
            return
        self.arena.check_survivors()
        self.process_clutch()
        self.arena.finish_team_turn(self.turn)
        self.arena.clear_defenses()
        for egg_id, expiry in list(self.brick_expiry.items()):
            if self.turn_number >= expiry:
                self.arena.deactivate_brickwall(egg_id)
                del self.brick_expiry[egg_id]
        a, b = len(self.arena.living(0)), len(self.arena.living(1))
        if a == 0 or b == 0:
            self.state = "over"
            self.winner = 1 if a == 0 and b else (0 if b == 0 and a else -1)
            if hasattr(self,'profile') and not self.rewarded:
                self.reward_amount=reward(self.profile,self.winner);self.rewarded=True
                self.store.save(self.profile)
                self.sound.play('victory' if self.winner==0 else 'defeat')
            return
        self.turn = 1 - self.turn
        self.turn_number += 1
        self.arena.turn_number=self.turn_number
        self.curve=0.;self.locked_curve=0.;self.eyes_notice={};self.eyes_targets={}
        self.turn_left = TURN_SECONDS
        self.state = "aim"
        self.locked_attack = None
        self.defense_ready = False
        self.prepared = {0: None, 1: None}
        self.e_armed = False
        self.chain_window = 0.0
        self.chain_target = None
        self.cpu_planner = None
        self.cpu_delay = 0.0
        if passed:
            self.banner("TURN PASSED", 1.0)

    def _start_reveal(self):
        self.detect_defense()
        self.state = "reveal"
        self.reveal_timer = .63
        self.e_armed = False
        self.sound.play("reveal")

    def _launch_revealed(self):
        if not self.locked_attack or not self.arena:
            self._finish_turn(passed=True)
            return
        attacker, defender = self.turn, 1-self.turn
        for team in (attacker, defender):
            active = self.prepared[team]
            if not active:
                continue
            selected = next((e for e in self.arena.living(team) if e.id == active.egg_id), None)
            if selected is None or not self.loadouts[team].ready(active.name, self.turn_number):
                continue
            # No partial spending on an invalid/removed target.
            if active.name == "brickwall":
                if not self.arena.activate_brickwall(selected.id):
                    continue
                self.brick_expiry[selected.id] = self.turn_number + (1 if team == attacker else 0)
            if team==defender and active.name in ("bull","ankle_breaker","infinity"):
                if not self.arena.activate_defense(selected.id,active.name):continue
            self.loadouts[team].commit(active.name, self.turn_number)
        egg_id, dx, dy = self.locked_attack
        selected = next((e for e in self.arena.living(attacker) if e.id == egg_id), None)
        if selected is None:
            self._finish_turn(passed=True)
            return
        active = self.prepared[attacker]
        ability = active.name if active and active.egg_id == egg_id and active.name != "brickwall" else ""
        if ability=="curse":
            self.state="curse";self.curse_timer=1.8;self.sound.play("curse_charge");self.sync_music()
            self.banner("CURSE UNLEASHED!",1.8)
            return
        cone = 0.0 if ability == "tiger" else self.arena.cone(selected)
        dx, dy, deviation = apply_shot_error(dx, dy, cone, self.rng)
        self.last_deviation = deviation
        if not self.arena.shoot(egg_id, dx, dy, ability=ability, curve=getattr(self,"locked_curve",0.)):
            self._finish_turn(passed=True)
            return
        self.state = "moving"
        self.travel_time = 0.0
        self.settle_time = 0.0
        self.accumulator = 0.0
        self.sound.play({"tiger":"tiger", "chain":"chain", "cola":"cola_charge", "bull":"bull_charge"}.get(ability, "shoot"))
        if cone:
            self.banner(f"AIM ERROR: {deviation:+.2f} DEG", .9)
        else:
            self.banner(f"{SKILL_NAMES.get(ability, 'PERFECT AIM')}!" if ability else "0 DEG AIM ERROR", 1.0)

    def _chain_redirect(self, auto=False):
        if not self.arena or self.chain_target is None:
            return
        egg = next((e for e in self.arena.living() if e.id == self.chain_target), None)
        if not egg:
            self.chain_window = 0.0
            return
        if auto:
            options = self.arena.living(1-egg.team)
            if not options:
                return
            target = min(options, key=lambda o: math.hypot(o.x-egg.x,o.y-egg.y))
            dx, dy = target.x-egg.x, target.y-egg.y
        else:
            dx, dy = self.mouse[0]-egg.x, self.mouse[1]-egg.y
        if self.arena.chain_redirect(egg.id, dx, dy):
            self.chain_window = 0.0
            self.chain_target = None
            self.sound.play("chain_dash")

    def process_clutch(self):
        for ev in self.arena.events:
            if ev.kind=='clutch':
                for skill in self.loadouts[ev.team].slots:self.loadouts[ev.team].ready_at[skill]=self.turn_number
                # Convert after processing so repeated checks never reset twice.
                ev.kind='clutch_fx'
                self.clutch_music=True;self.sync_music()

    def spawn_effect(self, ev: Event):
        if hasattr(self,'fx'):
            visual=Event('clutch' if ev.kind=='clutch_fx' else ev.kind,ev.x,ev.y,ev.team,ev.strength)
            self.fx.emit(visual)
        if ev.kind in ('clutch_fx','last_resort'):
            self.sound.play('clutch' if ev.kind=='clutch_fx' else 'passive')
            self.banner(('CLUTCH! SKILLS RESET' if ev.kind=='clutch_fx' else 'LAST RESORT! EDGE SHIELD'),2.5)
            return
        if ev.kind in ('bull_ready','bull_freeze','bull_counter','bull_impact','ankle_breaker_ready','ankle_dodge','infinity_ready','infinity_stop','curse_launch','walls_open'):
            self.sound.play(ev.kind)
            if ev.kind=='walls_open':self.banner('STEEL WALLS OPEN!',3)
            color,px,py,count,life=(200,100,255),ev.x,ev.y,24,.55
        elif ev.kind in ("injury", "cola_explosion"):
            color = (225, 46, 67) if ev.kind == "injury" else (241, 85, 82)
            px, py, count, life = ev.x, ev.y, 35 if ev.kind == "cola_explosion" else 19, .8
            self.sound.play("cola_explosion" if ev.kind == "cola_explosion" else "injury")
        elif ev.kind in ("fall", "cola_sacrifice"):
            color = BLUE if ev.team == 0 else RED
            px = clamp(ev.x, ARENA_RECT.left, ARENA_RECT.right)
            py = clamp(ev.y, ARENA_RECT.top, ARENA_RECT.bottom)
            count, life = 22, .7
            if ev.kind == "fall": self.sound.play("drop")
        elif ev.kind in ("brickwall_on", "brickwall_hit", "brickwall_off"):
            color, px, py, count, life = (174,182,190), ev.x, ev.y, 13, .45
            if ev.kind != "brickwall_off":
                self.sound.play(ev.kind)
        elif ev.kind in ("chain_hit", "chain_dash", "tiger_wind"):
            color = (251, 196, 74) if ev.kind != "tiger_wind" else (167, 232, 255)
            px, py, count, life = ev.x, ev.y, 15, .32
            self.sound.play(ev.kind)
        elif ev.kind == "wood_break":
            color, px, py, count, life = (226,178,107), ev.x, ev.y, 20, .7
            self.sound.play("breaker")
        elif ev.kind == "wood_hit":
            color, px, py, count, life = (226,178,107), ev.x, ev.y, 5, .2
        else:
            color, px, py, count, life = (240,247,255), ev.x, ev.y, 8, .3
            self.hit_count += 1
            self.sound.play("clack")
        for _ in range(min(count,max(0,400-len(self.particles)))):
            a = self.rng.uniform(0, math.tau)
            power = self.rng.uniform(45, 190) * (.65 + ev.strength)
            duration = life * self.rng.uniform(.42, 1.05)
            self.particles.append(Particle(px, py, math.cos(a)*power,
                                           math.sin(a)*power, color,
                                           duration, duration, self.rng.uniform(2,5.3)))

    def update(self, dt):
        self.frame += 1
        if hasattr(self.sound,'update'):self.sound.update(dt)
        if hasattr(self,'menu'):self.menu.update(dt)
        if hasattr(self,'fx'):
            self.fx.configure(getattr(self,'profile',{}).get('settings',{}))
            self.fx.allow_window_motion=self.state in ('moving','curse') and not self.chain_window
            freeze=self.fx.freeze>0 and self.fx.settings.get('hit_stop',True)
            self.fx.update(dt)
            if freeze and self.state=='moving':return
        self.mouse = pygame.mouse.get_pos() if pygame.display.get_init() else self.mouse
        self.status_life = max(0.0, self.status_life-dt)
        self.eyes_flash=max(0.,getattr(self,"eyes_flash",0.)-dt)
        for p in self.particles:
            p.life -= dt
            p.x += p.vx*dt
            p.y += p.vy*dt
            p.vx *= max(0, 1-dt*2.8)
            p.vy *= max(0, 1-dt*2.8)
        self.particles = [p for p in self.particles if p.life > 0]

        if self.state == "aim":
            previous_second=math.ceil(self.turn_left)
            self.turn_left = max(0, self.turn_left-dt)
            if 0<math.ceil(self.turn_left)<=5 and math.ceil(self.turn_left)!=previous_second:self.sound.play('countdown')
            if self.cpu_mode != "off" and self.turn == 1 and self.locked_attack is None:
                self.update_cpu(dt)
            if self.cpu_mode != "off" and self.turn == 0 and not self.defense_ready:
                self.cpu_delay += dt
                if self.cpu_delay >= .60:
                    self._cpu_defense()
            if self.turn_left <= 0:
                if self.locked_attack is None:
                    if self.cpu_mode != "off" and self.turn == 1 and self.cpu_planner and self.cpu_planner.best:
                        self._cpu_prepare_attack(self.cpu_planner.best)
                    else:
                        self._finish_turn(passed=True)
                if self.state == "aim":
                    self.defense_ready = True
            if self.state == "aim" and self.locked_attack is not None and self.defense_ready:
                self._start_reveal()
        elif self.state == "reveal":
            self.reveal_timer -= dt
            if self.reveal_timer <= 0:
                self._launch_revealed()
        elif self.state == 'curse' and self.arena:
            self.curse_timer-=dt
            if self.curse_timer<=0:
                self.arena.cast_curse(self.turn);self.sound.play('curse_release')
                self.state='moving';self.travel_time=0.;self.settle_time=0.;self.accumulator=0.;self.sync_music()
        elif self.state == "moving" and self.arena:
            self.travel_time += dt
            if self.chain_window > 0.0:
                self.chain_window -= dt
                if self.cpu_mode != "off" and self.turn == 1 and self.chain_window < 1.45:
                    self._chain_redirect(auto=True)
                if self.chain_window <= 0:
                    self.chain_target = None
            else:
                self.accumulator += dt*self.speed_factor
                steps = 0
                # Tiger moves 3x as fast; smaller substeps avoid tunneling.
                simdt = FIXED_DT/2 if any(e.tiger for e in self.arena.living()) else FIXED_DT
                while self.accumulator >= simdt and steps < 64:
                    self.arena.step(simdt)
                    self.accumulator -= simdt
                    steps += 1
                    # Cola explodes on stop, even if other discs are moving.
                    self.arena.trigger_cola_if_stopped()
                    # Pause physical time while the human chooses a chain link.
                    if any(ev.kind == "chain_hit" for ev in self.arena.events):
                        shooting = next((e for e in self.arena.living() if e.id == self.arena.active_shooter_id), None)
                        if shooting and shooting.chain_ready and shooting.chain_followups < 5:
                            self.chain_target = shooting.id
                            self.chain_window = 1.75
                            break
                if self.accumulator > simdt * 64:
                    self.accumulator = simdt * 64
                if self.frame % 3 == 0:
                    for egg in self.arena.living():
                        if egg.speed > 30:
                            points = self.trails[egg.id]
                            points.append((egg.x,egg.y))
                            if len(points)>10:
                                points.pop(0)
                if not self.arena.moving() and not self.chain_window:
                    self.settle_time += dt
                    if self.settle_time > .28 and self.travel_time > .3:
                        self._finish_turn()
                else:
                    self.settle_time = 0.0
        if self.arena is not None and self.arena.events:
            self.process_clutch()
            for ev in self.arena.events:
                self.spawn_effect(ev)
            self.arena.events.clear()

    def update_cpu(self, dt):
        self.cpu_delay += dt
        if self.cpu_delay < .38:
            return
        if self.cpu_planner is None:
            self.cpu_planner = CPUPlanner(self.arena, team=1,
                                          difficulty=self.cpu_mode,
                                          seed=self.turn_number*7919 + self.count*31)
        if not self.cpu_planner.candidates:
            self._finish_turn(passed=True)
            return
        shot = self.cpu_planner.think_one()
        if shot is not None:
            self._cpu_prepare_attack(shot)

    def _selected_egg(self):
        if self.arena is None or self.inspect_id is None:
            return None
        return next((e for e in self.arena.living() if e.id == self.inspect_id), None)

    def _lab_action(self, action, arg):
        if not self.arena:
            return
        if action == "team":
            self.edit_team = int(arg)
        elif action == "preset":
            stats = self.arena.team_stats[self.edit_team]
            if arg == "clear":
                stats.reset()
            elif arg == "attack":
                stats.preset(speed=20, power=30)
            elif arg == "defense":
                stats.preset(toughness=30, accuracy=15, critical=5)
            elif arg == "precision":
                stats.preset(accuracy=15, critical=10, power=25)
            elif arg == "speed":
                stats.preset(speed=30)
            self.banner(f"{['BLUE','RED'][self.edit_team]} LOADOUT: {str(arg).upper()}", 1.2)
        elif action == "injure":
            egg = self._selected_egg()
            if egg is not None:
                if self.arena.injure(egg.id):
                    self.banner(f"MARBLE #{egg.id+1} INJURED FOR 2 OWNER TURNS", 1.8)
                else:
                    self.banner("ALREADY INJURED: NO STACKING", 1.2)
        elif action == "heal":
            egg = self._selected_egg()
            if egg is not None and self.arena.heal(egg.id):
                self.banner(f"MARBLE #{egg.id+1} HEALED", 1.2)
        elif action == "mud_mode":
            self.arena.mud_variance = not self.arena.mud_variance
            self.banner("MUD CHAOS " + ("ON" if self.arena.mud_variance else "OFF"), 1.2)
        elif action == "floor":
            self.update_floor(arg)
        self.sound.play("click")

    def _pick_egg(self, pos, team=None):
        if not self.arena:
            return None
        options = self.arena.living(team)
        if not options:
            return None
        chosen = min(options, key=lambda e:(e.x-pos[0])**2+(e.y-pos[1])**2)
        return chosen if math.hypot(chosen.x-pos[0],chosen.y-pos[1]) <= chosen.r+9 else None

    def _skill_ui_action(self, action, arg):
        if action == "slot":
            team=self._input_team()
            if team is not None:self.loadouts[team].select_slot(int(arg))
        elif action == "equip":
            try:
                current = self.loadouts[self.edit_team].equipped()
                self.loadouts[self.edit_team].equip(self.loadouts[self.edit_team].selected, arg)
                if current != arg:
                    self.prepared[self.edit_team] = None
            except ValueError:
                self.banner("ALREADY EQUIPPED IN OTHER SLOT", 1.2)
        elif action == "ready":
            self.ready_defense()
        self.sound.play("click")

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            if hasattr(self,'menu'):self.menu.persist()
            return False
        if hasattr(self,'menu'):
            if event.type==pygame.KEYDOWN and event.key==pygame.K_p:
                self.profile['coins']+=1000;self.menu.persist();self.banner('+1000 Coins')
                return True
            if event.type==pygame.KEYDOWN and event.key==pygame.K_F10 and self.state!='menu':
                self._settings_return_state=self.state;self.state='menu';self.dragging_id=None;self.fx.shake=0.;self.fx.restore_window();self.menu.go('settings');return True
            if self.state=='menu':return self.menu.event(event)
            if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                self.state='menu';self.dragging_id=None;self._settings_return_state=None;self.fx.shake=0.;self.fx.restore_window();self.menu.go('home');return True
            if event.type==pygame.KEYDOWN and event.key==pygame.K_c and self.state=='aim' and self._input_is_attacker() and 'curve' in self.arena.team_perks[self.turn]:
                self.curve={0.:.75,.75:1.5,1.5:-1.5,-1.5:-.75,-.75:0.}.get(self.curve,0.)
            if event.type==pygame.MOUSEWHEEL and self.state=='aim' and self._input_is_attacker() and 'curve' in self.arena.team_perks[self.turn] and pygame.key.get_pressed()[pygame.K_c]:
                self.curve=round(clamp(self.curve+event.y*.15,-1.5,1.5),2)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and self.arena and self.state != "menu":
            e = self._pick_egg(event.pos)
            if e:
                self.inspect_id = e.id
                self.banner(f"INSPECT: {['BLUE','RED'][e.team]} #{e.id+1}", 1.0)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.state == "menu":
                for rect, action, value in self._menu_widgets:
                    if rect.collidepoint(pos):
                        if action == "start": self.start_match()
                        elif action == "count": self.count = value
                        elif action == "floor": self.floor = value
                        elif action == "obstacles": self.obstacles = value
                        elif action == "cpu": self.cpu_mode = value
                        self.sound.play("click")
                        break
            elif self.state == "over":
                if pygame.Rect(463,511,165,46).collidepoint(pos): self.start_match()
                elif pygame.Rect(647,511,165,46).collidepoint(pos):
                    self.state="menu"
                    if hasattr(self,"menu"):self.menu.go("home")
            elif self.arena is not None and any(rect.collidepoint(pos) for rect, _, _ in self._lab_widgets):
                for rect, action, arg in self._lab_widgets:
                    if rect.collidepoint(pos):
                        if action in ("slot", "equip", "ready"):
                            self._skill_ui_action(action, arg)
                        else:
                            self._lab_action(action,arg)
                        break
            elif self.state == "aim" and self.arena:
                input_team = self._input_team()
                egg = self._pick_egg(pos, input_team) if input_team is not None else None
                if egg is not None:
                    if self.e_armed:
                        if input_team != self.turn and self.defense_ready:
                            self.banner("DEFENSE ALREADY READY", 1.0)
                        else:
                            self._set_prepared(input_team, egg)
                        self.e_armed = False
                    elif self._input_is_attacker() and not egg.brickwall:
                        self.dragging_id = egg.id
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.state == "aim" and self.dragging_id is not None:
                self.lock_shot(self.dragging_id, event.pos)
                self.dragging_id = None
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = "menu"
                self.dragging_id = None
                self.dragging_stat = None
            elif event.key == pygame.K_r and self.state == "over":
                self.start_match()
            elif event.key in (pygame.K_1,pygame.K_2) and self.state=="aim":
                team=self._input_team()
                if team is not None and self.loadouts[team].slots:
                    self.loadouts[team].select_slot(min(len(self.loadouts[team].slots)-1,0 if event.key==pygame.K_1 else 1))
                    self.edit_team=team
                    self.banner(f"SLOT {self.loadouts[team].selected+1}: {SKILL_NAMES[self.loadouts[team].equipped()]}", 1.0)
            elif event.key == pygame.K_e:
                if self.state == "moving" and self.chain_window > 0 and (self.cpu_mode=="off" or self.turn == 0):
                    self._chain_redirect()
                elif self.state == "aim":
                    team=self._input_team()
                    if team is not None and not (team!=self.turn and self.defense_ready):
                        self.e_armed = not self.e_armed
                        self.edit_team=team
                        self.banner("E: CLICK YOUR MARBLE TO ARM SKILL" if self.e_armed else "SKILL SELECTION CANCELLED", 1.0)
            elif event.key == pygame.K_SPACE and self.state=="aim" and (self.locked_attack is not None or (self.cpu_mode!="off" and self.turn==1)):
                self.ready_defense()
            elif event.key == pygame.K_TAB and self.state == "aim" and self._input_is_attacker():
                self._finish_turn(passed=True)
            elif event.key == pygame.K_d: self.debug=not self.debug
            elif event.key == pygame.K_f:
                self.speed_factor = 2 if self.speed_factor == 1 else 1
                self.banner(f"SIMULATION SPEED: x{self.speed_factor}", 1.0)
            elif event.key == pygame.K_m:
                self.sound.muted=not self.sound.muted
                if hasattr(self,'profile'):self.profile['audio']['muted']=self.sound.muted;self.menu.persist()
            elif event.key == pygame.K_v and self.arena and getattr(self,"development",False): self._lab_action("mud_mode",None)
            elif event.key == pygame.K_j and self.arena and getattr(self,"development",False): self._lab_action("injure",None)
            elif event.key == pygame.K_k and self.arena and getattr(self,"development",False): self._lab_action("heal",None)
            elif event.key in (pygame.K_F1,pygame.K_F2,pygame.K_F3) and getattr(self,"development",False):
                self.update_floor({pygame.K_F1:"normal",pygame.K_F2:"ice",pygame.K_F3:"mud"}[event.key])
        return True

    def draw_global_background(self):
        self.screen.fill(BG)
        pygame.draw.circle(self.screen, (27, 35, 68), (190, -75), 240)
        pygame.draw.circle(self.screen, (31, 39, 81), (1170, 825), 320)

    def curse_background(self,size):
        if self.state!='curse':return None
        image=self.menu.assets.image('themes/노곡빈.png')
        if image:
            key=('curse',tuple(size))
            if key not in self.menu.assets.scaled:self.menu.assets.scaled[key]=pygame.transform.smoothscale(image,size)
            return self.menu.assets.scaled[key]
        return None

    def draw_menu(self):
        self.menu.render()

    def draw_egg_disc(self, x, y, r, team, number=None, selected=False, hovered=False, injured=False, inspected=False, brick=False, skill=None):
        x, y, r = round(x), round(y), int(r)
        color = (130, 136, 149) if brick else ((119, 37, 52) if injured else (BLUE if team == 0 else RED))
        if inspected:
            pygame.draw.circle(self.screen, GOLD, (x, y), r+10, 2)
        if skill:
            pygame.draw.circle(self.screen, GOLD, (x,y), r+9, 2)
        pygame.draw.ellipse(self.screen, (11, 21, 32), (x-r+3,y-r+7,2*r,2*r))
        if selected:
            pygame.draw.circle(self.screen, WHITE, (x,y), r+7, 3)
            pygame.draw.circle(self.screen, color, (x,y), r+12, 1)
        elif hovered:
            pygame.draw.circle(self.screen, blend(color,WHITE,.3), (x,y), r+6, 2)
        pygame.draw.circle(self.screen, blend(color,(6,16,29),.20), (x,y), r)
        pygame.draw.circle(self.screen, blend(color,WHITE,.35), (x,y), r, 2)
        pygame.draw.circle(self.screen, blend(color,WHITE,.40), (x-r//4,y-r//3), max(3,r//3))
        pygame.draw.circle(self.screen, blend(color,WHITE,.06), (x,y+3), max(4,r//2))
        if not brick and hasattr(self,'profile'):
            load=active(self.profile) if team==0 else self.red_loadout
            paint_skin(self.screen,pygame.Rect(x-r,y-r,2*r,2*r),load.get('skin','classic'),team)
        if injured:
            pygame.draw.line(self.screen, (232,69,84), (x-r//3,y-r//2),(x+3,y+r//4),2)
        if brick:
            pygame.draw.line(self.screen,(66,75,84),(x-r//2,y-r//3),(x+5,y+4),2)
            pygame.draw.line(self.screen,(66,75,84),(x+5,y+4),(x+12,y-4),2)
        if number is not None:
            self.label(number, x, y+1, "micro", (244, 220, 222) if injured else (11, 22, 33), "center")

    def draw_board(self):
        if self.board is None or not self.arena:
            return
        surround = ARENA_RECT.inflate(14, 14)
        self.rounded(surround, (12, 23, 33), 14, (80, 111, 134), 2)
        back=self.curse_background(ARENA_RECT.size)
        self.screen.blit(back if back is not None else self.board, ARENA_RECT.topleft)
        if self.state=='curse' and back is None:
            haze=pygame.Surface(ARENA_RECT.size,pygame.SRCALPHA);haze.fill((100,0,145,130));self.screen.blit(haze,ARENA_RECT)
        for zone in self.arena.zones:
            rect=pygame.Rect(zone.x,zone.y,zone.w,zone.h)
            tile=pygame.Surface(rect.size,pygame.SRCALPHA)
            color=(80,205,255) if zone.floor=='ice' else (120,72,29)
            pygame.draw.rect(tile,(*color,165),tile.get_rect(),border_radius=18)
            pygame.draw.rect(tile,(*color,240),tile.get_rect(),3,border_radius=18)
            self.screen.blit(tile,rect)
            self.label('ICE' if zone.floor=='ice' else 'MUD',rect.centerx,rect.centery,'small',WHITE,'center')
        if self.arena.boundary_walls and not self.arena.walls_open:
            pygame.draw.rect(self.screen,(170,190,213),ARENA_RECT.inflate(10,10),7,border_radius=5)
        pygame.draw.rect(self.screen, (120, 145, 157), ARENA_RECT, 2)
        # Accent corner guides mark the actual, deadly, boundary.
        for x, sx in ((ARENA_RECT.left,1),(ARENA_RECT.right,-1)):
            for y, sy in ((ARENA_RECT.top,1),(ARENA_RECT.bottom,-1)):
                pygame.draw.line(self.screen, GOLD, (x, y), (x+sx*33,y), 3)
                pygame.draw.line(self.screen, GOLD, (x, y), (x,y+sy*33), 3)
        self.label("RED  /  OPPONENT", ARENA_RECT.centerx, ARENA_RECT.top+11,
                   "micro", blend(RED,WHITE,.33), "midtop")
        self.label("BLUE  /  YOUR SIDE", ARENA_RECT.centerx, ARENA_RECT.bottom-25,
                   "micro", blend(BLUE,WHITE,.33), "midtop")

        for o in self.arena.obstacles:
            if not o.alive:
                continue
            rect = pygame.Rect(round(o.x),round(o.y),round(o.w),round(o.h))
            if o.material == "wood":
                self.rounded(rect.move(3,4), (26, 30, 29), 5)
                self.rounded(rect, (146, 100, 60), 5, (207, 155, 86), 2)
                for i in range(1, 4):
                    x = rect.x + rect.w * i//4
                    pygame.draw.line(self.screen, (99, 67, 44), (x,rect.y+5), (x,rect.bottom-5), 2)
                if o.hp < 1.0:
                    pygame.draw.line(self.screen, (55, 42, 30), rect.center,
                                     (rect.centerx+8,rect.y+4), 2)
            else:
                self.rounded(rect.move(3,4), (19, 28, 35), 5)
                self.rounded(rect, (107, 126, 143), 5, (181, 202, 218), 2)
                pygame.draw.line(self.screen, (177, 204, 218), (rect.x+6,rect.y+6),
                                 (rect.right-6,rect.y+6), 2)
                pygame.draw.line(self.screen, (65, 86, 105), (rect.x+8,rect.bottom-7),
                                 (rect.right-8,rect.bottom-7), 2)

        # Draw trajectory trails UNDER discs.
        trail_surface = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for egg in self.arena.living():
            trail = self.trails.get(egg.id, [])
            if not trail or egg.speed <= 28:
                continue
            c = GOLD if egg.tiger or egg.chain else BLUE if egg.team == 0 else RED
            allpts = trail + [(egg.x,egg.y)]
            for i, p in enumerate(allpts[:-1]):
                t = (i+1)/len(allpts)
                pygame.draw.line(trail_surface, (*c, int(20+140*t)),
                                 p, allpts[i+1], max(1,round(1+5*t)))
        self.screen.blit(trail_surface, (0,0))

        hover = None
        if self.state == "aim":
            eggs = self.arena.living(self._input_team())
            inside = [((e.x-self.mouse[0])**2 + (e.y-self.mouse[1])**2, e.id) for e in eggs]
            if inside:
                near = min(inside)
                if near[0] <= 28*28:
                    hover = near[1]
        for e in self.arena.living():
            tremble=math.sin(self.frame*2.4+e.id)*4 if self.state=='curse' and e.team!=self.turn else 0
            self.draw_egg_disc(e.x+tremble,e.y,e.r,e.team,e.id % self.count + 1,
                               selected=(self.dragging_id == e.id),
                               hovered=(hover == e.id and self.dragging_id is None),
                               injured=(e.injury_turns > 0), inspected=(self.inspect_id == e.id),
                               brick=e.brickwall,
                               skill=(next((p.name for p in self.prepared.values() if p and p.egg_id==e.id),None)
                                      if (self.state == "reveal" or e.team == self._input_team()) else None))
            revealed=self.state in ('reveal','moving','curse')
            prep=next((p.name for p in self.prepared.values() if p and p.egg_id==e.id),None)
            defense=e.defense or (prep if revealed else '')
            if revealed and defense in ('bull','infinity'):
                radius=e.r+(75 if defense=='bull' else 130)
                pygame.draw.circle(self.screen,(255,105,50) if defense=='bull' else (95,115,255),(round(e.x),round(e.y)),int(radius),2)
            if getattr(self,'eyes_targets',{}).get(self.turn)==e.id and (self.cpu_mode=='off' or self.turn==0):
                pulse=8+int(4*math.sin(self.frame*.22));pos=(round(e.x),round(e.y))
                pygame.draw.circle(self.screen,(255,40,220),pos,int(e.r+pulse),6)
                pygame.draw.line(self.screen,(255,255,255),(pos[0]-e.r-15,pos[1]),(pos[0]+e.r+15,pos[1]),2)
                self.label('LOCK ON: '+self.eyes_notice[self.turn],clamp(e.x,490,790),e.y-e.r-40,'body_b',(255,45,230),'center')
            if self.arena.protected(e):
                pygame.draw.circle(self.screen,GOLD,(round(e.x),round(e.y)),int(e.r+8),3)
            if self.arena.friendship(e)>1:
                pygame.draw.circle(self.screen,GREEN,(round(e.x),round(e.y)),int(e.r+4),2)
            if e.injury_turns:
                self.label(f"-{e.injury_turns}", e.x+e.r+3, e.y-e.r-8, "micro", (240, 92, 110))
            if self.debug and e.speed >= STOP_SPEED:
                pygame.draw.line(self.screen, GREEN, (e.x,e.y),
                                 (e.x+e.vx*.085,e.y+e.vy*.085), 2)
                self.label(str(round(e.speed)), e.x+14, e.y-24, "small", GREEN)

        if self.dragging_id is not None and self.state == "aim":
            e = next((egg for egg in self.arena.eggs if egg.id==self.dragging_id),None)
            if e:
                self.draw_aim(e)
        if self.state == "reveal" and self.locked_attack:
            egg_id, dx, dy = self.locked_attack
            e = next((egg for egg in self.arena.living() if egg.id==egg_id),None)
            if e:
                distance=max(1,math.hypot(dx,dy))
                ux,uy=dx/distance,dy/distance
                endpoint=(round(e.x+ux*135),round(e.y+uy*135))
                pygame.draw.line(self.screen,GOLD,(round(e.x),round(e.y)),endpoint,4)
                pygame.draw.circle(self.screen,GOLD,endpoint,7)
        if self.chain_window > 0 and self.chain_target is not None:
            e = next((e for e in self.arena.living() if e.id==self.chain_target),None)
            if e:
                pygame.draw.circle(self.screen,GOLD,(round(e.x),round(e.y)),round(e.r+16),3)
                if self.cpu_mode=="off" or self.turn==0:
                    pygame.draw.line(self.screen,GOLD,(e.x,e.y),self.mouse,2)
        for p in self.particles:
            fade = p.life/p.max_life
            color = blend(BG,p.color,fade)
            pygame.draw.circle(self.screen,color,(round(p.x),round(p.y)),max(1,round(p.size*fade)))

    def draw_aim(self, egg):
        # The cursor is the handle of a slingshot. Pull DOWN to shoot UP.
        dx, dy = vector_from_pull(egg.x, egg.y, *self.mouse)
        mag = math.hypot(dx,dy)
        if mag < 2:
            return
        ux,uy = dx/mag,dy/mag
        dist = min(mag,DRAG_LENGTH)
        pct = dist/DRAG_LENGTH
        c = blend(BLUE,GOLD,pct)
        # Backward pull line (mouse direction), visually distinct from aim arrow.
        pull_end = (egg.x-ux*dist, egg.y-uy*dist)
        pygame.draw.line(self.screen,(82,146,167), (egg.x,egg.y),pull_end,2)
        pygame.draw.circle(self.screen, c, (round(pull_end[0]),round(pull_end[1])),6,2)
        # Real full-cone angular uncertainty, including current injury penalty.
        cone = self.arena.cone(egg)
        if cone > 0:
            direction = math.atan2(uy, ux)
            half = math.radians(cone) / 2
            spread_dist = min(315, 170+dist)
            points = [(egg.x, egg.y)]
            for idx in range(25):
                angle = direction - half + idx / 24 * (2 * half)
                points.append((egg.x+math.cos(angle)*spread_dist, egg.y+math.sin(angle)*spread_dist))
            # Draw on board-sized alpha surface rather than allocating a full
            # window-sized texture for every cursor movement.
            wedge = pygame.Surface(ARENA_RECT.size, pygame.SRCALPHA)
            local = [(x-ARENA_RECT.x,y-ARENA_RECT.y) for x,y in points]
            pygame.draw.polygon(wedge, (*GOLD, 64), local)
            pygame.draw.line(wedge, (*GOLD, 155), local[0], local[1], 2)
            pygame.draw.line(wedge, (*GOLD, 155), local[0], local[-1], 2)
            self.screen.blit(wedge, ARENA_RECT.topleft)
        # Forward trajectory preview is opposite to mouse drag.
        origin=(egg.x+ux*(egg.r+4),egg.y+uy*(egg.r+4))
        end=(egg.x+ux*(dist+egg.r+24),egg.y+uy*(dist+egg.r+24))
        for i in range(1,8):
            alpha=i/8
            pos=(round(egg.x+ux*(dist+egg.r+i*26)),
                 round(egg.y+uy*(dist+egg.r+i*26)))
            pygame.draw.circle(self.screen, blend((38,55,65),c,alpha*.8),
                               pos, max(2,round(4*alpha)))
        pygame.draw.line(self.screen,c,origin,end,4)
        px,py=-uy,ux
        pygame.draw.polygon(self.screen,c,[end,
            (end[0]-ux*17+px*9,end[1]-uy*17+py*9),
            (end[0]-ux*17-px*9,end[1]-uy*17-py*9)])
        if 'curve' in self.arena.team_perks[egg.team] and getattr(self,'curve',0):
            x,y=egg.x,egg.y;vx,vy=ux*650,uy*650;curve=self.curve
            for i in range(30):
                angle=curve*.04;co,si=math.cos(angle),math.sin(angle)
                vx,vy=vx*co-vy*si,vx*si+vy*co
                curve*=math.exp(-1.2*.04)
                vx*=math.exp(-DRAG[self.floor]*.04);vy*=math.exp(-DRAG[self.floor]*.04)
                x+=vx*.04;y+=vy*.04
                pygame.draw.circle(self.screen,GOLD,(round(x),round(y)),3)
        msg=f"PULL {round(pct*100)}%  /  {cone:g} DEG"
        textx=clamp(egg.x+28,ARENA_RECT.left+8,ARENA_RECT.right-173)
        texty=clamp(egg.y-52,ARENA_RECT.top+8,ARENA_RECT.bottom-28)
        self.rounded(pygame.Rect(round(textx-7),round(texty-5),177,27),(12,25,38),7)
        self.label(msg,textx,texty,"small",c)

    def draw_stat_lab(self):
        # Battle loadouts are read-only; allocation exists only in Inventory.
        battle_panel(self)

    def draw_hud(self):
        if not self.arena:
            return
        self.draw_global_background()
        curse_bg=self.curse_background((SCREEN_W,SCREEN_H))
        if curse_bg is not None:self.screen.blit(curse_bg,(0,0))
        self.label("MARBLE FLICK",37,23,"title",TEXT)
        self.label("PASSIVES + SKILLS  /  V0.7",38,59,"small",MUTED)
        lang=self.profile['settings']['language'];map_name=MAPS[self.arena.map_key][0 if lang=='ko' else 1]
        self.label(f"{self.count}v{self.count}  |  {map_name}",SCREEN_W-36,31,'body_b',TEXT,'topright')
        self.label(f"TURN {self.turn_number}",SCREEN_W-36,60,"small",MUTED,"topright")
        active_color=BLUE if self.turn==0 else RED
        if self.state=="aim":
            attack_status="LOCKED" if self.locked_attack else "AIMING"
            defense_status="READY" if self.defense_ready else "PLANNING"
            self.label(f"{['BLUE','RED'][self.turn]} ATK {attack_status} | DEF {defense_status}",
                       640,42,"body_b",active_color,"center")
            self.label(f"{max(0,math.ceil(self.turn_left)):02d} SEC",640,70,"small",MUTED,"center")
        elif self.state=="reveal":
            self.label("LOCK REVEAL  /  SKILLS EXPOSED",640,48,"body_b",GOLD,"center")
        elif self.state=="moving":
            if self.chain_window>0:
                self.label(f"CHAIN! E TO DASH  /  {self.chain_window:.1f}s",640,47,"body_b",GOLD,"center")
            else:
                self.label("PHYSICS RUNNING",640,46,"body_b",GOLD,"center")
                self.label(f"{self.speed_factor}x PHYSICS",640,70,"small",MUTED,"center")
        else:
            self.label("MATCH FINISHED",640,55,"body_b",GOLD,"center")
        self.draw_board()
        if hasattr(self,'fx'):
            self.fx.draw(self.screen)
            if self.state in ('moving','curse') and not self.chain_window:self.fx.camera(self.screen,ARENA_RECT,self.frame)
        self.draw_stat_lab()
        pygame.draw.line(self.screen,(43,59,76),(36,831),(1244,831),1)
        if self.state=="aim":
            if self._input_is_attacker():
                msg="ATTACK: DRAG + RELEASE TO LOCK (DOES NOT FIRE YET)"
            elif self._input_team() is not None:
                msg="DEFENSE: E + CLICK MARBLE, THEN SPACE / READY"
            else:
                msg="WAITING FOR LOCKS..."
            self.label(msg,40,844,"body_b",GOLD if not self._input_is_attacker() else TEXT)
        elif self.state=="reveal":
            self.label("REVEALING LOCKED AIM AND HIDDEN DEFENSE...",40,844,"body_b",GOLD)
        elif self.state=="moving":
            self.label("CHAIN: POINT MOUSE + PRESS E TO DASH AGAIN" if self.chain_window else "WAIT FOR MARBLES TO STOP...",40,844,"body_b",GOLD)
        else:
            self.label("R REMATCH     ESC MENU",40,844,"body_b",TEXT)
        self.label("1/2 SLOT   E SKILL   SPACE DEF READY   TAB PASS   D DEBUG   F FAST",40,875,"small",MUTED)
        self.label(f"HITS: {self.hit_count}",1240,875,"small",MUTED,"topright")
        if self.status_life>0 and self.state!="over":
            toast=pygame.Rect(ARENA_RECT.centerx-220,ARENA_RECT.top+41,440,34)
            self.rounded(toast,PANEL,10,(105,178,217))
            self.fit_label(self.status,toast,"small",TEXT)
        if getattr(self,'eyes_notice',{}).get(self.turn) and (self.cpu_mode=='off' or self.turn==0):
            self.label('EYES: '+self.eyes_notice[self.turn],640,106,'body_b',(130,65,177),'center')
        if getattr(self,'eyes_flash',0)>0 and (self.cpu_mode=='off' or self.turn==0):
            image=self.menu.assets.image('vfx/eyes_of_heaven.png')
            if image:
                key=('eyes_banner',)
                if key not in self.menu.assets.scaled:self.menu.assets.scaled[key]=pygame.transform.smoothscale(image,(540,180))
                self.screen.blit(self.menu.assets.scaled[key],(370,170))
        if self.state=='curse':self.label('CURSE UNLEASHED!',640,80,'heading',(255,90,255),'center')
        if self.state=="over":
            self.draw_victory()

    def draw_victory(self):
        fog=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
        fog.fill((6,11,19,189))
        self.screen.blit(fog,(0,0))
        rect=pygame.Rect(386,295,508,281)
        self.rounded(rect,PANEL,22,(91,124,154),2)
        color=BLUE if self.winner==0 else RED if self.winner==1 else GOLD
        message="BLUE WINS!" if self.winner==0 else "RED WINS!" if self.winner==1 else "DRAW!"
        self.label("FINAL RESULT",640,328,"small",MUTED,"midtop")
        self.label(message,640,388,"title",color,"center")
        if hasattr(self,'reward_amount'):
            bounce=math.sin(min(1,(self.frame%120)/120)*math.pi)*5
            self.label(f"+{self.reward_amount} Coins",640,475-bounce,'heading',GOLD,'center')
        self.label(f"{self.turn_number} TURNS  |  {self.hit_count} COLLISIONS",640,442,"small",MUTED,"center")
        self.action_button(pygame.Rect(463,511,165,46),"REMATCH",tint=BLUE)
        self.action_button(pygame.Rect(647,511,165,46),"MENU",tint=GOLD)

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(FPS)/1000, .05)
            self.mouse=pygame.mouse.get_pos()
            for event in pygame.event.get():
                if self.handle_event(event) is False:
                    running=False
                    break
            self.update(dt)
            if self.state == "menu":
                self.draw_menu()
            else:
                self.draw_hud()
            pygame.display.flip()
        self.fx.restore_window()
        pygame.quit()


if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG if '--audio-debug' in sys.argv else logging.INFO,
                        format='%(levelname)s %(name)s: %(message)s')
    Game().run()
