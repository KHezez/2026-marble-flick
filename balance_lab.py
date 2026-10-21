"""Quick reproducible comparison of SPEED distance vs POWER knockback.
Run with `python balance_lab.py`, no Pygame required.
"""
from physics import Arena, Egg


def travel(level):
    a = Arena(left=0, top=0, width=3000, height=500)
    a.team_stats[0].set('speed', level)
    a.eggs = [Egg(0, 0, 150, 250)]
    a.shoot(0, 180, 0)
    for _ in range(1200):
        a.step(1 / 240)
        if not a.moving():
            break
    return a.eggs[0].x - 150


def knockback(level):
    a = Arena(left=0, top=0, width=3000, height=500)
    a.team_stats[0].set('power', level)
    a.eggs = [Egg(0, 0, 150, 250), Egg(1, 1, 310, 250)]
    a.shoot(0, 180, 0)
    peak_speed = 0.0
    for _ in range(1200):
        a.step(1 / 240)
        peak_speed = max(peak_speed, a.eggs[1].speed)
        if not a.moving():
            break
    return a.eggs[1].x - 310, peak_speed


if __name__ == '__main__':
    d0, d30 = travel(0), travel(30)
    k0, k30 = knockback(0), knockback(30)
    print('MARBLE FLICK v0.4 / BALANCE LAB')
    print('NORMAL surface, max pull, default defender / no obstacles')
    print(f'SPEED  0/30: solo travel {d0:7.1f} px')
    print(f'SPEED 30/30: solo travel {d30:7.1f} px  (+{100*(d30/d0-1):.1f}%)')
    print(f'POWER  0/30: target knockback {k0[0]:7.1f} px (peak {k0[1]:.1f} px/s)')
    print(f'POWER 30/30: target knockback {k30[0]:7.1f} px (peak {k30[1]:.1f} px/s)')
    print('Measurements are scenario-specific, not universal damage multipliers.')
