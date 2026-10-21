"""Player module — movement, HP, i-frames.

Scaffold: minimal stub. Full implementation in the player ticket.
"""
import config


def update(game):
    """Update player state. Called each frame during a run."""
    # Scaffold: no-op. Player movement added in the player ticket.
    pass


def init(game):
    """Initialize player state on game start."""
    game.player = {
        "x": config.DISPLAY["width"] / 2,
        "y": config.DISPLAY["height"] / 2,
        "vx": 0.0,
        "vy": 0.0,
        "hp": config.PLAYER["max_hp"],
        "invuln_timer": 0.0,
    }
