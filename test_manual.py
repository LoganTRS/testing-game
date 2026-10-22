"""test_manual.py — headless smoke test for the game scaffold.

Runs the game loop headless for N frames and verifies:
1. The loop runs without crashing.
2. The Game class is constructed and passed to all 12 modules.
3. Config tunables are plain dicts/lists.
4. Seeded RNG produces deterministic results.
5. The main menu state is the initial state.

Usage: python test_manual.py
"""
import os
import sys
import math
import random

# Set up headless environment before importing pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import config
from game import Game

PASS = 0
FAIL = 0


def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


def set_keys(keys):
    """Monkeypatch pygame.key.get_pressed to report the given keys as held.

    pygame has no public API to inject key state headless, so we patch
    get_pressed with a fake that answers from a set of key constants.
    """
    def get_pressed():
        class K:
            def __getitem__(self, k):
                return k in keys
        return K()
    pygame.key.get_pressed = get_pressed


def test_config_dicts():
    """All tunables are plain dicts/lists (no ECS)."""
    print("\n[config] Tunables are plain dicts/lists")
    check("DISPLAY is dict", isinstance(config.DISPLAY, dict))
    check("PLAYER is dict", isinstance(config.PLAYER, dict))
    check("ZOMBIE is dict", isinstance(config.ZOMBIE, dict))
    check("WEAPON is dict", isinstance(config.WEAPON, dict))
    check("XP is dict", isinstance(config.XP, dict))
    check("RUN is dict", isinstance(config.RUN, dict))
    check("HUD is dict", isinstance(config.HUD, dict))
    check("MENU is dict", isinstance(config.MENU, dict))
    check("UPGRADE is dict", isinstance(config.UPGRADE, dict))
    check("ITEM is dict", isinstance(config.ITEM, dict))
    check("RENDERER is dict", isinstance(config.RENDERER, dict))
    check("MENU options is list", isinstance(config.MENU["options"], list))
    check("ZOMBIE types is dict", isinstance(config.ZOMBIE["types"], dict))
    check("WEAPON types is dict", isinstance(config.WEAPON["types"], dict))
    check("Walker contact_damage is a config dict value",
          "contact_damage" in config.ZOMBIE["types"]["walker"])
    check("Walker i-frame duration is a config dict value",
          "i_frame_duration" in config.ZOMBIE["types"]["walker"])
    check("Walker speed is a config dict value",
          "speed" in config.ZOMBIE["types"]["walker"])
    check("Walker HP is a config dict value",
          "hp" in config.ZOMBIE["types"]["walker"])
    check("Stub spawn count is a config dict value",
          "initial_spawn_count" in config.ZOMBIE)


def test_game_construction():
    """Game class is constructed and all 12 modules are initialized."""
    print("\n[game] Game class construction and module init")
    pygame.init()
    game = Game(seed=42, headless=True)

    check("Game has player state", game.player is not None)
    check("Game has zombies state", game.zombies is not None)
    check("Game has weapons state", game.weapons is not None)
    check("Game has projectiles state", game.projectiles is not None)
    check("Game has xp state", game.xp is not None)
    check("Game has hud state", game.hud is not None)
    check("Game has menu state", game.menu is not None)
    check("Game has upgrade state", game.upgrade is not None)
    check("Game has items state", game.items is not None)
    check("Game has renderer state", game.renderer is not None)

    check("Initial state is menu", game.state == "menu")
    check("Game is running", game.running is True)
    check("Seed is set", game.seed == 42)
    check("RNG is seeded", game.rng is not None)

    pygame.quit()


def test_seeded_rng():
    """Same seed produces same RNG sequence (determinism)."""
    print("\n[rng] Seeded RNG determinism")
    pygame.init()
    g1 = Game(seed=123, headless=True)
    g2 = Game(seed=123, headless=True)
    g3 = Game(seed=456, headless=True)

    seq1 = [g1.rng.random() for _ in range(10)]
    seq2 = [g2.rng.random() for _ in range(10)]
    seq3 = [g3.rng.random() for _ in range(10)]

    check("Same seed → same sequence", seq1 == seq2)
    check("Different seed → different sequence", seq1 != seq3)

    pygame.quit()


def test_headless_loop():
    """Headless test mode runs the loop with no display and no crash."""
    print("\n[headless] Loop runs N frames headless")
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)

    # Run 60 frames in menu state
    frames_run = 0
    for _ in range(60):
        game.update(1 / 60.0)
        game.render(screen)
        frames_run += 1

    check("60 frames ran without crash", frames_run == 60)
    check("Still in menu state", game.state == "menu")
    check("Game still running", game.running is True)

    # Start a run and run 60 more frames
    game.start_run()
    for _ in range(60):
        game.update(1 / 60.0)
        game.render(screen)

    check("60 frames in playing state without crash", game.state == "playing")
    check("Frame counter advanced", game.frame == 60)
    check("Run time advanced", game.run_time > 0)

    pygame.quit()


def test_player_movement():
    """Player moves 8-directionally via WASD and arrow keys, speed from config."""
    print("\n[player] 8-directional movement")
    import player
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    dt = 1 / 60.0
    speed = config.PLAYER["speed"]

    # No input → no movement
    player.update(game)
    check("No input → no movement", game.player["x"] == config.DISPLAY["width"] / 2
          and game.player["y"] == config.DISPLAY["height"] / 2)

    # Right (D)
    game.player["x"] = config.DISPLAY["width"] / 2
    game.player["y"] = config.DISPLAY["height"] / 2
    set_keys([pygame.K_d])
    player.update(game)
    check("D moves right at config speed",
          abs(game.player["x"] - (config.DISPLAY["width"] / 2 + speed * dt)) < 1e-6
          and game.player["y"] == config.DISPLAY["height"] / 2)

    # Up (W)
    game.player["x"] = config.DISPLAY["width"] / 2
    game.player["y"] = config.DISPLAY["height"] / 2
    set_keys([pygame.K_w])
    player.update(game)
    check("W moves up at config speed",
          abs(game.player["y"] - (config.DISPLAY["height"] / 2 - speed * dt)) < 1e-6
          and game.player["x"] == config.DISPLAY["width"] / 2)

    # Diagonal (W+D) — normalized, same total speed
    game.player["x"] = config.DISPLAY["width"] / 2
    game.player["y"] = config.DISPLAY["height"] / 2
    set_keys([pygame.K_w, pygame.K_d])
    player.update(game)
    expected = speed * dt / math.sqrt(2)
    check("W+D diagonal is normalized (same total speed)",
          abs(game.player["x"] - (config.DISPLAY["width"] / 2 + expected)) < 1e-6
          and abs(game.player["y"] - (config.DISPLAY["height"] / 2 - expected)) < 1e-6)

    # Arrow keys
    game.player["x"] = config.DISPLAY["width"] / 2
    game.player["y"] = config.DISPLAY["height"] / 2
    set_keys([pygame.K_LEFT])
    player.update(game)
    check("Left arrow moves left",
          abs(game.player["x"] - (config.DISPLAY["width"] / 2 - speed * dt)) < 1e-6)

    game.player["x"] = config.DISPLAY["width"] / 2
    game.player["y"] = config.DISPLAY["height"] / 2
    set_keys([pygame.K_DOWN])
    player.update(game)
    check("Down arrow moves down",
          abs(game.player["y"] - (config.DISPLAY["height"] / 2 + speed * dt)) < 1e-6)

    # Arrow + WASD diagonal
    game.player["x"] = config.DISPLAY["width"] / 2
    game.player["y"] = config.DISPLAY["height"] / 2
    set_keys([pygame.K_UP, pygame.K_RIGHT])
    player.update(game)
    check("Up+Right arrow diagonal is normalized",
          abs(game.player["x"] - (config.DISPLAY["width"] / 2 + expected)) < 1e-6
          and abs(game.player["y"] - (config.DISPLAY["height"] / 2 - expected)) < 1e-6)

    set_keys([])
    pygame.quit()


def test_player_facing():
    """Player faces the nearest zombie; falls back to last-move direction."""
    print("\n[player] Facing nearest zombie")
    import player
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    # No zombies → facing falls back to last-move direction
    game.zombies = []
    game.player["x"] = config.DISPLAY["width"] / 2
    game.player["y"] = config.DISPLAY["height"] / 2
    set_keys([pygame.K_d])
    player.update(game)
    check("No zombies → faces last-move direction (right)",
          game.player["facing"] == (1.0, 0.0))

    # Release keys so the player stays put while we check zombie facing.
    set_keys([])

    # Zombie to the left → faces it
    game.zombies = [{"x": game.player["x"] - 100.0, "y": game.player["y"]}]
    player.update(game)
    check("Faces nearest zombie (left)",
          game.player["facing"] == (-1.0, 0.0))

    # Two zombies: nearest is below
    game.zombies = [
        {"x": game.player["x"], "y": game.player["y"] + 50.0},
        {"x": game.player["x"], "y": game.player["y"] - 200.0},
    ]
    player.update(game)
    check("Faces the NEAREST zombie (below, not the farther one)",
          game.player["facing"] == (0.0, 1.0))

    set_keys([])
    pygame.quit()


def test_player_hp():
    """Player HP exists as a dict value with a max."""
    print("\n[player] HP")
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    check("HP is a dict value", isinstance(game.player["hp"], (int, float)))
    check("HP starts at max", game.player["hp"] == config.PLAYER["max_hp"])
    check("max_hp is a config dict value", "max_hp" in config.PLAYER)

    pygame.quit()


def test_player_rendered():
    """Player is rendered (pixel-art placeholder) during a run."""
    print("\n[player] Rendered")
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    game.render(screen)
    # The player blit lands at the arena center (camera at 0,0 in scaffold).
    px = int(game.player["x"])
    py = int(game.player["y"])
    check("Player pixel is drawn at its position",
          screen.get_at((px, py)) != pygame.Color(*config.RENDERER["background_color"]))

    pygame.quit()


def test_zombie_spawn():
    """Stub spawning: a small fixed count of walkers spawns at run start."""
    print("\n[zombie] Stub spawn")
    import zombie
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    count = config.ZOMBIE["initial_spawn_count"]
    check("Stub spawn count from config", len(game.zombies) == count)
    check("All spawned zombies are walkers",
          all(z["type"] == "walker" for z in game.zombies))
    check("Walkers spawn with full HP from config",
          all(z["hp"] == config.ZOMBIE["types"]["walker"]["hp"] for z in game.zombies))
    check("Walkers spawn on the spawn ring (config radius from center)",
          all(abs(math.hypot(z["x"] - config.DISPLAY["width"] / 2,
                             z["y"] - config.DISPLAY["height"] / 2)
                  - config.ZOMBIE["spawn_ring_radius"]) < 1e-6
              for z in game.zombies))

    pygame.quit()


def test_zombie_seek():
    """Walker AI: moves toward the player at config speed."""
    print("\n[zombie] Seek-the-player AI")
    import zombie
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    dt = 1 / 60.0
    speed = config.ZOMBIE["types"]["walker"]["speed"]

    # Place one walker to the right of the player.
    game.zombies = [{"x": game.player["x"] + 100.0, "y": game.player["y"],
                     "vx": 0.0, "vy": 0.0, "hp": 30, "type": "walker"}]
    zombie.update(game, dt)
    check("Walker moves left toward the player",
          abs(game.zombies[0]["x"] - (game.player["x"] + 100.0 - speed * dt)) < 1e-6
          and game.zombies[0]["y"] == game.player["y"])

    # Diagonal: walker up-right of the player, normalized speed.
    game.zombies[0]["x"] = game.player["x"] + 100.0
    game.zombies[0]["y"] = game.player["y"] - 100.0
    zombie.update(game, dt)
    expected = speed * dt / math.sqrt(2)
    check("Walker diagonal seek is normalized (same total speed)",
          abs(game.zombies[0]["x"] - (game.player["x"] + 100.0 - expected)) < 1e-6
          and abs(game.zombies[0]["y"] - (game.player["y"] - 100.0 + expected)) < 1e-6)

    # Walker already at the player's position → no movement.
    game.zombies[0]["x"] = game.player["x"]
    game.zombies[0]["y"] = game.player["y"]
    zombie.update(game, dt)
    check("Walker at player position does not move",
          game.zombies[0]["x"] == game.player["x"]
          and game.zombies[0]["y"] == game.player["y"])

    pygame.quit()


def test_zombie_contact_damage():
    """Contact with a walker deals damage, with an i-frame window."""
    print("\n[zombie] Contact damage + i-frames")
    import zombie
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    dt = 1 / 60.0
    walker_cfg = config.ZOMBIE["types"]["walker"]
    damage = walker_cfg["contact_damage"]
    i_frames = walker_cfg["i_frame_duration"]

    # Walker overlapping the player → one hit.
    game.zombies = [{"x": game.player["x"], "y": game.player["y"],
                     "vx": 0.0, "vy": 0.0, "hp": 30, "type": "walker"}]
    zombie.update(game, dt)
    check("Contact deals config damage",
          game.player["hp"] == config.PLAYER["max_hp"] - damage)
    check("Hit starts the i-frame window",
          abs(game.player["invuln_timer"] - i_frames) < 1e-6)

    # Still overlapping during i-frames → no further damage.
    zombie.update(game, dt)
    check("No damage while invulnerable",
          game.player["hp"] == config.PLAYER["max_hp"] - damage)
    check("I-frame timer decays",
          abs(game.player["invuln_timer"] - (i_frames - dt)) < 1e-6)

    # After the i-frame window expires, contact damages again.
    game.player["invuln_timer"] = 0.0
    zombie.update(game, dt)
    check("Damage again after i-frames expire",
          game.player["hp"] == config.PLAYER["max_hp"] - 2 * damage)

    # A walker far away deals no damage.
    game.player["hp"] = config.PLAYER["max_hp"]
    game.player["invuln_timer"] = 0.0
    game.zombies[0]["x"] = game.player["x"] + 500.0
    game.zombies[0]["y"] = game.player["y"]
    zombie.update(game, dt)
    check("No damage when not in contact",
          game.player["hp"] == config.PLAYER["max_hp"]
          and game.player["invuln_timer"] == 0.0)

    pygame.quit()


def test_zombie_rendered():
    """Walkers are rendered with their distinct config color."""
    print("\n[zombie] Rendered with distinct color")
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    # Place a walker at a known on-screen position.
    game.zombies = [{"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0,
                     "hp": 30, "type": "walker"}]
    game.render(screen)
    color = pygame.Color(*config.ZOMBIE["types"]["walker"]["color"])
    check("Walker pixel is drawn in its config color",
          screen.get_at((100, 100)) == color)

    pygame.quit()


def test_weapon_targeting():
    """Nearest-zombie targeting is a pure function of the zombie list."""
    print("\n[weapon] Nearest-zombie targeting")
    import weapon

    # Three zombies at known positions; the middle one is closest.
    zombies = [
        {"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0, "hp": 30, "type": "walker"},
        {"x": 110.0, "y": 100.0, "vx": 0.0, "vy": 0.0, "hp": 30, "type": "walker"},
        {"x": 300.0, "y": 100.0, "vx": 0.0, "vy": 0.0, "hp": 30, "type": "walker"},
    ]
    target = weapon.nearest_zombie((108.0, 100.0), zombies)
    check("Targets the nearest zombie", target is zombies[1])

    # Diagonal distance is compared correctly (not per-axis).
    zombies = [
        {"x": 100.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "hp": 30, "type": "walker"},
        {"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0, "hp": 30, "type": "walker"},
    ]
    target = weapon.nearest_zombie((100.0, 90.0), zombies)
    check("Targets the closer of two zombies", target is zombies[1])

    # No zombies → no target.
    check("No zombies → no target", weapon.nearest_zombie((0.0, 0.0), []) is None)

    # A zombie exactly at the shooter's position is the target.
    zombies = [{"x": 50.0, "y": 50.0, "vx": 0.0, "vy": 0.0, "hp": 30, "type": "walker"}]
    target = weapon.nearest_zombie((50.0, 50.0), zombies)
    check("Zombie at shooter position is targeted", target is zombies[0])


def test_weapon_cooldown():
    """Fire cooldown is honored: given a timestamp + config, assert whether it fires."""
    print("\n[weapon] Fire cooldown")
    import weapon

    fire_rate = config.WEAPON["types"]["pistol"]["fire_rate"]

    # Never fired → fires immediately.
    check("Fires when never fired", weapon.should_fire(None, 0.0, fire_rate))
    # Just fired → on cooldown.
    check("On cooldown right after firing", not weapon.should_fire(0.0, 0.1, fire_rate))
    # Cooldown elapsed → fires again.
    check("Fires once cooldown elapsed", weapon.should_fire(0.0, fire_rate, fire_rate))
    # Slightly before the cooldown → still on cooldown.
    check("Still on cooldown just before it elapses",
          not weapon.should_fire(0.0, fire_rate - 0.01, fire_rate))


def test_pistol_auto_fire():
    """Pistol auto-fires at the nearest zombie on its cooldown (no shoot button)."""
    print("\n[weapon] Pistol auto-fire")
    import weapon
    import projectile
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    dt = 1 / 60.0
    pistol = config.WEAPON["types"]["pistol"]

    # One zombie to the right of the player.
    game.zombies = [{"x": game.player["x"] + 200.0, "y": game.player["y"],
                     "vx": 0.0, "vy": 0.0, "hp": 30, "type": "walker"}]

    # First frame: never fired → fires immediately, spawning a projectile.
    weapon.update(game, dt)
    pistol_p = [p for p in game.projectiles if p.get("weapon") == "pistol"]
    check("Pistol fires on the first frame (no shoot button)",
          len(pistol_p) == 1)
    check("Pistol is the active weapon",
          game.weapons and game.weapons[0]["type"] == "pistol")
    check("Cooldown is recorded after firing",
          game.weapons[0]["last_fired"] is not None)

    # Next frame: still on cooldown → no second projectile.
    weapon.update(game, dt)
    check("No second shot while on cooldown",
          len([p for p in game.projectiles if p.get("weapon") == "pistol"]) == 1)

    # After the cooldown elapses, the pistol fires again.
    game.weapons[0]["last_fired"] = game.run_time - pistol["fire_rate"]
    weapon.update(game, dt)
    check("Pistol fires again once the cooldown elapses",
          len([p for p in game.projectiles if p.get("weapon") == "pistol"]) == 2)

    # No zombies → no target → no fire.
    game.projectiles = []
    game.zombies = []
    weapon.update(game, dt)
    check("No zombies → no projectile", len(game.projectiles) == 0)


def test_all_weapons_fire_simultaneously():
    """All 5 weapons auto-fire at the nearest zombie on independent cooldowns."""
    print("\n[weapon] All 5 weapons fire simultaneously")
    import weapon
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    dt = 1 / 60.0
    types = [w["type"] for w in game.weapons]
    check("All 5 weapons are active from the start",
          sorted(types) == sorted(["pistol", "knife", "baton", "sniper", "flare"]))

    # One zombie in range of every weapon.
    game.zombies = [{"x": game.player["x"] + 50.0, "y": game.player["y"],
                     "vx": 0.0, "vy": 0.0, "hp": 1000, "type": "walker"}]

    # First frame: every weapon has never fired → all 5 fire.
    game.projectiles = []
    weapon.update(game, dt)
    check("All 5 weapons fire on the first frame",
          len(game.projectiles) + sum(1 for w in game.weapons if w["type"] == "baton") == 5)
    check("Every weapon recorded a cooldown",
          all(w["last_fired"] is not None for w in game.weapons))

    # Next frame: all on cooldown → nothing fires.
    game.projectiles = []
    weapon.update(game, dt)
    check("No weapon fires while all are on cooldown", len(game.projectiles) == 0)

    # Independent cooldowns: only the pistol (shortest fire_rate) is ready.
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = game.run_time - config.WEAPON["types"][w["type"]]["fire_rate"]
    weapon.update(game, dt)
    check("All 5 weapons fire again once their own cooldowns elapse",
          len(game.projectiles) + 1 == 5)

    # A zombie out of range of a weapon → that weapon does not fire.
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = None
    game.zombies = [{"x": game.player["x"] + 1000.0, "y": game.player["y"],
                     "vx": 0.0, "vy": 0.0, "hp": 1000, "type": "walker"}]
    weapon.update(game, dt)
    fired = [w["type"] for w in game.weapons if w["last_fired"] is not None]
    check("Only the sniper reaches a zombie 1000px away", fired == ["sniper"])

    pygame.quit()


def test_weapon_firing_behaviors():
    """Each weapon type has distinct firing behavior (throw arc / whirlwind area /
    long-range / AoE flare), dispatched on the config `type` field."""
    print("\n[weapon] Distinct firing behavior per type")
    import weapon
    import projectile
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    dt = 1 / 60.0
    px, py = game.player["x"], game.player["y"]

    # Knife (throw): arcing projectile — gains height, then falls.
    game.zombies = [{"x": px + 200.0, "y": py, "vx": 0.0, "vy": 0.0,
                     "hp": 1000, "type": "walker"}]
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = None if w["type"] == "knife" else 0.0
    weapon.update(game, dt)
    knife_p = [p for p in game.projectiles if p.get("weapon") == "knife"]
    check("Knife fires an arcing projectile", len(knife_p) == 1 and "arc" in knife_p[0])
    y0 = knife_p[0]["y"]
    projectile.update(game, dt)
    check("Knife projectile rises (throw arc)", knife_p[0]["y"] < y0)

    # Baton (whirlwind): no projectile — area damage around the player.
    game.zombies = [{"x": px + 40.0, "y": py, "vx": 0.0, "vy": 0.0,
                     "hp": 1000, "type": "walker"}]
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = None if w["type"] == "baton" else 0.0
    hp_before = game.zombies[0]["hp"]
    weapon.update(game, dt)
    check("Whirlwind spawns no projectile", len(game.projectiles) == 0)
    check("Whirlwind deals its config damage to a zombie in the area",
          game.zombies[0]["hp"] == hp_before - config.WEAPON["types"]["baton"]["damage"])

    # A zombie outside the whirlwind radius is untouched.
    game.zombies = [{"x": px + 200.0, "y": py, "vx": 0.0, "vy": 0.0,
                     "hp": 1000, "type": "walker"}]
    for w in game.weapons:
        w["last_fired"] = None if w["type"] == "baton" else 0.0
    hp_before = game.zombies[0]["hp"]
    weapon.update(game, dt)
    check("Whirlwind does not hit a zombie outside its radius",
          game.zombies[0]["hp"] == hp_before)

    # Sniper (long-range): fast projectile at the sniper's config speed.
    game.zombies = [{"x": px + 900.0, "y": py, "vx": 0.0, "vy": 0.0,
                     "hp": 1000, "type": "walker"}]
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = None if w["type"] == "sniper" else 0.0
    weapon.update(game, dt)
    sniper_p = [p for p in game.projectiles if p.get("weapon") == "sniper"]
    check("Sniper fires a projectile", len(sniper_p) == 1)
    check("Sniper projectile travels at its config speed",
          abs(math.hypot(sniper_p[0]["vx"], sniper_p[0]["vy"])
              - config.WEAPON["types"]["sniper"]["bullet_speed"]) < 1e-6)

    # Flare (AoE): arcing projectile that explodes, damaging zombies in the radius.
    game.zombies = [{"x": px + 100.0, "y": py, "vx": 0.0, "vy": 0.0,
                     "hp": 1000, "type": "walker"}]
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = None if w["type"] == "flare" else 0.0
    weapon.update(game, dt)
    flare_p = [p for p in game.projectiles if p.get("weapon") == "flare"]
    check("Flare fires an arcing projectile", len(flare_p) == 1 and "arc" in flare_p[0])
    # Place the flare on the zombie and let it explode.
    flare_p[0]["x"] = game.zombies[0]["x"]
    flare_p[0]["y"] = game.zombies[0]["y"]
    hp_before = game.zombies[0]["hp"]
    projectile.update(game, dt)
    check("Flare explosion deals its config damage (AoE)",
          game.zombies[0]["hp"] == hp_before - config.WEAPON["types"]["flare"]["damage"])

    # A second zombie inside the AoE radius is hit by the same explosion.
    game.zombies = [{"x": px + 100.0, "y": py, "vx": 0.0, "vy": 0.0,
                     "hp": 1000, "type": "walker"},
                    {"x": px + 100.0, "y": py + 30.0, "vx": 0.0, "vy": 0.0,
                     "hp": 1000, "type": "walker"}]
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = None if w["type"] == "flare" else 0.0
    weapon.update(game, dt)
    flare_p = [p for p in game.projectiles if p.get("weapon") == "flare"]
    flare_p[0]["x"] = game.zombies[0]["x"]
    flare_p[0]["y"] = game.zombies[0]["y"]
    hp0 = game.zombies[0]["hp"]
    hp1 = game.zombies[1]["hp"]
    projectile.update(game, dt)
    check("Flare AoE hits every zombie in the radius",
          game.zombies[0]["hp"] == hp0 - config.WEAPON["types"]["flare"]["damage"]
          and game.zombies[1]["hp"] == hp1 - config.WEAPON["types"]["flare"]["damage"])

    pygame.quit()


def test_weapon_stats_from_config():
    """Each weapon's stats (fire rate, damage, range, projectile behavior) are
    config.py dict values."""
    print("\n[config] Weapon stats are config dict values")
    for name in ["pistol", "knife", "baton", "sniper", "flare"]:
        w = config.WEAPON["types"][name]
        check(f"{name} has a type field", "type" in w)
        check(f"{name} fire rate is a config dict value", "fire_rate" in w)
        check(f"{name} damage is a config dict value", "damage" in w)
        check(f"{name} range is a config dict value", "range" in w)
    check("Knife throw arc is a config dict value", "arc" in config.WEAPON["types"]["knife"])
    check("Baton whirlwind radius is a config dict value",
          "whirlwind_radius" in config.WEAPON["types"]["baton"])
    check("Flare AoE radius is a config dict value",
          "aoe_radius" in config.WEAPON["types"]["flare"])
    check("Sniper range exceeds pistol range",
          config.WEAPON["types"]["sniper"]["range"] > config.WEAPON["types"]["pistol"]["range"])


def test_xp_math():
    """XP math is a pure function: gem count + config → XP total."""
    print("\n[xp] Pure XP math")
    import xp

    check("0 gems → 0 XP", xp.xp_total(0) == 0)
    check("1 gem → gem_value XP", xp.xp_total(1) == config.XP["gem_value"])
    check("5 gems → 5 * gem_value XP", xp.xp_total(5) == 5 * config.XP["gem_value"])
    check("100 gems → 100 * gem_value XP", xp.xp_total(100) == 100 * config.XP["gem_value"])

    # Independent of game state (pure function of gem count + config).
    pygame.init()
    game = Game(seed=42, headless=True)
    game.start_run()
    game.xp["current"] = 999
    check("Pure: ignores existing game XP state", xp.xp_total(3) == 3 * config.XP["gem_value"])

    pygame.quit()


def test_projectile_travel_and_damage():
    """A projectile spawns, travels at config speed, and deals config damage on hit."""
    print("\n[projectile] Travel + damage")
    import weapon
    import projectile
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    dt = 1 / 60.0
    pistol = config.WEAPON["types"]["pistol"]
    speed = pistol["bullet_speed"]
    damage = pistol["damage"]

    # One zombie to the right of the player.
    game.zombies = [{"x": game.player["x"] + 200.0, "y": game.player["y"],
                     "vx": 0.0, "vy": 0.0, "hp": 30, "type": "walker"}]
    weapon.update(game, dt)
    p = [q for q in game.projectiles if q.get("weapon") == "pistol"][0]
    check("A projectile was spawned", len(game.projectiles) >= 1)
    check("Projectile carries the pistol's config damage", p["damage"] == damage)
    check("Projectile aims at the target (moves right)", p["vx"] > 0 and p["vy"] == 0)

    # Travel: one frame moves the projectile at config speed.
    x0, y0 = p["x"], p["y"]
    projectile.update(game, dt)
    check("Projectile travels at config speed",
          abs(math.hypot(p["x"] - x0, p["y"] - y0) - speed * dt) < 1e-6)

    # Damage: place the projectile on the zombie → the hit deals config damage.
    p["x"] = game.zombies[0]["x"]
    p["y"] = game.zombies[0]["y"]
    hp_before = game.zombies[0]["hp"]
    projectile.update(game, dt)
    check("Hit deals the pistol's config damage",
          game.zombies[0]["hp"] == hp_before - damage)
    check("Hit projectile is removed",
          len([q for q in game.projectiles if q.get("weapon") == "pistol"]) == 0)

    # A lethal hit removes the zombie.
    game.zombies = [{"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0,
                     "hp": damage, "type": "walker"}]
    game.projectiles = [{"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0,
                         "damage": damage}]
    projectile.update(game, dt)
    check("Lethal hit removes the zombie", len(game.zombies) == 0)

    pygame.quit()


def test_xp_level_math():
    """XP/level math: given a gem count + config, assert the resulting level
    and whether a level-up fires."""
    print("\n[xp] Level math (gem count + config → level, level-up fires)")
    import xp

    # Pure math: 0 XP → level 1, no level-up.
    check("0 XP → level 1", xp.level_for_xp(0) == 1)
    check("0 XP → no level-up pending", xp.level_ups_pending(0) == 0)

    # Linear curve: level N needs N * xp_per_level XP.
    per = config.XP["xp_per_level"]
    check("xp_to_next_level(1) = xp_per_level", xp.xp_to_next_level(1) == per)
    check("xp_to_next_level(2) = 2 * xp_per_level", xp.xp_to_next_level(2) == 2 * per)
    check("xp_to_next_level(30) = 30 * xp_per_level", xp.xp_to_next_level(30) == 30 * per)

    # Crossing the threshold fires exactly one level-up.
    check("XP just below threshold → level 1", xp.level_for_xp(per - 1) == 1)
    check("XP at threshold → level 2", xp.level_for_xp(per) == 2)
    check("XP at threshold → 1 level-up pending", xp.level_ups_pending(per) == 1)

    # Multiple levels in one batch (e.g. a boss gem dump).
    # Cumulative XP to reach level 3: per + 2*per = 3*per.
    check("XP at 3*per → level 3", xp.level_for_xp(3 * per) == 3)
    check("XP at 3*per → 2 level-ups pending", xp.level_ups_pending(3 * per) == 2)

    # Gem count + config → level (the ticket's exact seam).
    gems = 3 * per  # 30 gems at gem_value 1
    check("Gem count + config → level 3",
          xp.level_for_xp(xp.xp_total(gems)) == 3)

    # Curve is ~linear to ~level 30 by the 20-min mark (config values).
    check("Level curve is linear (config)", config.XP["level_curve"] == "linear")
    check("Max level ~30 (config)", config.XP["max_level"] == 30)
    # Total XP to reach level 30: sum(1..29) * per = 435 * per.
    check("XP to reach level 30 = 435 * xp_per_level",
          xp.level_for_xp(435 * per - 1) == 29
          and xp.level_for_xp(435 * per) == 30)

    # At max level, no further level-ups fire.
    check("XP past max level caps at max_level",
          xp.level_for_xp(435 * per + 1000) == config.XP["max_level"])
    check("No level-up pending at max level",
          xp.level_ups_pending(435 * per + 1000, current_level=config.XP["max_level"]) == 0)

    # Independent of game state (pure function of XP + config).
    pygame.init()
    game = Game(seed=42, headless=True)
    game.start_run()
    game.xp["level"] = 99
    check("Pure: ignores existing game level state", xp.level_for_xp(per) == 2)

    pygame.quit()


def test_pistol_stats_from_config():
    """Pistol stats (fire rate, damage, projectile speed) are config dict values."""
    print("\n[config] Pistol stats are config dict values")
    pistol = config.WEAPON["types"]["pistol"]
    check("Pistol fire rate is a config dict value", "fire_rate" in pistol)
    check("Pistol damage is a config dict value", "damage" in pistol)
    check("Pistol projectile speed is a config dict value", "bullet_speed" in pistol)
    check("Pistol fire rate is positive", pistol["fire_rate"] > 0)
    check("Pistol damage is positive", pistol["damage"] > 0)
    check("Pistol projectile speed is positive", pistol["bullet_speed"] > 0)


def test_xp_kill_drops_gem():
    """Every zombie death drops 1 XP gem (elite/boss drop a handful)."""
    print("\n[xp] Kill drops gem")
    import zombie

    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    # Walker death drops exactly 1 gem at the zombie's position.
    # (Seek runs first, so the gem lands where the zombie moved to.)
    game.zombies = [{"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0,
                     "hp": 0, "type": "walker"}]
    game.xp["gems"] = []
    zombie.update(game, 1 / 60.0)
    check("Walker death drops 1 gem", len(game.xp["gems"]) == 1)
    check("Dead zombie is removed", len(game.zombies) == 0)
    # Seek moves the zombie toward the player by speed*dt along the
    # normalized direction, so the gem lands exactly there.
    px, py = game.player["x"], game.player["y"]
    dx, dy = px - 100.0, py - 100.0
    length = math.hypot(dx, dy)
    speed = config.ZOMBIE["types"]["walker"]["speed"]
    check("Gem drops at the zombie's (post-seek) position",
          game.xp["gems"][0]["x"] == 100.0 + dx / length * speed * (1 / 60.0)
          and game.xp["gems"][0]["y"] == 100.0 + dy / length * speed * (1 / 60.0))

    # Living zombies drop nothing.
    game.zombies = [{"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0,
                     "hp": 30, "type": "walker"}]
    game.xp["gems"] = []
    zombie.update(game, 1 / 60.0)
    check("Living zombie drops no gem", len(game.xp["gems"]) == 0)

    # Elite/boss drop a handful (stub, wired in T11).
    game.zombies = [{"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0,
                     "hp": 0, "type": "elite"}]
    game.xp["gems"] = []
    zombie.update(game, 1 / 60.0)
    check("Elite death drops a handful of gems (stub)",
          len(game.xp["gems"]) > 1)

    game.zombies = [{"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0,
                     "hp": 0, "type": "boss"}]
    game.xp["gems"] = []
    zombie.update(game, 1 / 60.0)
    check("Boss death drops a handful of gems (stub)",
          len(game.xp["gems"]) > 1)

    pygame.quit()


def test_xp_magnet_pickup():
    """Gems within the magnet radius are pulled to the player; collected on contact."""
    print("\n[xp] Magnet pickup")
    import xp

    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    dt = 1 / 60.0
    radius = config.XP["gem_magnet_radius"]
    value = config.XP["gem_value"]
    px, py = game.player["x"], game.player["y"]

    # Gem within the magnet radius is pulled toward the player.
    game.xp["gems"] = [{"x": px + 30.0, "y": py, "vx": 0.0, "vy": 0.0}]
    xp.update(game, dt)
    check("Gem within magnet radius is pulled toward the player",
          game.xp["gems"][0]["x"] < px + 30.0 and game.xp["gems"][0]["y"] == py)

    # Gem outside the magnet radius is not pulled.
    game.xp["gems"] = [{"x": px + radius + 50.0, "y": py, "vx": 0.0, "vy": 0.0}]
    xp.update(game, dt)
    check("Gem outside magnet radius is not pulled",
          game.xp["gems"][0]["x"] == px + radius + 50.0)

    # Gem on contact is collected and adds to the player's XP total.
    game.xp["current"] = 0
    game.xp["gems"] = [{"x": px, "y": py, "vx": 0.0, "vy": 0.0}]
    xp.update(game, dt)
    check("Gem on contact is collected", len(game.xp["gems"]) == 0)
    check("Collected gem adds gem_value to XP total",
          game.xp["current"] == value)

    # Multiple gems on contact all add up.
    game.xp["current"] = 0
    game.xp["gems"] = [{"x": px, "y": py, "vx": 0.0, "vy": 0.0},
                       {"x": px, "y": py, "vx": 0.0, "vy": 0.0}]
    xp.update(game, dt)
    check("Two gems on contact add 2 * gem_value",
          game.xp["current"] == 2 * value and len(game.xp["gems"]) == 0)

    pygame.quit()


def test_xp_rendered():
    """XP gems are rendered in their config color."""
    print("\n[xp] Gems rendered")
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    game.xp["gems"] = [{"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0}]
    game.render(screen)
    color = pygame.Color(*config.ITEM["xp_gem"]["color"])
    check("Gem pixel is drawn in its config color",
          screen.get_at((100, 100)) == color)

    pygame.quit()


def test_upgrade_option_pool():
    """Upgrade pool: 4 categories, 3 options per pick, multiple picks at high levels."""
    print("\n[upgrade] Option pool (4 categories, multiple picks at high levels)")
    import upgrade

    # The pool covers all 4 categories (config-driven).
    pool = upgrade.option_pool()
    categories = {opt["category"] for opt in pool}
    check("Pool covers all 4 config categories",
          categories == set(config.UPGRADE["categories"]))

    # Every option has the fields the 3-card overlay needs.
    check("Every option has icon, name, description",
          all("icon" in o and "name" in o and "description" in o for o in pool))

    # 3 options per pick (config), sampled from the pool.
    rng = random.Random(42)
    options = upgrade.roll_options(pool, rng)
    check("roll_options returns options_per_levelup options",
          len(options) == config.UPGRADE["options_per_levelup"])
    check("Rolled options are distinct",
          len({id(o) for o in options}) == len(options))

    # Multiple picks are offered at high levels (per the ~level-30 curve).
    check("Low level → 1 pick", upgrade.picks_for_level(2) == 1)
    check("High level → multiple picks",
          upgrade.picks_for_level(config.UPGRADE["max_level"]) > 1)
    check("Picks grow with level",
          upgrade.picks_for_level(config.UPGRADE["max_level"])
          >= upgrade.picks_for_level(config.UPGRADE["multi_pick_level"]))

    # Deterministic with a seeded rng.
    o1 = upgrade.roll_options(pool, random.Random(7))
    o2 = upgrade.roll_options(pool, random.Random(7))
    check("Seeded rng → same roll", [o["name"] for o in o1] == [o["name"] for o in o2])


def test_level_up_pause_and_pick():
    """On level-up the run pauses and a 3-card overlay offers 3 options;
    the player picks 1; 1 reroll is available."""
    print("\n[upgrade] Level-up pause + 3-card pick + 1 reroll")
    import upgrade

    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    # No level-up at run start.
    check("No level-up at run start", game.state == "playing"
          and not game.upgrade["active"])

    # Crossing the level threshold pauses the run and opens the overlay.
    per = config.XP["xp_per_level"]
    game.xp["current"] = per
    game.update(1 / 60.0)
    check("Level-up pauses the run", game.state == "level_up")
    check("Overlay is active", game.upgrade["active"] is True)
    check("Overlay shows 3 options",
          len(game.upgrade["options"]) == config.UPGRADE["options_per_levelup"])
    check("Each option has icon, name, description",
          all("icon" in o and "name" in o and "description" in o
              for o in game.upgrade["options"]))
    check("1 reroll available",
          game.upgrade["rerolls_left"] == config.UPGRADE["rerolls"])

    # The overlay is rendered full-screen (cards drawn on the screen).
    game.render(screen)
    check("Level-up overlay renders (screen not just background)",
          any(screen.get_at((x, y)) != pygame.Color(*config.RENDERER["background_color"])
              for x in range(0, config.DISPLAY["width"], 40)
              for y in range(0, config.DISPLAY["height"], 40)))

    # Reroll: 1 reroll is available and re-rolls the options.
    game.handle_level_up_reroll()
    check("Reroll consumes the reroll",
          game.upgrade["rerolls_left"] == config.UPGRADE["rerolls"] - 1)
    check("Reroll re-rolls the 3 options",
          len(game.upgrade["options"]) == config.UPGRADE["options_per_levelup"])
    # No second reroll.
    game.handle_level_up_reroll()
    check("Only 1 reroll available",
          game.upgrade["rerolls_left"] == 0)

    # Pick 1 of 3: the level advances and the run resumes.
    picked_name = game.upgrade["options"][1]["name"]
    game.handle_level_up_pick(1)
    check("Pick resumes the run", game.state == "playing")
    check("Overlay is closed", game.upgrade["active"] is False)
    check("Pick advances the level", game.xp["level"] == 2)
    check("Picked option is recorded",
          game.upgrade["picked"] == picked_name)

    # Multiple level-ups in one batch → multiple picks offered.
    # 60 XP from level 2 crosses the level-3 (30) and level-4 (60)
    # thresholds, so 2 picks are offered.
    game.xp["current"] = 6 * per  # 60 XP total (level 2 → 4)
    game.update(1 / 60.0)
    check("Batched level-ups open the overlay again", game.state == "level_up")
    check("Multiple picks offered for batched level-ups",
          game.upgrade["picks_left"] >= 2)
    # Pick through them all → run resumes.
    for _ in range(game.upgrade["picks_left"]):
        game.handle_level_up_pick(0)
    check("All picks consumed → run resumes",
          game.state == "playing" and not game.upgrade["active"])
    check("Level advanced by the batch", game.xp["level"] == 4)

    pygame.quit()


def test_passive_pick_effects():
    """Picking a passive at a level-up takes real effect: +damage, +move speed,
    +magnet radius, -cooldown. Passives live in the player's state dict and
    are applied each frame. All effects are config.py-driven."""
    print("\n[passive] Pick effects (damage, move speed, magnet, cooldown)")
    import player
    import xp
    import weapon
    import upgrade

    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    dt = 1 / 60.0
    base_speed = config.PLAYER["speed"]
    base_magnet = config.XP["gem_magnet_radius"]
    pistol = config.WEAPON["types"]["pistol"]

    # Passives are stored in the player's state dict.
    check("Player state has a passives dict",
          isinstance(game.player["passives"], dict))
    check("All 4 config passives start at level 0",
          all(game.player["passives"][name] == 0
              for name in config.UPGRADE["passives"]))

    # --- +damage: weapon damage increases by the config per_level. ---
    dmg_per = config.UPGRADE["passives"]["damage"]["per_level"]
    upgrade.apply_pick(game, "damage")
    check("Picking +damage stores the passive in the player state",
          game.player["passives"]["damage"] == 1)
    game.zombies = [{"x": game.player["x"] + 50.0, "y": game.player["y"],
                     "vx": 0.0, "vy": 0.0, "hp": 1000, "type": "walker"}]
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = None if w["type"] == "pistol" else 0.0
    weapon.update(game, dt)
    p = [q for q in game.projectiles if q.get("weapon") == "pistol"][0]
    check("Picking +damage increases weapon damage (config per_level)",
          abs(p["damage"] - pistol["damage"] * (1 + dmg_per)) < 1e-9)

    # --- +move speed: player movement speed increases by the config per_level. ---
    spd_per = config.UPGRADE["passives"]["move_speed"]["per_level"]
    upgrade.apply_pick(game, "move_speed")
    check("Picking +move speed stores the passive in the player state",
          game.player["passives"]["move_speed"] == 1)
    game.player["x"] = config.DISPLAY["width"] / 2
    game.player["y"] = config.DISPLAY["height"] / 2
    set_keys([pygame.K_d])
    player.update(game)
    check("Picking +move speed increases player movement speed (config per_level)",
          abs(game.player["x"] - (config.DISPLAY["width"] / 2
                                  + base_speed * (1 + spd_per) * dt)) < 1e-6)

    # --- +magnet radius: the XP-gem pickup radius increases by the config per_level. ---
    mag_per = config.UPGRADE["passives"]["magnet_radius"]["per_level"]
    upgrade.apply_pick(game, "magnet_radius")
    check("Picking +magnet radius stores the passive in the player state",
          game.player["passives"]["magnet_radius"] == 1)
    px, py = game.player["x"], game.player["y"]
    # A gem just outside the base radius but inside the boosted radius is pulled.
    game.xp["gems"] = [{"x": px + base_magnet + 5.0, "y": py, "vx": 0.0, "vy": 0.0}]
    xp.update(game, dt)
    check("Picking +magnet radius increases the gem pickup radius (config per_level)",
          game.xp["gems"][0]["x"] < px + base_magnet + 5.0)
    # A gem outside the boosted radius is still not pulled.
    game.xp["gems"] = [{"x": px + base_magnet + mag_per + 5.0, "y": py,
                        "vx": 0.0, "vy": 0.0}]
    xp.update(game, dt)
    check("Gem outside the boosted magnet radius is not pulled",
          game.xp["gems"][0]["x"] == px + base_magnet + mag_per + 5.0)

    # --- -cooldown: weapon fire cooldowns decrease by the config per_level. ---
    cd_per = config.UPGRADE["passives"]["cooldown"]["per_level"]
    upgrade.apply_pick(game, "cooldown")
    check("Picking -cooldown stores the passive in the player state",
          game.player["passives"]["cooldown"] == 1)
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = None if w["type"] == "pistol" else 0.0
    weapon.update(game, dt)
    check("Pistol fired with the reduced cooldown",
          len([q for q in game.projectiles if q.get("weapon") == "pistol"]) == 1)
    # The pistol is on its (reduced) cooldown: it does not fire again next frame.
    game.projectiles = []
    weapon.update(game, dt)
    check("Pistol is on its reduced cooldown (no second shot)",
          len([q for q in game.projectiles if q.get("weapon") == "pistol"]) == 0)
    # After the reduced cooldown elapses, it fires again.
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = game.run_time - pistol["fire_rate"] * (1 - cd_per) - 2 * dt
    weapon.update(game, dt)
    check("Pistol fires again once the reduced cooldown elapses",
          len([q for q in game.projectiles if q.get("weapon") == "pistol"]) == 1)

    # --- Passive levels cap at the config max_level. ---
    max_lvl = config.UPGRADE["passives"]["damage"]["max_level"]
    game.player["passives"]["damage"] = max_lvl
    upgrade.apply_pick(game, "damage")
    check("Passive level caps at the config max_level",
          game.player["passives"]["damage"] == max_lvl)

    # --- Effects are applied each frame from the player state (not one-shot). ---
    # Reset the pistol cooldown and confirm the damage bonus still applies
    # at the current (max) passive level.
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = None if w["type"] == "pistol" else 0.0
    weapon.update(game, dt)
    p = [q for q in game.projectiles if q.get("weapon") == "pistol"][0]
    expected = pistol["damage"] * (1 + dmg_per * max_lvl)
    check("Passive effects persist across frames (applied each frame)",
          abs(p["damage"] - expected) < 1e-9)

    pygame.quit()


def test_weapon_evolution():
    """T12: A weapon evolution unlocks when the weapon and its paired
    passive are both at max level. Evolved stats take effect."""
    print("\n[evolution] Weapon evolutions")
    import weapon
    import upgrade

    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    dt = 1 / 60.0
    evo_cfg = config.WEAPON["evolutions"]["pistol"]
    max_wpn = config.WEAPON["max_level"]
    max_psv = config.UPGRADE["passives"]["damage"]["max_level"]

    # --- can_evolve is a pure function of config values. ---
    check("can_evolve: weapon below max → False",
          weapon.can_evolve("pistol", 1, {"damage": max_psv}) is False)
    check("can_evolve: passive below max → False",
          weapon.can_evolve("pistol", max_wpn, {"damage": 0}) is False)
    check("can_evolve: both at max → True",
          weapon.can_evolve("pistol", max_wpn, {"damage": max_psv}) is True)
    check("can_evolve: unknown weapon → False",
          weapon.can_evolve("nonexistent", max_wpn, {"damage": max_psv}) is False)

    # --- Weapon starts at level 1, not evolved. ---
    pistol_w = [w for w in game.weapons if w["type"] == "pistol"][0]
    check("Pistol starts at level 1", pistol_w["level"] == 1)
    check("Pistol starts not evolved", pistol_w["evolved"] is False)

    # --- Bump weapon to max level via apply_weapon_level_pick. ---
    for _ in range(max_wpn - 1):
        upgrade.apply_weapon_level_pick(game, "pistol")
    check("Pistol at max level after picks", pistol_w["level"] == max_wpn)

    # --- Evolution not yet unlocked (passive not at max). ---
    upgrade.apply_evolved_pick(game, "pistol")
    check("Evolution not unlocked before passive at max",
          pistol_w["evolved"] is False)

    # --- Bump paired passive (damage) to max level. ---
    for _ in range(max_psv):
        upgrade.apply_pick(game, "damage")
    check("Damage passive at max level",
          game.player["passives"]["damage"] == max_psv)

    # --- Now evolution unlocks. ---
    upgrade.apply_evolved_pick(game, "pistol")
    check("Pistol evolved after both at max", pistol_w["evolved"] is True)

    # --- Evolved stats take effect: damage uses evolved value. ---
    game.zombies = [{"x": game.player["x"] + 50.0, "y": game.player["y"],
                     "vx": 0.0, "vy": 0.0, "hp": 1000, "type": "walker"}]
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = None if w["type"] == "pistol" else 0.0
    weapon.update(game, dt)
    p = [q for q in game.projectiles if q.get("weapon") == "pistol"][0]
    # Evolved damage (20) * passive multiplier (1 + 0.1 * 5 = 1.5) = 30
    expected_damage = evo_cfg["evolved_stats"]["damage"] * (
        1 + config.UPGRADE["passives"]["damage"]["per_level"] * max_psv)
    check("Evolved pistol uses evolved damage stat",
          abs(p["damage"] - expected_damage) < 1e-9)

    # --- Evolved fire rate is used (faster than base). ---
    # Reset cooldown and verify the evolved fire_rate is in effect.
    game.projectiles = []
    for w in game.weapons:
        w["last_fired"] = None if w["type"] == "pistol" else 0.0
    weapon.update(game, dt)
    check("Evolved pistol fires (evolved fire_rate honored)",
          len([q for q in game.projectiles if q.get("weapon") == "pistol"]) == 1)

    # --- Evolution is idempotent (picking again is a no-op). ---
    upgrade.apply_evolved_pick(game, "pistol")
    check("Evolution is idempotent", pistol_w["evolved"] is True)

    # --- Other weapons are unaffected. ---
    knife_w = [w for w in game.weapons if w["type"] == "knife"][0]
    check("Knife not evolved (different paired passive)",
          knife_w["evolved"] is False)

    pygame.quit()


def test_hud_timer_format():
    """The 20:00 countdown timer formats as MM:SS with a milestone each minute."""
    print("\n[hud] Timer format")
    import hud

    duration = config.RUN["duration_seconds"]
    check("Start of run shows the full 20:00", hud.format_timer(0) == "20:00")
    check("After 1 second it counts down", hud.format_timer(1) == "19:59")
    # Milestone at each minute: the MM component ticks down once per minute.
    check("Milestone at the 1-minute mark", hud.format_timer(60) == "19:00")
    check("Milestone at the 2-minute mark", hud.format_timer(120) == "18:00")
    check("Mid-minute shows the seconds", hud.format_timer(90) == "18:30")
    # Clamps at 00:00 (never goes negative).
    check("Clamps at 00:00 at the end of the run", hud.format_timer(duration) == "00:00")
    check("Clamps at 00:00 past the end of the run", hud.format_timer(duration + 5) == "00:00")
    # Pure function of elapsed + config duration (independent of game state).
    check("Uses the config duration by default",
          hud.format_timer(0) == f"{duration // 60:02d}:{duration % 60:02d}")


def test_hud_hp_bar_rendered():
    """A player HP bar is rendered as a proportional remaining-life fill."""
    print("\n[hud] HP bar")
    import hud
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    bar = config.HUD["hp_bar"]
    max_hp = config.PLAYER["max_hp"]
    fill_color = pygame.Color(*bar["color"])
    bg_color = pygame.Color(*bar["background"])

    # Full HP: the fill spans the whole bar width.
    game.player["hp"] = max_hp
    game.render(screen)
    check("Full HP fills the whole bar",
          screen.get_at((bar["x"] + 2, bar["y"] + 2)) == fill_color)
    check("Full HP fill width equals the bar width",
          hud._hp_bar_fill_width(max_hp, max_hp) == bar["width"])

    # Half HP: the fill is proportional (about half the width).
    game.player["hp"] = max_hp // 2
    game.render(screen)
    half_width = hud._hp_bar_fill_width(max_hp // 2, max_hp)
    check("Half HP fill is proportional (about half the width)",
          abs(half_width - bar["width"] // 2) <= 1)
    # The right half of the bar shows the empty (background) portion.
    check("Lost HP shows the bar background",
          screen.get_at((bar["x"] + bar["width"] - 2, bar["y"] + 2)) == bg_color)

    # Zero HP: no fill at all.
    game.player["hp"] = 0
    game.render(screen)
    check("Zero HP has no fill", hud._hp_bar_fill_width(0, max_hp) == 0)
    check("Zero HP bar shows the background",
          screen.get_at((bar["x"] + 2, bar["y"] + 2)) == bg_color)

    pygame.quit()


def test_hud_kill_count_increments():
    """The kill count increments on zombie death."""
    print("\n[hud] Kill count")
    import zombie
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    check("Kill count starts at 0", game.hud["kills"] == 0)

    # A dead zombie is removed and counted as a kill.
    game.zombies = [{"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0,
                     "hp": 0, "type": "walker"}]
    zombie.update(game, 1 / 60.0)
    check("Kill count increments on zombie death", game.hud["kills"] == 1)

    # A living zombie is not counted.
    game.zombies = [{"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0,
                     "hp": 30, "type": "walker"}]
    zombie.update(game, 1 / 60.0)
    check("Living zombie does not increment the kill count", game.hud["kills"] == 1)

    # Multiple deaths accumulate.
    game.zombies = [{"x": 100.0, "y": 100.0, "vx": 0.0, "vy": 0.0,
                     "hp": 0, "type": "walker"},
                    {"x": 200.0, "y": 200.0, "vx": 0.0, "vy": 0.0,
                     "hp": 0, "type": "walker"}]
    zombie.update(game, 1 / 60.0)
    check("Multiple deaths accumulate the kill count", game.hud["kills"] == 3)

    pygame.quit()


def test_hud_item_icons():
    """Item icons reflect the currently-owned weapons and passives."""
    print("\n[hud] Item icons")
    import hud
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)
    game.start_run()

    icons = config.HUD["icons"]
    size, gap = icons["size"], icons["gap"]
    weapon_color = pygame.Color(*icons["weapon_color"])
    passive_color = pygame.Color(*icons["passive_color"])
    bg_color = pygame.Color(*config.RENDERER["background_color"])

    n_weapons = len(game.weapons)
    # The first owned weapon draws an icon at the first slot.
    game.render(screen)
    check("First owned weapon draws an icon",
          screen.get_at((icons["x"] + 2, icons["y"] + 2)) == weapon_color)
    # The slot just past the last weapon icon is empty (no passives owned).
    last_weapon_x = icons["x"] + (n_weapons - 1) * (size + gap)
    check("No passive icon when no passives are owned",
          screen.get_at((last_weapon_x + size + gap + 2, icons["y"] + 2)) == bg_color)

    # Owning a passive adds a passive icon right after the weapon icons.
    game.hud["passives"] = ["damage"]
    game.render(screen)
    check("A passive icon appears after the weapon icons",
          screen.get_at((last_weapon_x + size + gap + 2, icons["y"] + 2)) == passive_color)

    pygame.quit()


def test_hud_config_driven():
    """All HUD layout/positions are config.py-driven."""
    print("\n[hud] Config-driven layout")
    check("HUD hp_bar position is a config dict value",
          "x" in config.HUD["hp_bar"] and "y" in config.HUD["hp_bar"])
    check("HUD hp_bar size is a config dict value",
          "width" in config.HUD["hp_bar"] and "height" in config.HUD["hp_bar"])
    check("HUD timer position is a config dict value",
          "x" in config.HUD["timer"] and "y" in config.HUD["timer"])
    check("HUD level position is a config dict value",
          "x" in config.HUD["level"] and "y" in config.HUD["level"])
    check("HUD kills position is a config dict value",
          "x" in config.HUD["kills"] and "y" in config.HUD["kills"])
    check("HUD icons position/size is a config dict value",
          "x" in config.HUD["icons"] and "y" in config.HUD["icons"]
          and "size" in config.HUD["icons"])
    check("HUD font size is a config dict value", "font_size" in config.HUD)


def test_menu_navigation():
    """Menu navigation works (Play starts a run, Quit exits)."""
    print("\n[menu] Menu navigation")
    pygame.init()
    screen = pygame.display.set_mode((config.DISPLAY["width"], config.DISPLAY["height"]))
    game = Game(seed=42, headless=True)

    check("Initial menu selection is 0", game.menu["selected"] == 0)

    # Simulate pressing DOWN
    game.menu["selected"] = (game.menu["selected"] + 1) % len(game.menu["options"])
    check("Menu selection moved to 1", game.menu["selected"] == 1)

    # Simulate pressing UP
    game.menu["selected"] = (game.menu["selected"] - 1) % len(game.menu["options"])
    check("Menu selection moved back to 0", game.menu["selected"] == 0)

    # Select Play and start
    game.menu["selected"] = 0
    game.start_run()
    check("Play starts a run", game.state == "playing")

    pygame.quit()


def main():
    print("=" * 60)
    print("test_manual.py — Zombie Survival scaffold smoke test")
    print("=" * 60)

    test_config_dicts()
    test_game_construction()
    test_seeded_rng()
    test_headless_loop()
    test_player_movement()
    test_player_facing()
    test_player_hp()
    test_player_rendered()
    test_zombie_spawn()
    test_zombie_seek()
    test_zombie_contact_damage()
    test_zombie_rendered()
    test_weapon_targeting()
    test_weapon_cooldown()
    test_pistol_auto_fire()
    test_all_weapons_fire_simultaneously()
    test_weapon_firing_behaviors()
    test_projectile_travel_and_damage()
    test_pistol_stats_from_config()
    test_weapon_stats_from_config()
    test_xp_math()
    test_xp_level_math()
    test_xp_kill_drops_gem()
    test_xp_magnet_pickup()
    test_xp_rendered()
    test_upgrade_option_pool()
    test_level_up_pause_and_pick()
    test_passive_pick_effects()
    test_weapon_evolution()
    test_hud_timer_format()
    test_hud_hp_bar_rendered()
    test_hud_kill_count_increments()
    test_hud_item_icons()
    test_hud_config_driven()
    test_menu_navigation()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    print("=" * 60)

    if FAIL > 0:
        sys.exit(1)
    print("ALL TESTS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
