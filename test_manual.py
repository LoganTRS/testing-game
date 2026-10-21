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
