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
    # T11: multi-stage decay + death-sprite animation (distinct per type via
    # the per-type color). Decay: the sprite darkens through `decay_stages`
    # stages as HP drops (read the horde's health at a glance). Death-sprite:
    # on a lethal hit the zombie plays a shrinking death sprite for
    # `death_animation` seconds before being removed. `death_animation` > 0
    # enables the animated death; 0 removes instantly (the legacy behavior).
    "decay_stages": 4,
    "death_animation": 0.0,
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
            "contact_damage": 8,
            "i_frame_duration": 0.5,
        },
        "brute": {
            "speed": 40.0,
            "hp": 120,
            "color": (150, 100, 100),
            "xp_drop": 3,
            "contact_damage": 20,
            "i_frame_duration": 0.5,
        },
        "elite": {
            "speed": 80.0,
            "hp": 500,
            "color": (200, 100, 200),
            "xp_drop": 20,
            "contact_damage": 20,
            "i_frame_duration": 0.5,
        },
        "boss": {
            "speed": 50.0,
            "hp": 5000,
            "color": (200, 50, 50),
            "xp_drop": 100,
            "contact_damage": 25,
            "i_frame_duration": 0.5,
        },
    },
}

# --- Spawning (T9: continuous rate, super-linear ramp, 1000-cap, type-mix shift) ---
# Rate curve: rate(t) = base + ramp * (t / duration) ** exponent, in zombies/second.
# exponent > 1 makes the ramp slightly super-linear. The rate flattens once the
# live zombie count reaches max_count (hard cap).
# Mix weights: weight of each type at time t is
#   w(t) = base + peak * exp(-((t - peak_time) / width) ** 2)
# normalized over the three types. Tuned at the 3-run sign-off.
SPAWN = {
    "base_rate": 0.5,
    "ramp_rate": 1.5,
    "exponent": 1.5,
    "mix": {
        "walker": {"base": 0.1, "peak": 0.9, "peak_time": 0.0, "width": 300.0},
        "runner": {"base": 0.0, "peak": 0.9, "peak_time": 600.0, "width": 120.0},
        "brute": {"base": 0.0, "peak": 0.9, "peak_time": 1200.0, "width": 120.0},
    },
}

# --- Boss (T10: end-of-run, on top of the horde, telegraphed) ---
# The boss spawns exactly once, at the timer end (20:00 → 0:00), on top of
# the horde: zombie spawning continues at a reduced rate while it is alive.
# The spawn is telegraphed with a banner and a screen shake. Defeating the
# boss (or the timer hitting 0:00) ends the run with a win.
BOSS = {
    "spawn_time": 1200.0,      # seconds into the run (the timer end)
    "reduced_spawn_rate": 0.5,  # zombies/second while the boss is alive
    "banner_text": "THE BOSS HAS ARRIVED",
    "banner_duration": 3.0,     # seconds the banner stays on screen
    "banner_color": (255, 60, 60),
    "banner_font_size": 48,
    "shake_magnitude": 10,      # screen-shake pixels for the telegraph
    "shake_duration": 0.5,      # seconds of screen shake for the telegraph
}

# --- Elite (T11: a single peak-threat moment near the run end) ---
# The Elite zombie appears exactly once near the run end — a distinct
# peak-threat beat BEFORE the boss spawns at the timer end (spec US13: two
# distinct peak-threat moments). Like the boss, its spawn is telegraphed with
# a banner and a screen shake.
ELITE = {
    "spawn_time": 1140.0,      # the 19:00 mark — 1 minute before the boss
    "banner_text": "AN ELITE ZOMBIE APPROACHES",
    "banner_duration": 3.0,     # seconds the banner stays on screen
    "banner_color": (255, 120, 255),
    "banner_font_size": 42,
    "shake_duration": 0.5,      # seconds of screen shake for the telegraph
}

# --- Weapons ---
# Every weapon has a `type` field the weapon module dispatches on:
#   projectile — straight bullet (pistol)
#   throw      — arcing projectile (knife)
#   whirlwind  — melee area damage around the player (baton)
#   sniper     — long-range fast projectile (sniper)
#   flare      — arcing projectile that explodes into an AoE (flare)
WEAPON = {
    "types": {
        "pistol": {
            "type": "projectile",
            "damage": 10,
            "fire_rate": 0.5,   # seconds between shots
            "bullet_speed": 500.0,
            "bullet_count": 1,
            "range": 600.0,
        },
        "knife": {
            "type": "throw",
            "damage": 25,
            "fire_rate": 1.0,
            "bullet_speed": 400.0,
            "bullet_count": 1,
            "range": 400.0,
            "arc": 150.0,       # throw arc height (pixels)
        },
        "baton": {
            "type": "whirlwind",
            "damage": 5,
            "fire_rate": 0.3,
            "bullet_speed": 0.0,  # melee, no projectile
            "bullet_count": 0,
            "range": 80.0,
            "whirlwind_radius": 80.0,  # area around the player
        },
        "sniper": {
            "type": "sniper",
            "damage": 80,
            "fire_rate": 2.0,
            "bullet_speed": 1200.0,
            "bullet_count": 1,
            "range": 1200.0,
        },
        "flare": {
            "type": "flare",
            "damage": 3,
            "fire_rate": 0.1,
            "bullet_speed": 300.0,
            "bullet_count": 1,
            "range": 500.0,
            "arc": 100.0,
            "aoe_radius": 60.0,  # explosion radius on impact
        },
    },
    "max_level": 5,
    # T12: weapon evolutions — unlock when the weapon and its paired
    # passive are both at max level. Evolved stats override the base
    # weapon stats (partial dict; missing keys fall back to base).
    "evolutions": {
        "pistol": {
            "paired_passive": "damage",
            "evolved_name": "Evolved: 9mm Pistol",
            "evolved_stats": {
                "damage": 20,
                "fire_rate": 0.3,
                "bullet_count": 2,
            },
        },
        "knife": {
            "paired_passive": "move_speed",
            "evolved_name": "Evolved: Hunting Knife",
            "evolved_stats": {
                "damage": 40,
                "fire_rate": 0.6,
            },
        },
        "baton": {
            "paired_passive": "magnet_radius",
            "evolved_name": "Evolved: Baton Whirlwind",
            "evolved_stats": {
                "damage": 10,
                "fire_rate": 0.2,
                "whirlwind_radius": 120.0,
            },
        },
        "sniper": {
            "paired_passive": "cooldown",
            "evolved_name": "Evolved: Sniper Rifle",
            "evolved_stats": {
                "damage": 150,
                "fire_rate": 1.0,
            },
        },
        "flare": {
            "paired_passive": "damage",
            "evolved_name": "Evolved: Flare",
            "evolved_stats": {
                "damage": 8,
                "fire_rate": 0.05,
                "aoe_radius": 100.0,
            },
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
    "hp_bar": {
        "x": 16,
        "y": 16,
        "width": 200,
        "height": 20,
        "color": (200, 40, 40),   # remaining-life fill
        "background": (60, 20, 20),  # empty (lost) portion
        "border": (255, 255, 255),
    },
    "timer": {
        "x": 1280 - 16,           # right-aligned (anchor = right edge)
        "y": 16,
        "color": (255, 255, 255),
    },
    "level": {
        "x": 16,
        "y": 44,
        "color": (100, 255, 100),
    },
    "kills": {
        "x": 16,
        "y": 72,
        "color": (255, 200, 100),
    },
    "icons": {
        "x": 16,
        "y": 100,
        "size": 24,
        "gap": 6,
        "weapon_color": (255, 255, 255),
        "passive_color": (120, 180, 255),
    },
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

# --- SFX (T13: hit, kill, level-up, gem pickup, boss roar — no music in v1) ---
# File paths are relative to the project root. Missing files are silently
# skipped (the game still runs without audio).
SFX = {
    "hit": "sfx/hit.wav",
    "kill": "sfx/kill.wav",
    "level_up": "sfx/level_up.wav",
    "gem_pickup": "sfx/gem_pickup.wav",
    "boss_roar": "sfx/boss_roar.wav",
}

# --- End Screen (T13: "You survived X minutes", Play again, Main menu) ---
END_SCREEN = {
    "title_font_size": 48,
    "stat_font_size": 28,
    "option_font_size": 32,
    "title_color": (255, 255, 255),
    "stat_color": (200, 200, 200),
    "best_color": (255, 200, 100),
    "option_color": (200, 200, 200),
    "selected_color": (255, 255, 0),
    "options": ["Play again", "Main menu"],
}

# --- Best Run (T13: single-file persistence) ---
BEST_RUN = {
    "file": "best_run.json",
}
