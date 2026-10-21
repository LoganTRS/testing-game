"""Entry point — python main.py launches the game.

Supports headless mode via --headless flag or HEADLESS=1 env var.
"""
import os
import sys

import pygame
import config
from game import Game


def main():
    headless = "--headless" in sys.argv or os.environ.get("HEADLESS", "0") == "1"

    if headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"

    pygame.init()
    screen = pygame.display.set_mode(
        (config.DISPLAY["width"], config.DISPLAY["height"])
    )
    pygame.display.set_caption(config.DISPLAY["title"])
    clock = pygame.time.Clock()

    game = Game(headless=headless)

    while game.running:
        dt = clock.tick(config.DISPLAY["fps"]) / 1000.0
        for event in pygame.event.get():
            if game.handle_event(event):
                break
        game.update(dt)
        game.render(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
