"""Player module — movement, HP, i-frames.

8-directional movement (WASD + arrows, normalized diagonals), speed from
config, cosmetic facing toward the nearest zombie (falls back to the
last-move direction when no zombie exists).
"""
import math

import pygame

import config


def update(game, dt=1 / 60.0):
    """Update player state. Called each frame during a run."""
    p = game.player
    keys = pygame.key.get_pressed()

    dx = (1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0) - \
         (1 if keys[pygame.K_a] or keys[pygame.K_LEFT] else 0)
    dy = (1 if keys[pygame.K_s] or keys[pygame.K_DOWN] else 0) - \
         (1 if keys[pygame.K_w] or keys[pygame.K_UP] else 0)

    if dx or dy:
        length = math.hypot(dx, dy)
        speed = config.PLAYER["speed"]
        p["x"] += dx / length * speed * dt
        p["y"] += dy / length * speed * dt
        p["facing"] = (dx / length, dy / length)

    # Cosmetic: face the nearest zombie when one exists.
    if game.zombies:
        nearest = min(game.zombies,
                      key=lambda z: (z["x"] - p["x"]) ** 2 + (z["y"] - p["y"]) ** 2)
        fx = nearest["x"] - p["x"]
        fy = nearest["y"] - p["y"]
        length = math.hypot(fx, fy)
        if length > 0:
            p["facing"] = (fx / length, fy / length)


def init(game):
    """Initialize player state on game start."""
    game.player = {
        "x": config.DISPLAY["width"] / 2,
        "y": config.DISPLAY["height"] / 2,
        "vx": 0.0,
        "vy": 0.0,
        "hp": config.PLAYER["max_hp"],
        "invuln_timer": 0.0,
        "facing": (1.0, 0.0),
    }
