"""Projectile module — bullet movement, collision.

T4: projectiles travel at their config speed and deal their damage to the
zombie they hit; a lethal hit removes the zombie.
T5: arcing projectiles (throw/flare) rise then fall; flares explode into
an AoE on impact, damaging every zombie in the radius.
"""
import math

import config
import zombie


def _lethal_hit(z, game):
    """T11: after a damaging hit, begin the death animation (when enabled) or
    remove the zombie if it is now dead. A dying zombie is not removed here —
    `_death_animation` removes it when its timer expires."""
    zombie._begin_death(z, game)
    if z["hp"] <= 0 and not z.get("dying"):
        game.zombies.remove(z)


def _collide(game):
    """Deal damage where projectiles overlap zombies; remove dead entities.

    T11: a lethal hit may begin the death-sprite animation (when enabled), in
    which case the zombie is not removed immediately.
    """
    for p in list(game.projectiles):
        for z in list(game.zombies):
            if p["x"] == z["x"] and p["y"] == z["y"]:
                if "aoe_radius" in p:
                    _explode(game, p)
                else:
                    z["hp"] -= p["damage"]
                    _lethal_hit(z, game)
                    game.projectiles.remove(p)
                break


def _explode(game, p):
    """Flare impact: damage every zombie within the AoE radius."""
    radius = p["aoe_radius"]
    for z in list(game.zombies):
        if math.hypot(z["x"] - p["x"], z["y"] - p["y"]) <= radius:
            z["hp"] -= p["damage"]
            _lethal_hit(z, game)
    game.projectiles.remove(p)


def update(game, dt=1 / 60.0):
    """Update projectile state. Called each frame during a run."""
    _collide(game)
    for p in game.projectiles:
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        if "arc_vy" in p:
            # Throw arc: rise, then fall (simple gravity on the arc axis).
            p["y"] += p["arc_vy"] * dt
            p["arc_vy"] += 2 * abs(p["arc_vy"]) * dt


def init(game):
    """Initialize projectile state on game start."""
    game.projectiles = []
