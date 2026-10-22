"""Game configuration — all tunables live here as plain dicts/lists.

No ECS. Every module reads its tunables from these dicts.
"""

# --- Display ---
DISPLAY = {
    "width": 1280,
    "height": 720,
    "fps": 60,
    "title": "Zombie Survival",
}

# --- Player ---
PLAYER = {
    "speed": 200.0,          # pixels per second
    "max_hp": 100,
    "invuln_time": 0.5,      # seconds of i-frames after a hit
    "contact_damage": 10,    # damage per zombie contact
}

# --- Zombies ---
ZOMBIE = {
    "max_count": 1000,       # hard cap
    "spawn_ring_radius": 400,  # spawn just outside camera
    "initial_spawn_count": 3,  # stub spawn (real spawn curve comes in T9)
    "types": {
        "walker": {
            "speed": 60.0,
            "hp": 30,
            "color": (100, 200, 100),
            "xp_drop": 1,
            "contact_damage": 10,   # damage dealt on player contact
            "i_frame_duration": 0.5,  # player i-frames after a hit (seconds)
        },
        "runner": {
            "speed": 150.0,
            "hp": 15,
            "color": (200, 200, 100),
            "xp_drop": 1,
        },
        "brute": {
            "speed": 40.0,
            "hp": 120,
            "color": (150, 100, 100),
            "xp_drop": 3,
        },
        "elite": {
            "speed": 80.0,
            "hp": 500,
            "color": (200, 100, 200),
            "xp_drop": 20,
        },
        "boss": {
            "speed": 50.0,
            "hp": 5000,
            "color": (200, 50, 50),
            "xp_drop": 100,
        },
    },
}

# --- Weapons ---
WEAPON = {
    "types": {
        "pistol": {
            "damage": 10,
            "fire_rate": 0.5,   # seconds between shots
            "bullet_speed": 500.0,
            "bullet_count": 1,
        },
        "knife": {
            "damage": 25,
            "fire_rate": 1.0,
            "bullet_speed": 400.0,
            "bullet_count": 1,
        },
        "baton": {
            "damage": 5,
            "fire_rate": 0.3,
            "bullet_speed": 0.0,  # melee, no projectile
            "bullet_count": 0,
        },
        "sniper": {
            "damage": 80,
            "fire_rate": 2.0,
            "bullet_speed": 1200.0,
            "bullet_count": 1,
        },
        "flare": {
            "damage": 3,
            "fire_rate": 0.1,
            "bullet_speed": 300.0,
            "bullet_count": 1,
        },
    },
}

# --- XP / Leveling ---
XP = {
    "gem_magnet_radius": 60.0,
    "gem_magnet_speed": 300.0,  # pixels per second
    "gem_pickup_radius": 10.0,  # collect on contact
    "gem_value": 1,
    "level_curve": "linear",
    "max_level": 30,
    "xp_per_level": 10,  # base XP needed per level (linear: level * xp_per_level)
}

# --- Run ---
RUN = {
    "duration_seconds": 1200,  # 20 minutes
    "seed": 42,                # default RNG seed for determinism
}

# --- HUD ---
HUD = {
    "font_size": 24,
    "hp_bar_width": 200,
    "hp_bar_height": 20,
}

# --- Menu ---
MENU = {
    "title_font_size": 64,
    "option_font_size": 32,
    "options": ["Play", "Quit"],
}

# --- Upgrades ---
UPGRADE = {
    "options_per_levelup": 3,
    "rerolls": 1,
    "categories": ["weapon_level", "new_weapon", "passive", "evolved_weapon"],
    "passives": {
        "damage": {"max_level": 5, "per_level": 0.1},
        "move_speed": {"max_level": 5, "per_level": 0.1},
        "magnet_radius": {"max_level": 5, "per_level": 20.0},
        "cooldown": {"max_level": 5, "per_level": 0.05},
    },
    # Multiple picks at high levels (per the ~level-30 curve).
    "multi_pick_level": 15,   # level at which extra picks start
    "picks_per_extra_level": 15,  # +1 pick every N levels above multi_pick_level
    "max_picks": 3,
    "max_level": 30,          # mirrors XP max_level for the pick curve
}

# --- Items ---
ITEM = {
    "xp_gem": {
        "color": (100, 255, 100),
        "size": 6,
    },
}

# --- Renderer ---
RENDERER = {
    "background_color": (30, 30, 30),
    "camera_shake_magnitude": 5,
    "camera_shake_duration": 0.2,
}
