# Forsaken (Pygame)

## Requirements
- Python 3.9+
- pygame (`pip install pygame`)

## Run
From repo root:
- `python cabbage/forsaken.py`

## Round Flow
- Title: press Enter, then choose the killer (Left/Right + Enter)
- 3-second intro shows the killer
- Game: survive, complete generators, or eliminate Noob
- Game Over: click Rematch or press R to restart

## Map
- Three full-width floors (ground, mid, top)
- Portals only way between floors (ends and near-ends)
  - Enter a portal to teleport beside the paired portal, placed on the floor
  - 0.6s cooldown prevents instant re-entry
- Houses on platforms; house windows light when Noob is inside (killer hint)

## Generators (Puzzle)
- Approach a generator (brown box with green slider)
- Press G to start a 3-key sequence (from A/S/D/W/Q/E)
- Type the sequence correctly to complete (-10s timer)
- Wrong key resets that generator’s sequence attempt

## Split Screen
- Always on: left view follows Noob, right view follows Killer
- Central divider; UI overlays on top

## Controls
Noob (Player 1)
- Move A/D, Jump W
- Q: Speed boost x2 (5s, 10s cd)
- E: Invisibility (5s, 10s cd)
- R: Fortify (half speed, take 10% damage, 5s, 30s cd)
- G: Start generator puzzle when close

CoolKid (Killer)
- Move ←/→, Jump ↑
- , (comma): Slash (1s cd)
- / (slash): Dash (up to 4s, 40s cd). Hitting Noob stops dash and deals 40 dmg + explosion FX
- M: Spawn up to 3 clones (10s cd)

1x1x1x1 (Killer)
- Move ←/→, Jump ↑
- , (comma): Entanglement — small flying stun blade (5s stun) (short cd)
- . (period): Melee slash like CoolKid (1s cd)
- / (slash): Mass Infection — fast spinning blade projectile (damage, short cd)
- M: Arrow Ping — green arrow points toward Noob (15s, 40s cd)

## Audio (CoolKid)
Place audio files (if you want music/SFX):
- `cabbage/assets/sounds/coolkid/`
  - `theme_ready_or_not.mp3` (BGM; loops)
  - `slash.ogg`, `dash_start.ogg`, `dash_hit_explosion.ogg`, `clone_spawn.ogg` (SFX)

Helper to download placeholders/BGM links:
- `python cabbage/tools/download_coolkid_audio.py`

## Tips
- Noob: use R before big hits; Q to reach gaps; E to avoid slashes
- CoolKid: time dash to land the 40-dmg hit; clones to pressure
- 1x1x1x1: use long-range blade (/) to control lanes; ping (M) to track Noob

## Troubleshooting
- No audio: verify files are in `cabbage/assets/sounds/coolkid`, and try `pygame.mixer.init` defaults (already enabled). If needed, set `SDL_AUDIODRIVER=directsound` on Windows.
- Split screen squished: the game renders native half-width panes (no scaling). Ensure window is large enough (1100x700 default).
