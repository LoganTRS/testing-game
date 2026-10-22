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

    def handle_level_up_pick(self, index):
        """Pick one of the 3 overlay options. Resumes the run when done."""
        if self.state != "level_up" or not self.upgrade["active"]:
            return
        if not 0 <= index < len(self.upgrade["options"]):
            return
        self.upgrade["picked"] = self.upgrade["options"][index]["name"]
        self.upgrade["picks_left"] -= 1
        self.xp["level"] = min(self.xp["level"] + 1, config.XP["max_level"])
        if self.upgrade["picks_left"] <= 0:
            self.upgrade["active"] = False
            self.upgrade["options"] = []
            self.state = "playing"
        else:
            # Multiple picks (high levels / batched level-ups): re-roll.
            self.upgrade["options"] = upgrade.roll_options(
                upgrade.option_pool(), self.rng)

    def handle_level_up_reroll(self):
        """Re-roll the 3 overlay options (1 reroll per level-up)."""
        if self.state != "level_up" or not self.upgrade["active"]:
            return
        if self.upgrade["rerolls_left"] <= 0:
            return
        self.upgrade["rerolls_left"] -= 1
        self.upgrade["options"] = upgrade.roll_options(
            upgrade.option_pool(), self.rng)

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
        elif self.state in ("playing", "level_up"):
            self._render_game(screen)
            if self.state == "level_up":
                self._render_level_up_overlay(screen)

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
        # XP gems: pixel-art placeholder (small square in the config color).
        for gem in self.xp["gems"]:
            gx = int(gem["x"])
            gy = int(gem["y"])
            size = config.ITEM["xp_gem"]["size"]
            pygame.draw.rect(screen, config.ITEM["xp_gem"]["color"],
                             (gx - size // 2, gy - size // 2, size, size))
        # Player: pixel-art placeholder (small square at its position).
        px = int(self.player["x"])
        py = int(self.player["y"])
        pygame.draw.rect(screen, (255, 255, 255), (px - 4, py - 4, 8, 8))

    def _render_level_up_overlay(self, screen):
        """Full-screen 3-card level-up overlay (icon, name, description)."""
        w, h = config.DISPLAY["width"], config.DISPLAY["height"]
        # Dim the world behind the overlay.
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        title_font = pygame_font(config.MENU["title_font_size"] // 2)
        title = title_font.render("LEVEL UP", True, (255, 255, 0))
        screen.blit(title, (w // 2 - title.get_width() // 2, h // 8))

        card_w, card_h = w // 4, h // 2
        gap = (w - 3 * card_w) // 4
        name_font = pygame_font(config.MENU["option_font_size"])
        desc_font = pygame_font(config.HUD["font_size"])
        for i, option in enumerate(self.upgrade["options"][:3]):
            x = gap + i * (card_w + gap)
            y = h // 4
            pygame.draw.rect(screen, (60, 60, 80), (x, y, card_w, card_h))
            pygame.draw.rect(screen, (255, 255, 0), (x, y, card_w, card_h), 2)
            # Icon: pixel-art placeholder square in the card's top area.
            icon_color = (100, 255, 100)
            pygame.draw.rect(screen, icon_color,
                             (x + card_w // 2 - 12, y + 24, 24, 24))
            name = name_font.render(option["name"], True, (255, 255, 255))
            screen.blit(name, (x + card_w // 2 - name.get_width() // 2,
                               y + 64))
            desc = desc_font.render(option["description"], True, (200, 200, 200))
            screen.blit(desc, (x + card_w // 2 - desc.get_width() // 2,
                               y + 100))
            key = desc_font.render(str(i + 1), True, (255, 255, 0))
            screen.blit(key, (x + 12, y + 12))

        reroll_font = pygame_font(config.HUD["font_size"])
        reroll = reroll_font.render(
            "R = reroll ({})".format(self.upgrade["rerolls_left"]),
            True, (200, 200, 200))
        screen.blit(reroll, (w // 2 - reroll.get_width() // 2, h * 3 // 4))

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
        elif self.state == "level_up":
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.handle_level_up_pick(event.key - pygame.K_1)
                elif event.key == pygame.K_r:
                    self.handle_level_up_reroll()
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
