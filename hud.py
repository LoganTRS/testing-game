"""HUD module — HP bar, XP level, timer, kill count, item icons.

Scaffold: minimal stub. Full implementation in the HUD ticket.
"""
import config


def update(game):
    """Update HUD state. Called each frame during a run."""
    # Scaffold: no-op. HUD rendering added in the HUD ticket.
    pass


def init(game):
    """Initialize HUD state on game start."""
    game.hud = {
        "kills": 0,
    }
