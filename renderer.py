"""Renderer module — camera, sprite blits, screen shake.

T10: the screen-shake timer decays each frame (triggered by the boss
telegraph and other big hits).
"""
import config


def update(game, dt=1 / 60.0):
    """Update renderer state. Called each frame."""
    if game.renderer["shake_timer"] > 0:
        game.renderer["shake_timer"] = max(0.0, game.renderer["shake_timer"] - dt)


def init(game):
    """Initialize renderer state."""
    game.renderer = {
        "camera_x": 0.0,
        "camera_y": 0.0,
        "shake_timer": 0.0,
    }
