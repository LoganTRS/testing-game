"""Zombie module — spawning, AI, contact damage.

T3: walker zombie — seek-the-player AI, contact damage with a short
i-frame window. T6: zombie death drops XP gems. T9: continuous spawning
from a ring just outside the camera, super-linear rate ramp, 1000-zombie
hard cap, and a type mix that shifts over the 20-minute run. All stats
from config.
"""
import math

import config

# Stub gem drop counts per zombie type (elite/boss drop a handful;
# the real drop wiring comes in T11).
_GEM_DROPS = {
    "elite": 5,
    "boss": 10,
}


def spawn_rate_at(elapsed, duration, live_count=0, boss_alive=False):
    """Spawn rate (zombies/second) at `elapsed` seconds into a run.

    rate(t) = base_rate + ramp_rate * (t / duration) ** exponent,
    clamped to 0 once the live zombie count reaches the hard cap.
    While the boss is alive (T10), the rate is the reduced config value.
    """
    if live_count >= config.ZOMBIE["max_count"]:
        return 0.0
    if boss_alive:
        return config.BOSS["reduced_spawn_rate"]
    t = min(max(elapsed, 0.0), duration)
    s = config.SPAWN
    return s["base_rate"] + s["ramp_rate"] * (t / duration) ** s["exponent"]


def type_mix_at(elapsed, duration):
    """Normalized zombie type mix at `elapsed` seconds into a run.

    Each type's weight is base + peak * exp(-((t - peak_time) / width) ** 2);
    the weights are normalized to sum to 1.
    """
    t = min(max(elapsed, 0.0), duration)
    weights = {}
    for ztype, m in config.SPAWN["mix"].items():
        d = (t - m["peak_time"]) / m["width"]
        weights[ztype] = m["base"] + m["peak"] * math.exp(-d * d)
    total = sum(weights.values())
    return {ztype: w / total for ztype, w in weights.items()}


def _spawn_zombie(game, x, y, ztype):
    """Create a zombie of the given type at (x, y) and add it to the game."""
    cfg = config.ZOMBIE["types"][ztype]
    game.zombies.append({
        "x": x,
        "y": y,
        "vx": 0.0,
        "vy": 0.0,
        "hp": cfg["hp"],
        "type": ztype,
    })


def _boss_alive(game):
    """T10: True if the boss is currently alive."""
    return any(z["type"] == "boss" for z in game.zombies)


def _spawn_boss(game):
    """T10: spawn the boss exactly once, at the timer end, on top of the
    horde, with a telegraph (banner + screen shake)."""
    if game.run_time < config.BOSS["spawn_time"]:
        return
    if _boss_alive(game) or game._boss_spawned:
        return
    game._boss_spawned = True
    _spawn_zombie(game, config.DISPLAY["width"] / 2,
                  config.DISPLAY["height"] / 2, "boss")
    # Telegraph: banner + screen shake.
    game.hud["boss_banner_timer"] = config.BOSS["banner_duration"]
    game.renderer["shake_timer"] = config.BOSS["shake_duration"]


def _continuous_spawn(game, dt):
    """Accumulator-based continuous spawning from a ring just outside the camera.

    Each frame, the spawn accumulator is advanced by rate * dt. When the
    accumulator reaches 1.0, a zombie is spawned (type chosen from the
    current mix) and the accumulator is decremented. The 1000-zombie hard
    cap is enforced: no new zombies spawn once the cap is reached.
    T10: while the boss is alive, the rate is the reduced config value.
    """
    duration = config.RUN["duration_seconds"]
    cap = config.ZOMBIE["max_count"]
    ring = config.ZOMBIE["spawn_ring_radius"]
    w = config.DISPLAY["width"]
    h = config.DISPLAY["height"]

    if len(game.zombies) >= cap:
        return

    rate = spawn_rate_at(game.run_time, duration,
                         live_count=len(game.zombies),
                         boss_alive=_boss_alive(game))
    game._spawn_accumulator += rate * dt

    while game._spawn_accumulator >= 1.0 and len(game.zombies) < cap:
        game._spawn_accumulator -= 1.0
        # Pick a type from the current mix.
        mix = type_mix_at(game.run_time, duration)
        r = game.rng.random()
        cumulative = 0.0
        chosen = "walker"
        for ztype, weight in mix.items():
            cumulative += weight
            if r <= cumulative:
                chosen = ztype
                break
        # Spawn on the ring at a random angle.
        angle = game.rng.uniform(0.0, 2.0 * math.pi)
        x = w / 2 + ring * math.cos(angle)
        y = h / 2 + ring * math.sin(angle)
        _spawn_zombie(game, x, y, chosen)


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
    """Remove dead zombies, drop XP gems at their position, and count the kill.

    T10: defeating the boss ends the run with a win.
    """
    for z in list(game.zombies):
        if z["hp"] <= 0:
            game.zombies.remove(z)
            game.hud["kills"] += 1
            for _ in range(_GEM_DROPS.get(z["type"], 1)):
                game.xp["gems"].append({"x": z["x"], "y": z["y"],
                                        "vx": 0.0, "vy": 0.0})
            if z["type"] == "boss":
                game.state = "game_over"
                game.hud["won"] = True


def update(game, dt=1 / 60.0):
    """Update zombie state. Called each frame during a run."""
    _spawn_boss(game)
    _continuous_spawn(game, dt)
    _seek_player(game, dt)
    _contact_damage(game, dt)
    _kill_drops(game)
    # T10: the timer hitting 0:00 ends the run with a win.
    if game.state == "playing" and game.run_time >= config.RUN["duration_seconds"]:
        game.state = "game_over"
        game.hud["won"] = True


def init(game):
    """Initialize zombie state on game start."""
    game.zombies = []
    game._spawn_accumulator = 0.0
    game._boss_spawned = False
