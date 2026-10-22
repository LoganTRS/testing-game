"""Zombie module — spawning, AI, contact damage.

T3: walker zombie — stub spawn (fixed count), seek-the-player AI,
contact damage with a short i-frame window. All stats from config.
T6: zombie death drops XP gems (1 for normal types, a handful for
elite/boss — stub, wired in T11).
"""
import math

import config

# Stub gem drop counts per zombie type (elite/boss drop a handful;
# the real drop wiring comes in T11).
_GEM_DROPS = {
    "elite": 5,
    "boss": 10,
}


def spawn_walker(game, x, y):
    """Create a walker zombie at (x, y) and add it to the game."""
    cfg = config.ZOMBIE["types"]["walker"]
    game.zombies.append({
        "x": x,
        "y": y,
        "vx": 0.0,
        "vy": 0.0,
        "hp": cfg["hp"],
        "type": "walker",
    })


def _spawn_stub(game):
    """Stub spawning: a small fixed count of walkers on the spawn ring.

    The real continuous spawn curve comes in T9.
    """
    count = config.ZOMBIE["initial_spawn_count"]
    ring = config.ZOMBIE["spawn_ring_radius"]
    w = config.DISPLAY["width"]
    h = config.DISPLAY["height"]
    for i in range(count):
        angle = game.rng.uniform(0.0, 2.0 * math.pi)
        x = w / 2 + ring * math.cos(angle)
        y = h / 2 + ring * math.sin(angle)
        spawn_walker(game, x, y)


def _seek_player(game, dt):
    """Move each zombie toward the player at its config speed."""
    p = game.player
    for z in game.zombies:
        cfg = config.ZOMBIE["types"][z["type"]]
        dx = p["x"] - z["x"]
        dy = p["y"] - z["y"]
        length = math.hypot(dx, dy)
        if length == 0:
            continue
        speed = cfg["speed"]
        z["x"] += dx / length * speed * dt
        z["y"] += dy / length * speed * dt


def _contact_damage(game, dt):
    """Deal contact damage to the player, honoring the i-frame window."""
    p = game.player
    if p["invuln_timer"] > 0:
        p["invuln_timer"] = max(0.0, p["invuln_timer"] - dt)
        return
    for z in game.zombies:
        if z["x"] == p["x"] and z["y"] == p["y"]:
            cfg = config.ZOMBIE["types"][z["type"]]
            p["hp"] -= cfg["contact_damage"]
            p["invuln_timer"] = cfg["i_frame_duration"]
            break


def _kill_drops(game):
    """Remove dead zombies and drop XP gems at their position."""
    for z in list(game.zombies):
        if z["hp"] <= 0:
            game.zombies.remove(z)
            for _ in range(_GEM_DROPS.get(z["type"], 1)):
                game.xp["gems"].append({"x": z["x"], "y": z["y"],
                                        "vx": 0.0, "vy": 0.0})


def update(game, dt=1 / 60.0):
    """Update zombie state. Called each frame during a run."""
    _seek_player(game, dt)
    _contact_damage(game, dt)
    _kill_drops(game)


def init(game):
    """Initialize zombie state on game start."""
    game.zombies = []
    _spawn_stub(game)
