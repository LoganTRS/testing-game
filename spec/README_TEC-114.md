# [LoganTRS/testing-game#18] Spec — Zombie top-down survival (Python/Pygame): v1 spec (consolidated from wayfinding map)

> Routed from GitHub issue **LoganTRS/testing-game#18** (label `spec`).
> Paperclip reference: TEC-114 (id c09d401e-844c-409c-88ab-32e95384e66f).
> Source: https://github.com/LoganTRS/testing-game

---

# Spec — Zombie Top-Down Survival (Python/Pygame), Vampire-Survivors-style

Consolidated from the resolved wayfinding map (TEC-86–91, 93–97). The map is complete; this spec is the single source of truth the `code` tickets are cut from. **No specific file paths** — the architecture section fixes the module boundaries, and the code tickets own the exact files.

## Problem Statement

A player wants a one-session, keyboard-driven survival game in the style of Vampire Survivors: move with WASD/arrows while your weapons auto-fire at a closing horde, kill zombies for XP, level up, pick upgrades, and try to outlast a 20-minute run (or a final boss). It must run at 60 FPS on a laptop with ~1000 zombies on screen, be data-driven (plain `config.py` dicts), and be buildable by an agent via a set of small, ordered `code` tickets.

## Solution

A complete 20-minute survival run, top-down, in Python + Pygame (SDL2) + numpy. The player is a pixel-art survivor in a wrapping (feel-infinite) arena; weapons fire automatically at the nearest zombie; zombies spawn continuously from a ring just outside the camera with a super-linear ramp up to a 1000-zombie hard cap; every zombie drops an XP gem; leveling up pauses the run and offers a 1-of-3 upgrade pick; a boss appears at the end on top of the horde with a telegraph; surviving the full timer is a win, HP 0 is a loss. A single best-run score file persists across runs. The build order, module boundaries, and performance budget are all locked below so the code tickets are unambiguous.

## User Stories

1. As a player, I want to launch the game with `python main.py` and land on a main menu (title, Play, Quit) so that I can start a run with one keypress.
2. As a player, I want to move 8-directionally with WASD (and arrow keys) so that I can dodge the horde from any direction.
3. As a player, I want my weapons to fire automatically at the nearest zombie (no shoot button) so that I can focus purely on movement.
4. As a player, I want the player sprite to face the nearest zombie (cosmetic) so that the action reads clearly.
5. As a player, I want contact with a zombie to damage me with a short invulnerability window so that a single zombie can't kill me in one tick.
6. As a player, I want to pause with Esc and see a pause menu (Resume, Restart, Quit to menu) so that I can take a break or restart without closing the app.
7. As a player, I want the run to be a fixed 20:00 countdown so that "survive" has a concrete, winnable goal.
8. As a player, I want the timer shown on screen with a milestone at each minute so that I can track how long I have left.
9. As a player, I want zombies to spawn continuously from a ring just outside the camera (not in waves) so that the horde pressure is constant and smooth.
10. As a player, I want the spawn rate to scale slightly faster than linearly so that pickups let me outpace a linear curve.
11. As a player, I want a 1000-zombie hard cap (rate flattens at the cap) so that the game stays playable and the machine doesn't melt.
12. As a player, I want the zombie type mix to shift continuously over the 20 minutes — 100% walkers early, runners dominant at the midpoint, brutes dominating late — so that the difficulty ramps in a believable arc.
13. As a player, I want an Elite zombie to appear once at run end and a Boss to spawn at the timer end so that there are two distinct "peak threat" moments.
14. As a player, I want the boss to spawn on top of the horde (spawning continues at reduced rate while it's alive) with a telegraph (banner + screen shake) so that I'm not blindsided.
15. As a player, I want difficulty to feel like a slow build — easy first ~3 minutes, then a steep climb — so that the run has a satisfying pacing curve.
16. As a player, I want every zombie to drop 1 XP gem (elite/boss drop a handful) and a ~60px magnet so that the "juicy" VS loop of killing-for-levels works.
17. As a player, I want a ~linear XP curve to ~level 30 by the 20-minute mark so that my level pacing matches the run length.
18. As a player, I want leveling up to pause the run and present 3 upgrade options (pick 1) so that I have an active, meaningful choice.
19. As a player, I want 1 reroll of the 3 options so that a bad hand doesn't ruin the run.
20. As a player, I want multiple upgrade picks at high levels so that late-game power growth keeps up with the horde.
21. As a player, I want 4 upgrade categories — weapon level, new weapon, passive, evolved weapon — so that every level-up has meaningful options.
22. As a player, I want 4 passives — +damage, +move speed, +magnet radius, -cooldown — so that my build can specialize.
23. As a player, I want weapon evolutions that unlock when a weapon and its paired passive are both at max level so that endgame has "evolved" payoff.
24. As a player, I want 5 weapons available from the start — 9mm Pistol, Hunting Knife (throw), Baton Whirlwind, Sniper Rifle, Flare — so that the run starts with a full kit.
25. As a player, I want all weapons to aim at the nearest zombie so that there is zero aim management.
26. As a player, I want a HUD showing HP, XP level, timer, kill count, and item icons (weapons + passives) so that I have full run state at a glance.
27. As a player, I want a player HP bar so that my remaining life is visible (not just a number).
28. As a player, I want distinct colors per zombie type and a multi-stage decay + death-sprite animation on damage so that I can read the horde's health at a glance.
29. As a player, I want the world to feel infinite (wrapping/looping, no hard walls) so that I'm never pinned against an edge.
30. As a player, I want a top-down scrolling camera that keeps me centered, with subtle camera shake on big hits so that the action feels impactful.
31. As a player, I want a pixel-art visual style so that the game reads as a VS-like title.
32. As a player, I want a full-screen 3-card level-up overlay (icon, name, description) so that upgrade choices are clear.
33. As a player, I want an end screen ("You survived X minutes", Play again, Main menu) with score/time/kills/level so that I see how I did and can immediately replay.
34. As a player, I want my best-run score saved to a single file so that I can track my high score across sessions.
35. As a player, I want SFX (hit, kill, level-up, gem pickup, boss roar) but no music in v1 so that the game has audio feedback without a music pipeline.
36. As a player, I want the game to hold 60 FPS with ~1000 zombies on screen on a laptop so that it stays smooth at the performance budget.
37. As a player, I want the arena to be a wrapping region where all entities stay in-bounds so that nothing escapes the visible field.
38. As a QA person, I want a built-in profiler (toggle: FPS, entity count, frame time) so that I can verify the performance budget.
39. As a QA person, I want a headless test mode (run the loop with no display) so that CI can verify the loop runs.
40. As a QA person, I want unit tests on the XP math and weapon targeting so that the core game rules are regression-protected.
41. As a QA person, I want `test_manual.py` to pass for most tickets so that there's a consistent mechanical acceptance check.
42. As the human owner, I want the final "v1 complete" sign-off to require 3 full human runs that feel right so that difficulty is tuned by play, not guesswork.
43. As the human owner, I want the scope to be exactly v1 (no scope cutting) so that what's specified is what ships.

## Implementation Decisions

- **Tech stack (locked, TEC-94/96):** Python 3.9+, Pygame 2.5+ (SDL2) + numpy only. `python main.py` entry point. No third-party deps in the game loop. Data-driven: all tunables live in `config.py` dicts (plain dicts/lists — no ECS).
- **Architecture (TEC-94):** Flat modules — 12 of them: `main`, `config`, `player`, `zombie`, `weapon`, `projectile`, `xp`, `hud`, `menu`, `upgrade`, `item`, `renderer`. A single `Game` class is constructed in `main` and passed to every module (the modules don't import each other; `Game` is the shared context). All tunables read from `config.py` dicts.
- **Entity model:** Player, zombies, bullets, XP gems, and passives are plain dicts (or lightweight dataclasses backed by the config dicts) with `x`, `y`, `vx`, `vy`, `hp`, and type-specific fields. No inheritance hierarchies; the `zombie` and `weapon` modules dispatch on a `type` key read from config.
- **Run / core loop (TEC-91/86):** A single 20:00 → 0:00 timer. Win = the timer hits 0:00. Lose = player HP hits 0. Boss spawns at the timer end on top of the horde (reduced-rate spawning continues while the boss is alive) with a telegraph. The per-frame order is: input → player update → zombie spawn/update → weapon fire/projectile update → collision (zombie↔bullet, zombie↔player) → XP gem magnet/update → level-up check → HUD → render.
- **Movement & damage (TEC-87):** WASD/arrows 8-directional. Auto-fire (no shoot button). Contact damage with a short i-frame window (VS model). Player faces the nearest zombie (cosmetic; weapons auto-aim independently). Esc = pause (pause menu carries quick restart; no dedicated restart key). No dash.
- **Zombie roster & AI (TEC-88):** Walker (slow/low-HP/filler), Runner (fast/low-HP/chase), Brute (slow/high-HP/wall), Elite (once at run end), Boss (end-of-run). Movement = seek the player (cheap; not flocking). Overlap for the VS "blob" feel with light separation (every-N-frames + spatial-hash fast path). Contact damage + i-frames; no stun/knockback in v1.
- **Weapons (TEC-89):** 5 weapons — 9mm Pistol, Hunting Knife (throw), Baton Whirlwind, Sniper Rifle, Flare. Aim = nearest zombie. All available from the start. Weapon evolutions gated on the weapon and its paired passive both being at max level.
- **Progression (TEC-90):** Every zombie drops 1 XP gem (elite/boss a handful); magnet ~60px. ~linear XP curve to ~level 30 by 20 min. Level-up pauses the run, shows 3 options, 1 reroll. 4 categories: weapon level, new weapon, passive, evolved weapon. 4 passives: +damage, +move speed, +magnet radius, -cooldown. Multiple picks at high levels.
- **Spawning & difficulty (TEC-95):** Continuous rate (not waves/ring) from a ring just outside the camera. Super-linear ramp (slightly faster than linear). 1000-zombie hard cap. Continuous type-mix shift: 100% walkers → runners (peak mid) → brutes (late). Boss on top of the horde with a telegraph. Slow-build difficulty feel.
- **Visuals & HUD (TEC-93):** Top-down scrolling camera (player centered, subtle camera shake). World wraps/loops (no hard walls). Pixel-art style. Distinct color per zombie type; damage shown via several decay stages + a death-sprite animation; player HP bar. HUD: HP + XP level + timer + kill count + item icons (weapons and passives). Full-screen 3-card level-up overlay. SFX only (no music) in v1.
- **Performance (TEC-96):** 60 FPS target; ~1000 zombies on screen at peak. Spatial hash grid over the arena for nearest-zombie auto-aim + bullet collision. Light separation with an empty-cell fast path, computed every-N-frames. Batched zombie sprite blits; cull off-screen zombies for both update and render. Built-in profiler toggle; headless test mode for CI.
- **Persistence (TEC-86):** A single best-run score file; no unlocks.
- **Build order (TEC-97, locked):** scaffold → player → zombie(walker) → all 5 weapons (pistol first) → XP gems → level-up picks → HUD → spawn system (20-min curve) → boss → runner/brute/elite → upgrade passives → audio (SFX) → polish. QA gate per ticket: PR merged + `test_manual.py` passes. Final "v1 complete" ticket = 3 full human runs.
- **Tuning is build-time:** exact spawn-rate numbers, per-weapon stat/hitbox values, level caps, and concrete evolved forms are constants to be tuned at the 3-run sign-off — they live in `config.py` dicts, not in the spec.

## Testing Decisions

- **Good test:** tests external behavior (the returned value, the emitted state, the rendered output at a public boundary) — never the implementation internals.
- **Modules with unit tests (TEC-94):** the XP math (gem accumulation → level-up threshold → which level you're on) and weapon targeting (given a set of zombies, which is "nearest", which weapon fires, cooldown honored). These are pure functions of the config dicts, so they're trivially unit-testable.
- **Prior art:** greenfield — no existing tests. The `test_manual.py` harness is a new seam (a manual-play checklist / headless smoke run) created in the scaffold ticket and extended by each subsequent ticket.
- **Seams:**
  - `xp` module — test the XP/level-up math given a gem count and config; assert the resulting level and whether a level-up fires.
  - `weapon` module — test targeting + fire-cooldown given a zombie list and config; assert which weapon fires at which target.
  - `zombie` module — test the spawn-rate curve given elapsed time and config; assert the zombie count and the type mix at sample timestamps (including the 1000-cap flattening).
  - `main` (headless) — test that the loop runs N frames with no display and no crash, and that the profiler reports sane FPS/entity counts.

## Out of Scope

Multiplayer/online; mobile/touch; content tools (level/weapon editors, modding); non-Python/Pygame engine alternatives; release packaging (PyInstaller/bundling); story/campaign narrative beyond the survival loop; localization/i18n; distribution (Steam/itch.io). Post-run unlocks and music are also out of v1 (single best-run score file; SFX only).

## Further Notes

- The wayfinding map is **complete** — all 10 decision tickets resolved; this spec is the consolidation.
- The code tickets are cut from the **TEC-97 build order** above and published as GitHub issues labeled `code` (the label-router auto-assigns them to an OpenHands agent; the Wayfinder does not work them).
- The 12-module architecture (TEC-94) fixes the module boundaries; each code ticket targets one or a small group of modules in build order.
- Determinism: same seed → same run (seeded RNG) is a VS parity feature; the scaffold ticket should seed the RNG so the headless test mode is reproducible.

