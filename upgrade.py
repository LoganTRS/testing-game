"""Upgrade module — level-up picks, rerolls, categories.

Scaffold: minimal stub. Full implementation in the upgrade ticket.
"""
import config


def update(game):
    """Update upgrade state. Called each frame during a run."""
    # Scaffold: no-op. Upgrade picks added in the upgrade ticket.
    pass


def init(game):
    """Initialize upgrade state on game start."""
    game.upgrade = {
        "active": False,
        "options": [],
        "rerolls_left": config.UPGRADE["rerolls"],
    }
