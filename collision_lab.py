"""No Pygame required. Repeatable automatic 10v10 impulse experiments."""
from physics import make_match


def demo():
    print("\nMARBLE FLICK | 10 vs 10 collision lab")
    print("Automated trial: launch blue front-line disc #3 at red front-line disc #3 at max power.\n")
    print(f"{'FLOOR':<8} {'OBSTACLES':<10} {'SECONDS':>8} {'HITS':>6} {'FALLS':>6} {'WOOD':>6}  ALIVE(B/R)")
    print("=" * 71)
    for floor in ("normal", "ice", "mud"):
        for obstacle in ("none", "mixed"):
            arena = make_match(10, floor, obstacle)
            source, target = arena.eggs[2], arena.eggs[12]
            assert arena.shoot(source.id, target.x - source.x, target.y - source.y)
            for step in range(3600):
                arena.step(1/240)
                if not arena.moving():
                    break
            summary = {key: sum(event.kind == key for event in arena.events)
                       for key in ("hit", "fall", "wood_break")}
            print(f"{floor:<8} {obstacle:<10} {step/240:>8.2f} {summary['hit']:>6} "
                  f"{summary['fall']:>6} {summary['wood_break']:>6}  "
                  f"{len(arena.living(0))}/{len(arena.living(1))}")
    print("\nTip: adjust DRAG and RESTITUTION_EGGS in physics.py to experiment.\n")


if __name__ == "__main__":
    demo()
