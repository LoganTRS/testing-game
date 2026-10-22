"""SFX module — sound effects for hit, kill, level-up, gem pickup, boss roar.

T13: SFX only (no music in v1). File paths are config-driven (config.SFX).
Missing files are silently skipped so the game runs without audio assets.
Headless mode is a no-op (no audio output).
"""
import os

import config


def _sfx_path(name):
    """Resolve the SFX file path for `name` relative to the project root."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        config.SFX[name])


def play(game, name):
    """Play the SFX for `name` (hit, kill, level_up, gem_pickup, boss_roar).

    No-op in headless mode or when the file is missing.
    """
    if game.headless:
        return
    path = _sfx_path(name)
    if not os.path.exists(path):
        return
    import pygame
    try:
        sound = pygame.mixer.Sound(path)
        sound.play()
    except Exception:
        pass


def init(game):
    """Initialize SFX state. Called on game construction."""
    game.sfx = {"enabled": not game.headless}
