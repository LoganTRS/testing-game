"""Upgrade module — level-up picks, rerolls, categories.

T7: level-up pause + 3-card pick + 1 reroll.
"""
import config

# Option pool: 4 categories (config-driven). Real effects wired in T12;
# the pool is stubbed for the pick UI.
_POOL = [
    # weapon level
    {"category": "weapon_level", "icon": "pistol", "name": "9mm Pistol Lv Up",
     "description": "Level up your 9mm Pistol."},
    {"category": "weapon_level", "icon": "knife", "name": "Hunting Knife Lv Up",
     "description": "Level up your Hunting Knife."},
    {"category": "weapon_level", "icon": "baton", "name": "Baton Whirlwind Lv Up",
     "description": "Level up your Baton Whirlwind."},
    {"category": "weapon_level", "icon": "sniper", "name": "Sniper Rifle Lv Up",
     "description": "Level up your Sniper Rifle."},
    {"category": "weapon_level", "icon": "flare", "name": "Flare Lv Up",
     "description": "Level up your Flare."},
    # new weapon
    {"category": "new_weapon", "icon": "pistol", "name": "9mm Pistol",
     "description": "Add the 9mm Pistol to your loadout."},
    {"category": "new_weapon", "icon": "knife", "name": "Hunting Knife",
     "description": "Add the Hunting Knife to your loadout."},
    {"category": "new_weapon", "icon": "baton", "name": "Baton Whirlwind",
     "description": "Add the Baton Whirlwind to your loadout."},
    {"category": "new_weapon", "icon": "sniper", "name": "Sniper Rifle",
     "description": "Add the Sniper Rifle to your loadout."},
    {"category": "new_weapon", "icon": "flare", "name": "Flare",
     "description": "Add the Flare to your loadout."},
    # passive
    {"category": "passive", "icon": "damage", "name": "Damage Up",
     "description": "+10% weapon damage."},
    {"category": "passive", "icon": "move_speed", "name": "Move Speed Up",
     "description": "+10% move speed."},
    {"category": "passive", "icon": "magnet_radius", "name": "Magnet Radius Up",
     "description": "+20px gem magnet radius."},
    {"category": "passive", "icon": "cooldown", "name": "Cooldown Down",
     "description": "-5% weapon cooldown."},
    # evolved weapon (stubbed for the pick UI; real effects wired in T12)
    {"category": "evolved_weapon", "icon": "pistol", "name": "Evolved: 9mm Pistol",
     "description": "Evolve your 9mm Pistol (stub)."},
    {"category": "evolved_weapon", "icon": "knife", "name": "Evolved: Hunting Knife",
     "description": "Evolve your Hunting Knife (stub)."},
    {"category": "evolved_weapon", "icon": "baton", "name": "Evolved: Baton Whirlwind",
     "description": "Evolve your Baton Whirlwind (stub)."},
    {"category": "evolved_weapon", "icon": "sniper", "name": "Evolved: Sniper Rifle",
     "description": "Evolve your Sniper Rifle (stub)."},
    {"category": "evolved_weapon", "icon": "flare", "name": "Evolved: Flare",
     "description": "Evolve your Flare (stub)."},
]


def option_pool():
    """The full upgrade option pool (all 4 categories)."""
    return list(_POOL)


def roll_options(pool, rng):
    """Sample `options_per_levelup` distinct options from the pool (seeded rng)."""
    return rng.sample(pool, config.UPGRADE["options_per_levelup"])


def picks_for_level(level):
    """How many upgrade picks are offered at `level` (multiple at high levels)."""
    cfg = config.UPGRADE
    if level < cfg["multi_pick_level"]:
        return 1
    extra = (level - cfg["multi_pick_level"]) // cfg["picks_per_extra_level"]
    return min(1 + extra, cfg["max_picks"])


def update(game):
    """Update upgrade state. Called each frame during a run."""
    # Level-up overlay input is handled in Game.handle_event.
    pass


def init(game):
    """Initialize upgrade state on game start."""
    game.upgrade = {
        "active": False,
        "options": [],
        "rerolls_left": config.UPGRADE["rerolls"],
        "picks_left": 0,
    }
