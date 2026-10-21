"""XP module — gem accumulation, level-up math.

Scaffold: minimal stub. Full implementation in the XP ticket.
"""
import config


def update(game):
    """Update XP state. Called each frame during a run."""
    # Scaffold: no-op. XP gem magnet/level-up added in the XP ticket.
    pass


def init(game):
    """Initialize XP state on game start."""
    game.xp = {
        "level": 1,
        "current": 0,
        "gems": [],
    }
