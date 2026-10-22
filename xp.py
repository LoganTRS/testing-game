"""XP module — gem accumulation, level-up math.

T6: XP gems — kill drops gem, magnet pickup, pure XP math.
"""
import math

import config
import sfx
import upgrade


def xp_total(gem_count):
    """Pure XP math: given a gem count and config, return the XP total."""
    return gem_count * config.XP["gem_value"]


def xp_to_next_level(level):
    """Pure XP math: XP needed to go from `level` to `level + 1`.

    Linear curve: level * xp_per_level (config values).
    """
    return level * config.XP["xp_per_level"]


def level_for_xp(xp_amount):
    """Pure XP math: given a total XP amount and config, return the level.

    Linear curve to max_level (config values); caps at max_level.
    """
    level = 1
    max_level = config.XP["max_level"]
    while level < max_level and xp_amount >= xp_to_next_level(level):
        xp_amount -= xp_to_next_level(level)
        level += 1
    return level


def level_ups_pending(xp_amount, current_level=1):
    """Pure XP math: how many level-ups fire from `current_level` at this XP total.

    Caps at max_level (no level-ups past max_level).
    """
    return max(0, min(level_for_xp(xp_amount), config.XP["max_level"]) - current_level)


def update(game, dt=1 / 60.0):
    """Update XP state. Called each frame during a run."""
    _magnet_pickup(game, dt)
    _check_level_up(game)


def _check_level_up(game):
    """Fire the level-up beat when the XP crosses the next threshold.

    Batched level-ups (e.g. a boss gem dump) open the overlay once with
    `picks_left` picks; the level advances one per pick.
    """
    if game.state != "playing":
        return
    pending = level_ups_pending(game.xp["current"], game.xp["level"])
    if pending <= 0:
        return
    game.state = "level_up"
    game.upgrade["active"] = True
    game.upgrade["picks_left"] = pending
    game.upgrade["rerolls_left"] = config.UPGRADE["rerolls"]
    game.upgrade["picked"] = None
    game.upgrade["options"] = upgrade.roll_options(
        upgrade.option_pool(), game.rng)
    sfx.play(game, "level_up")


def _magnet_pickup(game, dt):
    """Pull gems within the magnet radius toward the player; collect on contact."""
    p = game.player
    # T12: +magnet radius passive (config per_level, applied each frame).
    radius = config.XP["gem_magnet_radius"] + \
        config.UPGRADE["passives"]["magnet_radius"]["per_level"] \
        * p["passives"]["magnet_radius"]
    pickup = config.XP["gem_pickup_radius"]
    speed = config.XP["gem_magnet_speed"]
    gems = game.xp["gems"]
    collected = 0
    for gem in list(gems):
        dx = p["x"] - gem["x"]
        dy = p["y"] - gem["y"]
        length = math.hypot(dx, dy)
        if length <= pickup:
            gems.remove(gem)
            collected += 1
            continue
        if length <= radius:
            gem["x"] += dx / length * speed * dt
            gem["y"] += dy / length * speed * dt
    if collected:
        game.xp["current"] += xp_total(collected)
        sfx.play(game, "gem_pickup")


def init(game):
    """Initialize XP state on game start."""
    game.xp = {
        "level": 1,
        "current": 0,
        "gems": [],
    }
