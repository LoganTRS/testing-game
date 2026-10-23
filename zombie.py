"""Zombie module — spawning, AI, contact damage.

T3: walker zombie — seek-the-player AI, contact damage with a short
i-frame window. T6: zombie death drops XP gems. T9: continuous spawning
from a ring just outside the camera, super-linear rate ramp, 1000-zombie
hard cap, and a type mix that shifts over the 20-minute run. All stats
from config.
"""
import math

import config
import sfx

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


def decay_stage(z):
    """T11: the decay stage (0..decay_stages-1) for a zombie.

    Multi-stage decay: the sprite darkens through the stages as HP drops,
    so the horde's health reads at a glance. Stage 0 is full health; the
    highest stage is just below death. Pure function of the zombie's HP and
    the config.
    """
    stages = config.ZOMBIE["decay_stages"]
    max_hp = config.ZOMBIE["types"][z["type"]]["hp"]
    if max_hp <= 0:
        return 0
    fraction = 1.0 - (z["hp"] / max_hp)
    if fraction <= 0.0:
        return 0
    if fraction >= 1.0:
        return stages - 1
    return min(int(fraction * stages), stages - 1)


def decay_color(base, stage):
    """T11: the sprite color for a decay stage.

    The base color is darkened in equal steps, one per stage. Stage 0 is the
    untouched base color; higher stages are progressively darker. Pure
    function of the base color and the stage.
    """
    max_stage = config.ZOMBIE["decay_stages"] - 1
    if stage <= 0:
        return tuple(base)
    t = stage / max_stage
    return tuple(int(c * (1.0 - t)) for c in base)


def death_scale(z):
    """T11: the death-sprite scale (1.0 → 0.0) for a dying zombie.

    The sprite shrinks to nothing as the death timer counts down. A
    non-dying zombie, or one whose timer has not started, scales at 1.0.
    Pure function of the zombie's death state and the config.
    """
    if not z.get("dying"):
        return 1.0
    duration = config.ZOMBIE["death_animation"]
    if duration <= 0.0:
        return 0.0
    return max(0.0, z["death_timer"] / duration)


def _horde_count(game):
    """T11: the number of regular horde zombies (not the boss or the elite).

    The 1000-zombie cap is the horde cap; the boss (T10) and the elite (T11)
    spawn "on top of the horde" as distinct peak-threat entities and do not
    count toward it.
    """
    return sum(1 for z in game.zombies if z["type"] not in ("boss", "elite"))


def _spawn_zombie(game, x, y, ztype):
    """Create a zombie of the given type at (x, y) and add it to the game.

    Returns the new zombie dict.
    """
    cfg = config.ZOMBIE["types"][ztype]
    z = {
        "x": x,
        "y": y,
        "vx": 0.0,
        "vy": 0.0,
        "hp": cfg["hp"],
        "type": ztype,
    }
    game.zombies.append(z)
    return z


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
    # Telegraph: banner + screen shake + boss roar SFX.
    game.hud["boss_banner_timer"] = config.BOSS["banner_duration"]
    game.renderer["shake_timer"] = config.BOSS["shake_duration"]
    sfx.play(game, "boss_roar")


def _elite_alive(game):
    """T11: True if the elite is currently alive."""
    return any(z["type"] == "elite" for z in game.zombies)


def _spawn_elite(game):
    """T11: spawn the elite exactly once, at its run-end time, distinct from
    the boss, with a telegraph (banner + screen shake)."""
    if game.run_time < config.ELITE["spawn_time"]:
        return
    if _elite_alive(game):
        return
    # Spawn on the ring just outside the camera, like a normal horde member,
    # so it closes in on the player instead of spawning on top of them.
    ring = config.ZOMBIE["spawn_ring_radius"]
    x = config.DISPLAY["width"] / 2 + ring
    y = config.DISPLAY["height"] / 2
    _spawn_zombie(game, x, y, "elite")
    # Telegraph: banner + screen shake.
    game.hud["elite_banner_timer"] = config.ELITE["banner_duration"]
    game.renderer["shake_timer"] = config.ELITE["shake_duration"]
    sfx.play(game, "boss_roar")


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

    # The 1000-cap is the regular-horde cap. The boss (T10) and the elite
    # (T11) spawn "on top of the horde" and are distinct peak-threat entities,
    # so they don't count toward it.
    horde = _horde_count(game)
    if horde >= cap:
        return

    rate = spawn_rate_at(game.run_time, duration,
                         live_count=horde,
                         boss_alive=_boss_alive(game))
    game._spawn_accumulator += rate * dt

    while game._spawn_accumulator >= 1.0 and _horde_count(game) < cap:
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
    """Move each living zombie toward the player at its config speed.

    T11: a dying zombie (playing its death-sprite animation) no longer seeks.
    """
    p = game.player
    for z in game.zombies:
        if z.get("dying"):
            continue
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
    """Deal contact damage to the player, honoring the i-frame window.

    T11: every zombie type (walker, runner, brute, elite, boss) shares this
    model; per-type damage and the i-frame window come from the type's config
    dict. Types that omit the fields fall back to the player's config defaults.
    """
    p = game.player
    if p["invuln_timer"] > 0:
        p["invuln_timer"] = max(0.0, p["invuln_timer"] - dt)
        return
    for z in game.zombies:
        if z.get("dying"):
            continue
        if z["x"] == p["x"] and z["y"] == p["y"]:
            cfg = config.ZOMBIE["types"][z["type"]]
            p["hp"] -= cfg.get(
                "contact_damage", config.PLAYER["contact_damage"])
            p["invuln_timer"] = cfg.get(
                "i_frame_duration", config.PLAYER["invuln_time"])
            sfx.play(game, "hit")
            break


def _kill_drops(game):
    """Remove dead zombies, drop XP gems at their position, and count the kill.

    T10: defeating the boss ends the run with a win.
    """
    for z in list(game.zombies):
        if z["hp"] <= 0:
            game.zombies.remove(z)
            game.hud["kills"] += 1
            sfx.play(game, "kill")
            for _ in range(_GEM_DROPS.get(z["type"], 1)):
                game.xp["gems"].append({"x": z["x"], "y": z["y"],
                                        "vx": 0.0, "vy": 0.0})
            if z["type"] == "boss":
                game.state = "game_over"
                game.hud["won"] = True


def _begin_death(z, game):
    """T11: start the death-sprite animation on `z` (no-op if disabled).

    Called when a lethal hit drops a zombie's HP to 0. When the death-sprite
    animation is enabled (config ZOMBIE["death_animation"] > 0), the zombie is
    marked dying with its full death timer; it then plays its shrinking sprite
    via `_death_animation` instead of being removed immediately. When the
    animation is disabled (the default), the zombie is left for
    `zombie._kill_drops` to remove on the next update (legacy behavior).
    """
    if game._death_animation_enabled and z["hp"] <= 0 and not z.get("dying"):
        z["dying"] = True
        z["death_timer"] = config.ZOMBIE["death_animation"]


def _death_animation(game, dt):
    """T11: advance the death-sprite animation for dying zombies.

    When the death-sprite animation is enabled (config
    ZOMBIE["death_animation"] > 0), a zombie whose HP drops to 0 (via a
    projectile hit) begins a short death sprite instead of being removed
    immediately: it plays a shrinking sprite (rendered via `death_scale`) for
    `death_animation` seconds, during which it neither seeks nor deals contact
    damage. When the timer expires, it is removed and its XP gems are dropped.
    With the animation disabled (the default), this is a no-op and deaths are
    handled by `_kill_drops` as before.
    """
    if not game._death_animation_enabled:
        return
    duration = config.ZOMBIE["death_animation"]
    for z in list(game.zombies):
        if not z.get("dying"):
            continue
        z["death_timer"] = max(0.0, z["death_timer"] - dt)
        if z["death_timer"] <= 0.0:
            game.zombies.remove(z)
            game.hud["kills"] += 1
            sfx.play(game, "kill")
            for _ in range(config.ZOMBIE["types"][z["type"]]["xp_drop"]):
                game.xp["gems"].append({"x": z["x"], "y": z["y"],
                                        "vx": 0.0, "vy": 0.0})
            if z["type"] == "boss":
                game.state = "game_over"
                game.hud["won"] = True


def update(game, dt=1 / 60.0):
    """Update zombie state. Called each frame during a run."""
    _spawn_elite(game)
    _spawn_boss(game)
    _continuous_spawn(game, dt)
    _seek_player(game, dt)
    _contact_damage(game, dt)
    _death_animation(game, dt)
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
    # T11: death-sprite animation is opt-in (enabled via config
    # ZOMBIE["death_animation"] > 0). When 0, deaths remove instantly.
    game._death_animation_enabled = config.ZOMBIE["death_animation"] > 0
