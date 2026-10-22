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
    """Fire the weapon at the target, dispatched on the config `type` field."""
    cfg = config.WEAPON["types"][weapon_state["type"]]
    p = game.player
    dx = target["x"] - p["x"]
    dy = target["y"] - p["y"]
    length = math.hypot(dx, dy)
    if length == 0:
        dx, dy = 1.0, 0.0
        length = 1.0
    weapon_state["last_fired"] = game.run_time
    if cfg["type"] == "whirlwind":
        _fire_whirlwind(game, cfg)
    else:
        _spawn_projectile(game, weapon_state["type"], cfg, dx, dy, length)


def _spawn_projectile(game, weapon_name, cfg, dx, dy, length):
    """Spawn a projectile toward the target; arcing types get an arc field."""
    p = game.player
    proj = {
        "x": p["x"],
        "y": p["y"],
        "vx": dx / length * cfg["bullet_speed"],
        "vy": dy / length * cfg["bullet_speed"],
        "damage": cfg["damage"],
        "weapon": weapon_name,
    }
    if cfg["type"] in ("throw", "flare"):
        proj["arc"] = cfg["arc"]
        proj["arc_vy"] = -cfg["arc"] / max(length / cfg["bullet_speed"], 1e-6)
    if cfg["type"] == "flare":
        proj["aoe_radius"] = cfg["aoe_radius"]
    game.projectiles.append(proj)


def _fire_whirlwind(game, cfg):
    """Whirlwind: instant area damage to every zombie within the radius."""
    p = game.player
    radius = cfg["whirlwind_radius"]
    for z in list(game.zombies):
        if math.hypot(z["x"] - p["x"], z["y"] - p["y"]) <= radius:
            z["hp"] -= cfg["damage"]
            if z["hp"] <= 0:
                game.zombies.remove(z)


def update(game, dt=1 / 60.0):
    """Update weapon state. Called each frame during a run."""
    for weapon_state in game.weapons:
        cfg = config.WEAPON["types"][weapon_state["type"]]
        if not should_fire(weapon_state["last_fired"], game.run_time, cfg["fire_rate"]):
            continue
        target = nearest_zombie((game.player["x"], game.player["y"]), game.zombies)
        if target is None:
            continue
        if math.hypot(target["x"] - game.player["x"],
                      target["y"] - game.player["y"]) > cfg["range"]:
            continue
        _fire(game, weapon_state, target)


def init(game):
    """Initialize weapon state on game start.

    All 5 v1 weapons are available from the start, each with its own
    independent cooldown.
    """
    game.weapons = [{"type": name, "last_fired": None}
                    for name in config.WEAPON["types"]]
