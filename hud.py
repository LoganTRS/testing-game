"""HUD module — HP bar, XP level, timer, kill count, item icons.

T8: the in-run HUD renders the full run state:
  - a player HP bar (remaining life as a proportional fill, not just a number)
  - the 20:00 countdown timer with a milestone at each minute
  - the XP level
  - the kill count (increments on zombie death)
  - item icons for the currently-owned weapons and passives

All layout/positions and colors are read from the config.HUD dict.
"""
import config


def format_timer(elapsed, duration=None):
    """Pure function: format the run countdown as an MM:SS string.

    `elapsed` is the seconds elapsed in the run; `duration` is the total run
    length in seconds (defaults to config.RUN["duration_seconds"]). The result
    is the remaining time, clamped at 0:00, with a milestone at each minute
    (the MM component ticks down once per minute).
    """
    if duration is None:
        duration = config.RUN["duration_seconds"]
    remaining = max(0, int(duration - elapsed))
    minutes, seconds = divmod(remaining, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _hp_bar_fill_width(hp, max_hp):
    """Pure function: the pixel width of the HP bar's remaining-life fill."""
    if max_hp <= 0:
        return 0
    ratio = max(0.0, min(1.0, hp / max_hp))
    return int(round(ratio * config.HUD["hp_bar"]["width"]))


def update(game):
    """Update HUD state. Called each frame during a run."""
    # The kill count is incremented by the zombie module on death; the HUD
    # itself is stateless beyond the kill counter it owns.
    pass


def render(game, screen):
    """Render the HUD overlay onto the given pygame Surface."""
    import pygame

    font = pygame.font.Font(None, config.HUD["font_size"])

    # --- Player HP bar (proportional remaining-life fill) ---
    bar = config.HUD["hp_bar"]
    bx, by = bar["x"], bar["y"]
    bw, bh = bar["width"], bar["height"]
    pygame.draw.rect(screen, bar["background"], (bx, by, bw, bh))
    fill = _hp_bar_fill_width(game.player["hp"], config.PLAYER["max_hp"])
    if fill > 0:
        pygame.draw.rect(screen, bar["color"], (bx, by, fill, bh))
    pygame.draw.rect(screen, bar["border"], (bx, by, bw, bh), 1)

    # --- Timer (right-aligned countdown with a per-minute milestone) ---
    timer = config.HUD["timer"]
    timer_text = font.render(format_timer(game.run_time), True, timer["color"])
    screen.blit(timer_text, (timer["x"] - timer_text.get_width(), timer["y"]))

    # --- XP level ---
    level = config.HUD["level"]
    level_text = font.render(f"LVL {game.xp['level']}", True, level["color"])
    screen.blit(level_text, (level["x"], level["y"]))

    # --- Kill count ---
    kills = config.HUD["kills"]
    kills_text = font.render(f"KILLS {game.hud['kills']}", True, kills["color"])
    screen.blit(kills_text, (kills["x"], kills["y"]))

    # --- Item icons (owned weapons + passives) ---
    icons = config.HUD["icons"]
    size, gap = icons["size"], icons["gap"]
    x = icons["x"]
    y = icons["y"]
    icon_colors = [icons["weapon_color"] for _ in game.weapons] + \
                  [icons["passive_color"] for _ in game.hud.get("passives", [])]
    for color in icon_colors:
        pygame.draw.rect(screen, color, (x, y, size, size))
        x += size + gap


def init(game):
    """Initialize HUD state on game start."""
    game.hud = {
        "kills": 0,
        "passives": [],
    }
