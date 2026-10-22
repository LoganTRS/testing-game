"""Game class — shared context passed to all 12 modules.

The Game class is constructed in main and passed to every module.
Modules don't import each other; Game is the shared context.
"""
import random

import pygame
import config

import player
import zombie
import weapon
import projectile
import xp
import hud
import menu
import upgrade
import item
import renderer


class Game:
    """Shared game context. Constructed in main, passed to all modules."""

    def __init__(self, seed=None, headless=False):
        if seed is None:
            seed = config.RUN["seed"]
        self.seed = seed
        self.rng = random.Random(seed)
        self.headless = headless

        # Game state
        self.state = "menu"  # "menu" | "playing" | "paused" | "game_over"
        self.running = True
        self.frame = 0
        self.run_time = 0.0  # seconds elapsed in current run

        # Module state (initialized by each module's init)
        self.player = None
        self.zombies = None
        self.weapons = None
        self.projectiles = None
        self.xp = None
        self.hud = None
        self.menu = None
        self.upgrade = None
        self.items = None
        self.renderer = None

        # Initialize all modules
        self._init_modules()

    def _init_modules(self):
        """Call init on all 12 modules, passing self as the shared context."""
        player.init(self)
        zombie.init(self)
        weapon.init(self)
        projectile.init(self)
        xp.init(self)
        hud.init(self)
        menu.init(self)
        upgrade.init(self)
        item.init(self)
        renderer.init(self)

    def start_run(self):
        """Start a new run from the menu."""
        self.state = "playing"
        self.run_time = 0.0
        self.frame = 0
        # Re-initialize run state
        player.init(self)
        zombie.init(self)
        weapon.init(self)
        projectile.init(self)
        xp.init(self)
        hud.init(self)
        upgrade.init(self)
        item.init(self)
        renderer.init(self)

    def update(self, dt):
        """Update game state for one frame. dt is in seconds."""
        if self.state == "playing":
            self.run_time += dt
            self.frame += 1
            # Per-frame order: input → player → zombie → weapon → projectile
            # → collision → XP → level-up → HUD → render
            player.update(self)
            zombie.update(self, dt)
            weapon.update(self)
            projectile.update(self)
            xp.update(self)
            hud.update(self)
            upgrade.update(self)
            item.update(self)
            renderer.update(self)
        elif self.state == "menu":
            menu.update(self)

    def render(self, screen):
        """Render the current frame to the given pygame Surface."""
        if self.state == "menu":
            self._render_menu(screen)
        elif self.state == "playing":
            self._render_game(screen)

    def _render_menu(self, screen):
        """Render the main menu."""
        screen.fill(config.RENDERER["background_color"])
        # Title
        font = pygame_font(config.MENU["title_font_size"])
        title = font.render(config.DISPLAY["title"], True, (255, 255, 255))
        screen.blit(title, (config.DISPLAY["width"] // 2 - title.get_width() // 2,
                            config.DISPLAY["height"] // 4))
        # Options
        opt_font = pygame_font(config.MENU["option_font_size"])
        for i, option in enumerate(self.menu["options"]):
            color = (255, 255, 0) if i == self.menu["selected"] else (200, 200, 200)
            text = opt_font.render(option, True, color)
            screen.blit(text, (config.DISPLAY["width"] // 2 - text.get_width() // 2,
                               config.DISPLAY["height"] // 2 + i * 50))

    def _render_game(self, screen):
        """Render the game world."""
        screen.fill(config.RENDERER["background_color"])
        # Zombies: pixel-art placeholder (small square in the type's color).
        for z in self.zombies:
            color = config.ZOMBIE["types"][z["type"]]["color"]
            zx = int(z["x"])
            zy = int(z["y"])
            pygame.draw.rect(screen, color, (zx - 4, zy - 4, 8, 8))
        # Player: pixel-art placeholder (small square at its position).
        px = int(self.player["x"])
        py = int(self.player["y"])
        pygame.draw.rect(screen, (255, 255, 255), (px - 4, py - 4, 8, 8))

    def handle_event(self, event):
        """Handle a pygame event. Returns True if the game should quit."""
        if event.type == pygame.QUIT:
            self.running = False
            return True

        if self.state == "menu":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.menu["selected"] = (self.menu["selected"] - 1) % len(self.menu["options"])
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.menu["selected"] = (self.menu["selected"] + 1) % len(self.menu["options"])
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    option = self.menu["options"][self.menu["selected"]]
                    if option == "Play":
                        self.start_run()
                    elif option == "Quit":
                        self.running = False
                        return True
        elif self.state == "playing":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = "paused"
        elif self.state == "paused":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = "playing"
                elif event.key == pygame.K_RETURN:
                    self.start_run()
                elif event.key == pygame.K_q:
                    self.state = "menu"

        return False


def pygame_font(size):
    """Get a pygame font of the given size."""
    return pygame.font.Font(None, size)
