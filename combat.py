"""v0.7 defensive skills, counter choreography and one-shot curse.
Priority: Infinity barrier > temporary invulnerability > Ankle dodge > Bull counter
> ordinary collision/injury > boundary rules. All motion is in world coordinates.
"""
from dataclasses import dataclass
from math import hypot,exp,cos,sin,tau

@dataclass
class Counter:
    owner: int
    target: int
    origin: tuple
    retreat: tuple
    contact: tuple
    age: float = 0

class CombatRules:
    def emit(self,kind,e,strength=1):
        from physics import Event
        self.events.append(Event(kind,e.x,e.y,e.team,strength))

    def invulnerable(self,e):
        return e.defense=='infinity' or e.invulnerable_until>self.elapsed

    def counter_locked(self,e):
        return any(e.id in (c.owner,c.target) for c in self.counters)

    def terrain_at(self,x,y):
        for zone in reversed(self.zones):
            if zone.x<=x<=zone.x+zone.w and zone.y<=y<=zone.y+zone.h:return zone.floor
        return self.floor

    def activate_defense(self,egg_id,skill):
        e=next((e for e in self.living() if e.id==egg_id),None)
        if e is None or e.brickwall or skill not in ('bull','ankle_breaker','infinity'):return False
        e.defense=skill;e.guard_used=False
        if skill=='infinity':e.vx=e.vy=0;e.injury_turns=0
        self.emit(skill+'_ready',e)
        return True

    def clear_defenses(self):
        for e in self.eggs:
            e.defense='';e.guard_used=False;e.invulnerable_until=0
        self.counters.clear()

    def can_place(self,e,x,y):
        if not (self.left+e.r<=x<=self.right-e.r and self.top+e.r<=y<=self.bottom-e.r):return False
        for box in self.obstacles:
            if box.alive and hypot(x-min(max(x,box.x),box.x+box.w),y-min(max(y,box.y),box.y+box.h))<e.r:return False
        return not any(other.id!=e.id and hypot(x-other.x,y-other.y)<e.r+other.r for other in self.living())

    def clear_path(self,e,start,end):
        # A swept disk must fit along the entire counter route, including retreat.
        distance=hypot(end[0]-start[0],end[1]-start[1]);steps=max(1,int(distance/max(2,e.r*.4))+1)
        for i in range(1,steps+1):
            t=i/steps;x=start[0]+(end[0]-start[0])*t;y=start[1]+(end[1]-start[1])*t
            if not self.can_place(e,x,y):return False
        return True

    def pre_collision_guard(self,a,b):
        if self.counter_locked(a) or self.counter_locked(b):return True
        if self.invulnerable(a) or self.invulnerable(b):return True
        for guard,enemy in ((a,b),(b,a)):
            if guard.team==enemy.team or guard.guard_used or enemy.speed<30:continue
            if guard.defense=='ankle_breaker':
                dx,dy=enemy.vx,enemy.vy;length=max(1,hypot(dx,dy))
                px,py=-dy/length,dx/length
                # Side-step safely; do not redirect the attacker's velocity.
                for distance in (guard.r*2.4,guard.r*1.3):
                    choices=[(guard.x+px*distance*s,guard.y+py*distance*s) for s in (-1,1)]
                    dest=next(((x,y) for x,y in choices if self.can_place(guard,x,y)),None)
                    if dest:guard.x,guard.y=dest;break
                guard.guard_used=True;guard.invulnerable_until=self.elapsed+.65
                guard.vx=guard.vy=0;self.emit('ankle_dodge',guard)
                return True
        return False

    def update_combat(self,dt):
        living=self.living()
        # Infinity is immovable. Project incoming marbles outside contact distance
        # and remove inward velocity at the inner boundary, including Tiger/Cola.
        for guard in living:
            if guard.defense!='infinity':continue
            guard.vx=guard.vy=0
            for other in living:
                if other.team==guard.team or other.brickwall:continue
                dx,dy=other.x-guard.x,other.y-guard.y;dist=hypot(dx,dy)
                radius=guard.r+other.r+110
                if dist>=radius:continue
                nx,ny=(dx/dist,dy/dist) if dist>1e-8 else (1,0)
                incoming=other.vx*nx+other.vy*ny
                if incoming<0:
                    if not guard.guard_used:self.emit('infinity_stop',guard);guard.guard_used=True
                    damp=exp(-dt*(12+65*(1-dist/radius)))
                    other.vx*=damp;other.vy*=damp
                minimum=guard.r+other.r+8
                if dist<minimum:
                    other.x=guard.x+nx*minimum;other.y=guard.y+ny*minimum
                    inward=min(0,other.vx*nx+other.vy*ny)
                    other.vx-=nx*inward;other.vy-=ny*inward
        for guard in living:
            if guard.defense!='bull' or guard.guard_used or self.counter_locked(guard):continue
            for enemy in living:
                if enemy.team==guard.team or enemy.brickwall or self.invulnerable(enemy) or self.counter_locked(enemy):continue
                distance=hypot(enemy.x-guard.x,enemy.y-guard.y)
                if enemy.speed<40 or distance>guard.r+enemy.r+55:continue
                nx,ny=((enemy.x-guard.x)/distance,(enemy.y-guard.y)/distance) if distance>1 else (0,-1)
                if enemy.vx*nx+enemy.vy*ny>=0:continue
                retreat=(guard.x-nx*42,guard.y-ny*42)
                if not self.clear_path(guard,(guard.x,guard.y),retreat):retreat=(guard.x,guard.y)
                contact=(enemy.x-nx*(guard.r+enemy.r+.05),enemy.y-ny*(guard.r+enemy.r+.05))
                if not self.clear_path(guard,retreat,contact):continue
                self.counters.append(Counter(guard.id,enemy.id,(guard.x,guard.y),retreat,contact))
                guard.guard_used=True;guard.vx=guard.vy=enemy.vx=enemy.vy=0
                self.emit('bull_freeze',enemy);self.emit('bull_counter',guard)
                break
        by_id={e.id:e for e in living}
        for c in list(self.counters):
            owner,target=by_id.get(c.owner),by_id.get(c.target)
            if not owner or not target:self.counters.remove(c);continue
            c.age+=dt;owner.vx=owner.vy=target.vx=target.vy=0
            if c.age<.14:
                pass # visibly stop the incoming attacker first
            elif c.age<.34:
                t=(c.age-.14)/.20;owner.x=c.origin[0]+(c.retreat[0]-c.origin[0])*t;owner.y=c.origin[1]+(c.retreat[1]-c.origin[1])*t
            elif c.age<.48:
                t=(c.age-.34)/.14;owner.x=c.retreat[0]+(c.contact[0]-c.retreat[0])*t;owner.y=c.retreat[1]+(c.contact[1]-c.retreat[1])*t
            else:
                owner.x,owner.y=c.contact
                dx,dy=target.x-owner.x,target.y-owner.y;dist=max(.001,hypot(dx,dy))
                from stats import power_transfer_multiplier
                strength=1500*.5*power_transfer_multiplier(self.team_stats[owner.team],owner.injury_turns>0)*self.mult(owner.team,'power')
                resistance=max(.1,self._effective_mass(target))
                target.vx=dx/dist*strength/resistance;target.vy=dy/dist*strength/resistance
                self.injure(target.id,3);self.emit('bull_impact',target,1.4)
                self.counters.remove(c)

    def cast_curse(self,team):
        """Cast choreography is handled by Game; this releases the actual velocities."""
        from physics import MAX_PULL,BASE_POWER_SCALE
        from stats import shot_speed_multiplier
        for e in self.eggs:
            e.tiger=e.bull=e.chain=e.cola=e.chain_ready=False;e.curve=0.
        self._wind_seen.clear();self._contact_cooldowns.clear();self._power_contacts.clear()
        for e in self.living(1-team):
            if e.brickwall or self.invulnerable(e):continue
            angle=self.rng.uniform(0,tau)
            speed=MAX_PULL*BASE_POWER_SCALE*shot_speed_multiplier(self.team_stats[e.team],e.injury_turns>0)*self.mult(e.team,'speed')
            e.vx=cos(angle)*speed;e.vy=sin(angle)*speed
            self.emit('curse_launch',e)
        self.active_shooter_id=None;self.attacking_team=1-team
