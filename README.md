# Forsaken (Pygame)

## Requirements
- Python 3.9+
- pygame (`pip install pygame`)

## How to Run
- From the repo root:
  - `python cabbage/forsaken.py`

## Controls
- Noob (Player 1)
  - Move: A / D
  - Jump: W
  - Q: Speed boost (x2) — 5s, 10s cooldown
  - E: Invisibility — 5s, 10s cooldown
  - R: Fortify (half speed, take 10% damage, grey overlay) — 5s, 30s cooldown
- CoolKid (Player 2 / Boss)
  - Move: Arrow Left / Right
  - Jump: Arrow Up
  - / (slash): Dash — lasts up to 4s, 40s cooldown; on hit stops dash, deals 40 damage, plays explosion
  - , (comma): Sword slash — short range, 1s cooldown
  - M: Spawn up to 3 clones (auto-chase and slash; despawn after 15s)

## Objective
- Survive until the timer reaches 0 (Noob wins), or drop your opponent's HP to 0.
- If CoolKid falls into the void, Noob immediately wins.
- Win screen includes confetti:
  - CoolKid wins: red confetti
  - Noob wins: blue/green/yellow confetti

## UI
- Top center: survive timer
- Top left: Noob HP bar (fixed on screen)
- Cooldowns: colored ticks above characters

## World & Camera
- Theme: Night circus with stars, rainbow tents, and market stalls
- Platforming: multiple striped platforms; jumping height boosted 1.5x
- Dynamic camera: follows Noob; zooms out and re-centers so CoolKid stays visible before getting cut off

## Tips
- Noob: Use R before big hits; Q to cross gaps; E to avoid slashes
- CoolKid: Dash to close distance, time it to trigger the 40-damage explosion; use clones to pressure Noob

## Troubleshooting
- If window is very small or zoom changes feel abrupt, consider adjusting `margin`, `view_scale` min, or gravity/jump values in `forsaken.py`.
