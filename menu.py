"""Menu module — main menu, pause menu, end screen.

Scaffold: main menu with title, Play, Quit.
"""
import config


def update(game):
    """Update menu state. Called each frame when in a menu."""
    # Scaffold: no-op. Menu interaction added here.
    pass


def init(game):
    """Initialize menu state."""
    game.menu = {
        "selected": 0,
        "options": config.MENU["options"],
    }
