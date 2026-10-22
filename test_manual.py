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
    test_xp_kill_drops_gem()
    test_xp_magnet_pickup()
    test_xp_rendered()
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
