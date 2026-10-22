"""Weapon module — auto-fire, targeting, cooldowns.

T4: 9mm Pistol — auto-fires at the nearest zombie on its cooldown.
Targeting and cooldown are pure functions of the zombie list / timestamp
and the config dicts, so they are unit-testable.
"""
import math

import config


def nearest_zombie(shooter_pos, zombies):
    """Return the zombie closest to shooter_pos, or None if there are none.

    Pure function: given a (x, y) position and a list of zombie dicts,
    returns the zombie dict with the smallest Euclidean distance.
    """
    if not zombies:
        return None
    sx, sy = shooter_pos
    return min(zombies, key=lambda z: (z["x"] - sx) ** 2 + (z["y"] - sy) ** 2)


def should_fire(last_fired, now, fire_rate):
    """Return True if the weapon may fire at time `now`.

    Pure function: `last_fired` is the timestamp of the previous shot
    (None if it has never fired), `now` is the current timestamp, and
    `fire_rate` is the minimum seconds between shots (from config).
    """
    if last_fired is None:
        return True
    return (now - last_fired) >= fire_rate


def _fire(game, weapon_state, target):
    """Spawn a projectile from the weapon toward the target zombie."""
    cfg = config.WEAPON["types"][weapon_state["type"]]
    p = game.player
    dx = target["x"] - p["x"]
    dy = target["y"] - p["y"]
    length = math.hypot(dx, dy)
    if length == 0:
        dx, dy = 1.0, 0.0
        length = 1.0
    speed = cfg["bullet_speed"]
    game.projectiles.append({
        "x": p["x"],
        "y": p["y"],
        "vx": dx / length * speed,
        "vy": dy / length * speed,
        "damage": cfg["damage"],
    })
    weapon_state["last_fired"] = game.run_time


def update(game, dt=1 / 60.0):
    """Update weapon state. Called each frame during a run."""
    for weapon_state in game.weapons:
        cfg = config.WEAPON["types"][weapon_state["type"]]
        if not should_fire(weapon_state["last_fired"], game.run_time, cfg["fire_rate"]):
            continue
        target = nearest_zombie((game.player["x"], game.player["y"]), game.zombies)
        if target is None:
            continue
        _fire(game, weapon_state, target)


def init(game):
    """Initialize weapon state on game start."""
    # The 9mm Pistol is the first weapon and is available from the start.
    game.weapons = [{"type": "pistol", "last_fired": None}]
