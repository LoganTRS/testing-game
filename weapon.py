"""Weapon module — auto-fire, targeting, cooldowns.

T4: 9mm Pistol — auto-fires at the nearest zombie on its cooldown.
T5: All 5 weapons — each with its own type dispatch and cooldown.
T12: Passive effects (damage, cooldown) + weapon evolutions.
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


def can_evolve(weapon_name, weapon_level, passive_levels):
    """T12: Pure function — True if the weapon and its paired passive
    are both at max level (config values).
    """
    evo = config.WEAPON["evolutions"].get(weapon_name)
    if evo is None:
        return False
    if weapon_level < config.WEAPON["max_level"]:
        return False
    paired = evo["paired_passive"]
    return passive_levels.get(paired, 0) >= config.UPGRADE["passives"][paired]["max_level"]


def _passive_multiplier(game, passive_name):
    """T12: 1 + per_level * passive level, from the player's state dict."""
    return 1 + config.UPGRADE["passives"][passive_name]["per_level"] \
        * game.player["passives"][passive_name]


def _cooldown_multiplier(game):
    """T12: 1 - per_level * passive level (decreases fire rate)."""
    return 1 - config.UPGRADE["passives"]["cooldown"]["per_level"] \
        * game.player["passives"]["cooldown"]


def _get_weapon_cfg(weapon_state):
    """Return the effective weapon config (base or evolved).

    T12: if the weapon is evolved, merge evolved_stats over the base
    config so evolved weapons use their upgraded stats.
    """
    base = dict(config.WEAPON["types"][weapon_state["type"]])
    if weapon_state.get("evolved"):
        evo = config.WEAPON["evolutions"][weapon_state["type"]]
        base.update(evo["evolved_stats"])
    return base


def _fire(game, weapon_state, target):
    """Fire the weapon at the target, dispatched on the config `type` field."""
    cfg = _get_weapon_cfg(weapon_state)
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
        # T12: +damage passive (config per_level, applied each frame).
        "damage": cfg["damage"] * _passive_multiplier(game, "damage"),
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
    damage = cfg["damage"] * _passive_multiplier(game, "damage")
    for z in list(game.zombies):
        if math.hypot(z["x"] - p["x"], z["y"] - p["y"]) <= radius:
            z["hp"] -= damage
            if z["hp"] <= 0:
                game.zombies.remove(z)


def update(game, dt=1 / 60.0):
    """Update weapon state. Called each frame during a run."""
    # T12: -cooldown passive (config per_level, applied each frame).
    cooldown_mult = _cooldown_multiplier(game)
    for weapon_state in game.weapons:
        cfg = _get_weapon_cfg(weapon_state)
        if not should_fire(weapon_state["last_fired"], game.run_time,
                           cfg["fire_rate"] * cooldown_mult):
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
    independent cooldown. T12: each weapon tracks a level (starts at 1)
    and an evolved flag (starts False).
    """
    game.weapons = [
        {"type": name, "last_fired": None, "level": 1, "evolved": False}
        for name in config.WEAPON["types"]
    ]
