"""Projectile module — bullet movement, collision.

T4: projectiles travel at their config speed and deal their damage to the
zombie they hit; a lethal hit removes the zombie.
"""
import config


def _collide(game):
    """Deal damage where projectiles overlap zombies; remove dead entities."""
    for p in list(game.projectiles):
        for z in list(game.zombies):
            if p["x"] == z["x"] and p["y"] == z["y"]:
                z["hp"] -= p["damage"]
                if z["hp"] <= 0:
                    game.zombies.remove(z)
                game.projectiles.remove(p)
                break


def update(game, dt=1 / 60.0):
    """Update projectile state. Called each frame during a run."""
    _collide(game)
    for p in game.projectiles:
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt


def init(game):
    """Initialize projectile state on game start."""
    game.projectiles = []
