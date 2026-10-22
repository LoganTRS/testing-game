"""XP module — gem accumulation, level-up math.

T6: XP gems — kill drops gem, magnet pickup, pure XP math.
"""
import math

import config


def xp_total(gem_count):
    """Pure XP math: given a gem count and config, return the XP total."""
    return gem_count * config.XP["gem_value"]


def update(game, dt=1 / 60.0):
    """Update XP state. Called each frame during a run."""
    _magnet_pickup(game, dt)


def _magnet_pickup(game, dt):
    """Pull gems within the magnet radius toward the player; collect on contact."""
    p = game.player
    radius = config.XP["gem_magnet_radius"]
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


def init(game):
    """Initialize XP state on game start."""
    game.xp = {
        "level": 1,
        "current": 0,
        "gems": [],
    }
