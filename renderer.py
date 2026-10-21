"""Renderer module — camera, sprite blits, screen shake.

Scaffold: minimal stub. Full implementation in the renderer ticket.
"""
import config


def update(game):
    """Update renderer state. Called each frame."""
    # Scaffold: no-op. Rendering added in the renderer ticket.
    pass


def init(game):
    """Initialize renderer state."""
    game.renderer = {
        "camera_x": 0.0,
        "camera_y": 0.0,
        "shake_timer": 0.0,
    }
