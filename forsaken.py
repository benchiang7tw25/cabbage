import pygame, sys, time, random
import os
import math # Added for blade projectile rotation
#v3.0.1-audio
pygame.init()
# Initialize audio mixer
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except Exception:
    pass
WIDTH, HEIGHT = 1100, 700
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Forsaken")

# Colors
WHITE = (255,255,255)
BLACK = (0,0,0)
SKY = (20,24,48)  # night sky
YELLOW = (255,255,0)
BLUE = (0,0,255)
GREEN = (0,200,0)
RED = (200,0,0)
GRAY = (150,150,150)
SKIN = (255,224,189)
GOLD = (255,215,0)
PURPLE = (140, 0, 140)
DARK_RED = (120, 0, 0)
MID_BLUE = (40, 60, 160)

clock = pygame.time.Clock()
FONT = pygame.font.SysFont("Arial", 24)
BIG = pygame.font.SysFont("Arial", 72, bold=True)
PRESS_FONT = pygame.font.SysFont("Arial", 28, bold=True)

# Map / platforms
# Three full-width floors (ground + 2 upper solid floors)
platforms = [
    pygame.Rect(0, HEIGHT-50, 3000, 50),   # Floor 1: ground
    pygame.Rect(0, 380, 3000, 60),         # Floor 2: middle (thicker)
    pygame.Rect(0, 210, 3000, 60),         # Floor 3: top (thicker)
]
# clouds (for parallax) -> convert to stars for night
stars = [(random.randint(0, 3000), random.randint(20, 180), random.randint(1,3)) for _ in range(120)]

# Starting barrier
barrier = pygame.Rect(50, HEIGHT-150, 20, 100)

# Game constants
GRAVITY = 0.65
NOOB_MAX_HP = 100
GAME_DURATION = 180  # seconds to survive

# cooldown dict stores next-ready timestamps
cooldowns = {
    "noob_speed": 0.0,     # Q: duration 5s, cd 10s
    "noob_invis": 0.0,     # E: duration 5s, cd 10s
    "noob_reduce": 0.0,    # R: duration 5s, cd 30s (slow + 90% damage reduction)
    "coolkid_dash": 0.0,   # /: duration 4s, cd 40s OR used as 1x1x1x1 blade cooldown
    "coolkid_slash": 0.0,  # ,: cd 1s (CoolKid slash)
    "coolkid_clone": 0.0,  # m: cd 10s
    "clone_slash": 0.0,    # clone own slash cd 1s
    "one_stun": 0.0,       # 1x1x1x1 comma stun blade cooldown
    "one_slash": 0.0,      # 1x1x1x1 period melee slash cooldown
    "one_arrow": 0.0       # 1x1x1x1 M arrow ping cooldown
}

ability_colors = {
    "noob_speed": (0,255,0),
    "noob_invis": (0,0,0),
    "coolkid_dash": (255,0,0),
    "coolkid_clone": (255,165,0),
    "coolkid_slash": (0,0,0),
    "clone_slash": (80,80,80)
}

# Helper: draw cooldown bar above a player
def draw_cooldowns(player_x, player_y, abil_list, x_off, y_off):
    bar_w, bar_h = 42, 6
    for i, ab in enumerate(abil_list):
        now = time.time()
        cd_left = max(0, cooldowns.get(ab,0) - now)
        # define expected max cooldowns for bar lengths
        if ab in ("coolkid_slash","clone_slash"):
            max_cd = 1
        elif ab == "coolkid_dash":
            max_cd = 40
        elif ab == "noob_reduce":
            max_cd = 30
        elif ab == "one_arrow":
            max_cd = 40
        else:
            max_cd = 10
        ratio = 1 - min(1, cd_left / max_cd)  # filled ratio
        # background
        pygame.draw.rect(win, GRAY, (player_x + x_off, player_y + y_off + i*10, bar_w, bar_h))
        pygame.draw.rect(win, ability_colors.get(ab,(255,255,255)),
                         (player_x + x_off, player_y + y_off + i*10, int(bar_w * ratio), bar_h))

# Player classes
class Player:
    def __init__(self, x, y, is_noob=False):
        self.x = x
        self.y = y
        self.w = 40
        self.h = 60
        self.is_noob = is_noob
        self.base_speed = 5
        self.speed = self.base_speed
        self.vel_y = 0
        self.on_ground = False
        self.invisible = False
        self.hp = NOOB_MAX_HP if is_noob else 999
        self.stun_until = 0.0
        # slash visuals
        self.slash_line = None
        self.slash_end_time = 0.0
        self.slash_spawn_time = 0.0
        self.has_hit = False
        # clone flag
        self.is_clone = False
        # dash flags for coolkid
        self.dash_active = False
        self.dash_end = 0.0
        self.dash_has_hit = False
        # facing: -1 left, 1 right
        self.facing_dir = 1
        # last frame y for top-landing detection
        self.last_y = y
        self.variant = "CoolKid"  # or "1x1x1x1"

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def apply_gravity(self):
        # remember last y before moving
        self.last_y = self.y
        self.y += self.vel_y
        self.vel_y += GRAVITY
        if self.vel_y > 12:
            self.vel_y = 12

    def check_platforms(self, plats):
        r = self.rect()
        self.on_ground = False
        for p in plats:
            # vertical landing check: crossed top this frame while moving downward
            last_bottom = self.last_y + self.h
            cur_bottom = r.bottom
            if self.vel_y >= 0 and last_bottom <= p.top + 2 and cur_bottom >= p.top and r.right > p.left and r.left < p.right:
                # snap on top
                self.y = p.top - self.h
                self.vel_y = 0
                self.on_ground = True
                # refresh rect after snapping to avoid multiple triggers
                r = self.rect()
            # ceiling collision: prevent jumping up through floors
            last_top = self.last_y
            cur_top = r.top
            if self.vel_y < 0 and last_top >= p.bottom - 2 and cur_top <= p.bottom and r.right > p.left and r.left < p.right:
                # hit the underside; stop upward movement and place just below
                self.y = p.bottom
                self.vel_y = 0
                r = self.rect()

    def move_input(self, keys, left_key, right_key, jump_key, barrier_rect=None):
        # don't move if stunned
        if time.time() < self.stun_until:
            return
        if keys[left_key]:
            # check barrier
            if not barrier_rect or (self.x - self.speed) > (barrier_rect[0] + barrier_rect[2]):
                self.x -= self.speed
                self.facing_dir = -1
        if keys[right_key]:
            self.x += self.speed
            self.facing_dir = 1
        if keys[jump_key] and self.on_ground:
            self.vel_y = -18
            self.on_ground = False

    def draw(self, offset_x):
        # draw player; if noob, split head/torso/pants
        if self.is_noob:
            # head (yellow)
            head_x = self.x - offset_x + 4
            head_y = self.y
            head_w = self.w-8
            head_h = 18
            pygame.draw.rect(win, YELLOW, (head_x, head_y, head_w, head_h))
            # face on head (eyes + mouth)
            eye_r = 2
            # squint if stunned
            is_squint = time.time() < self.stun_until
            eye_y = head_y + head_h//2 - (1 if is_squint else 3)
            eye_lx = head_x + head_w//3
            eye_rx = head_x + 2*head_w//3
            if is_squint:
                pygame.draw.line(win, BLACK, (int(eye_lx-2), int(eye_y)), (int(eye_lx+2), int(eye_y)), 2)
                pygame.draw.line(win, BLACK, (int(eye_rx-2), int(eye_y)), (int(eye_rx+2), int(eye_y)), 2)
            else:
                pygame.draw.circle(win, BLACK, (int(eye_lx), int(eye_y)), eye_r)
                pygame.draw.circle(win, BLACK, (int(eye_rx), int(eye_y)), eye_r)
            mouth_y = head_y + head_h - 5
            pygame.draw.line(win, BLACK, (head_x + head_w//3, mouth_y), (head_x + 2*head_w//3, mouth_y), 2)
            # subtle top shadow on head
            shadow = pygame.Surface((head_w, head_h//2), pygame.SRCALPHA)
            shadow.fill((0,0,0,40))
            win.blit(shadow, (head_x, head_y))
            # torso (blue)
            pygame.draw.rect(win, BLUE, (self.x - offset_x, self.y + 18, self.w, 26))
            # pants (green)
            pygame.draw.rect(win, GREEN, (self.x - offset_x, self.y + 44, self.w, 16))
            if self.invisible:
                # overlay to show invisibility
                s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
                s.fill((255,255,255,120))
                win.blit(s, (self.x - offset_x, self.y))
        else:
            # killer visuals
            if getattr(self, 'variant', 'CoolKid') == '1x1x1x1':
                # green body
                body_rect = pygame.Rect(self.x - offset_x, self.y, self.w, self.h)
                pygame.draw.rect(win, (0,180,0), body_rect)
                pygame.draw.rect(win, (0,100,0), body_rect, 2)
                # red + eye
                cx = self.x - offset_x + self.w//2
                cy = self.y + self.h//3
                pygame.draw.line(win, (220,0,0), (cx-6, cy), (cx+6, cy), 3)
                pygame.draw.line(win, (220,0,0), (cx, cy-6), (cx, cy+6), 3)
                # three dominos on head
                for i in range(3):
                    pygame.draw.rect(win, (30,30,30), (self.x - offset_x + 6 + i*10, self.y - 10 - i*2, 8, 12))
                # black smile
                pygame.draw.line(win, (0,0,0), (self.x - offset_x + self.w//4, self.y + 2*self.h//3), (self.x - offset_x + 3*self.w//4, self.y + 2*self.h//3), 3)
            else:
                # original CoolKid red face
                body_rect = pygame.Rect(self.x - offset_x, self.y, self.w, self.h)
                pygame.draw.rect(win, RED, body_rect)
                pygame.draw.rect(win, (120,0,0), body_rect, 2)
                shade = pygame.Surface((self.w//3, self.h), pygame.SRCALPHA)
                shade.fill((0,0,0,60))
                win.blit(shade, (self.x - offset_x + 2*self.w//3, self.y))
                eye_r = 6
                eye_y = self.y + self.h//3
                eye_lx = self.x - offset_x + self.w//3
                eye_rx = self.x - offset_x + 2*self.w//3
                pygame.draw.circle(win, BLACK, (int(eye_lx), int(eye_y)), eye_r)
                pygame.draw.circle(win, BLACK, (int(eye_rx), int(eye_y)), eye_r)
                pygame.draw.circle(win, WHITE, (int(eye_lx - 2), int(eye_y - 2)), 2)
                pygame.draw.circle(win, WHITE, (int(eye_rx - 2), int(eye_y - 2)), 2)
                mouth_y = self.y + 2*self.h//3
                pygame.draw.line(win, BLACK, (self.x - offset_x + self.w//4, mouth_y), (self.x - offset_x + 3*self.w//4, mouth_y), 3)
        # slash drawing (if active)
        if self.slash_line:
            a, b = self.slash_line
            pygame.draw.line(win, BLACK, (a[0] - offset_x, a[1]), (b[0] - offset_x, b[1]), 8)

# Slash as lightweight struct in this code base (we draw lines directly on owner.slash_line)
# We'll keep slashes attached to owners

# Create players
noob = Player(100, HEIGHT - 150, is_noob=True)
# coolkid will be created after killer selection
coolkid = None
clones = []
selected_killer = "CoolKid"  # default

# Random Noob spawn points
NOOB_SPAWNS = [(120, HEIGHT-150), (600, 460), (900, 400), (1300, 340), (1700, 430), (2100, 330), (2450, 250)]

# Title screen with killer selection

def title_screen():
    # splash
    while True:
        win.fill(SKY)
        pygame.draw.circle(win, (255,255,0), (140,100), 30)
        for sx, sy, sr in stars:
            pygame.draw.circle(win, (240, 240, 200), (sx, sy), sr)
        title_text = BIG.render("FORSAKEN", True, WHITE)
        win.blit(title_text, (WIDTH//2 - title_text.get_width()//2, 140))
        press = PRESS_FONT.render("Press ENTER", True, WHITE)
        win.blit(press, (WIDTH//2 - press.get_width()//2, 280))
        pygame.display.update()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                break
        else:
            continue
        break
    # selection menu
    killer_select()

def killer_select():
    global selected_killer
    options = ["CoolKid", "1x1x1x1"]
    idx = 0
    while True:
        win.fill(SKY)
        for sx, sy, sr in stars:
            pygame.draw.circle(win, (240, 240, 200), (sx, sy), sr)
        title_text = PRESS_FONT.render("Choose Killer", True, GOLD)
        win.blit(title_text, (WIDTH//2 - title_text.get_width()//2, 120))
        # options with simple face preview
        for i, name in enumerate(options):
            col = GOLD if i == idx else WHITE
            txt = PRESS_FONT.render(name, True, col)
            x = WIDTH//2 - (len(options)*220)//2 + i*220
            y = 200
            win.blit(txt, (x, y))
            # draw preview box
            preview = pygame.Rect(x, y+40, 80, 100)
            pygame.draw.rect(win, (255,255,255), preview, 2)
            if name == 'CoolKid':
                pygame.draw.rect(win, RED, (preview.x+10, preview.y+20, 60, 60))
                pygame.draw.circle(win, BLACK, (preview.x+28, preview.y+46), 6)
                pygame.draw.circle(win, BLACK, (preview.x+52, preview.y+46), 6)
            else:
                pygame.draw.rect(win, (0,180,0), (preview.x+10, preview.y+20, 60, 60))
                cx = preview.x+40; cy = preview.y+50
                pygame.draw.line(win, (220,0,0), (cx-6, cy), (cx+6, cy), 3)
                pygame.draw.line(win, (220,0,0), (cx, cy-6), (cx, cy+6), 3)
        button = PRESS_FONT.render("Enter to Confirm", True, WHITE)
        win.blit(button, (WIDTH//2 - button.get_width()//2, 360))
        pygame.display.update()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_LEFT:
                    idx = (idx - 1) % len(options)
                if ev.key == pygame.K_RIGHT:
                    idx = (idx + 1) % len(options)
                if ev.key == pygame.K_RETURN:
                    selected_killer = options[idx]
                    return
# start
title_screen()
# instantiate killer after selection
if selected_killer == "CoolKid":
    coolkid = Player(300, HEIGHT - 150, is_noob=False)
    coolkid.variant = "CoolKid"
else:
    coolkid = Player(300, HEIGHT - 150, is_noob=False)
    coolkid.variant = "1x1x1x1"
    coolkid.base_speed = int(coolkid.base_speed * 0.85) if isinstance(coolkid.base_speed, int) else coolkid.base_speed * 0.85
    coolkid.speed = coolkid.base_speed

# Randomize Noob spawn
noob_spawn = random.choice(NOOB_SPAWNS)
noob.x, noob.y = noob_spawn[0], noob_spawn[1]

# Round intro (3s) showing killer face and text
intro_until = time.time() + 3.0
while time.time() < intro_until:
    win.fill(SKY)
    # killer face preview center
    face_rect = pygame.Rect(WIDTH//2 - 60, HEIGHT//2 - 100, 120, 160)
    if selected_killer == '1x1x1x1':
        pygame.draw.rect(win, (0,180,0), face_rect)
        pygame.draw.rect(win, (0,100,0), face_rect, 3)
        cx = face_rect.centerx; cy = face_rect.top + 55
        pygame.draw.line(win, (220,0,0), (cx-10, cy), (cx+10, cy), 4)
        pygame.draw.line(win, (220,0,0), (cx, cy-10), (cx, cy+10), 4)
        for i in range(3):
            pygame.draw.rect(win, (30,30,30), (face_rect.left + 12 + i*16, face_rect.top - 14 - i*3, 12, 16))
        title = PRESS_FONT.render("This round's killer is 1x1x1x", True, (0,220,100))
    else:
        pygame.draw.rect(win, RED, face_rect)
        pygame.draw.rect(win, (120,0,0), face_rect, 3)
        pygame.draw.circle(win, BLACK, (face_rect.left+38, face_rect.top+55), 10)
        pygame.draw.circle(win, BLACK, (face_rect.right-38, face_rect.top+55), 10)
        title = PRESS_FONT.render("This round's killer is CoolKid", True, (255,180,180))
    win.blit(title, (WIDTH//2 - title.get_width()//2, face_rect.bottom + 16))
    pygame.display.update()
    clock.tick(60)

# === Audio: CoolKid sounds & music ===
coolkid_snd_dir = os.path.join("cabbage", "assets", "sounds", "coolkid")
def load_snd(name):
    try:
        path = os.path.join(coolkid_snd_dir, name)
        if os.path.exists(path):
            return pygame.mixer.Sound(path)
    except Exception:
        return None
    return None

snd_slash = load_snd("slash.ogg")
snd_dash = load_snd("dash_start.ogg")
snd_explosion = load_snd("dash_hit_explosion.ogg")
snd_clone = load_snd("clone_spawn.ogg")
snd_punch = load_snd("punch.ogg")

def play(snd, vol=1.0):
    try:
        if snd:
            snd.set_volume(vol)
            snd.play()
    except Exception:
        pass

# Start BGM if CoolKid
if selected_killer == "CoolKid":
    try:
        bgm_path = os.path.join(coolkid_snd_dir, "theme_ready_or_not.mp3")
        if os.path.exists(bgm_path) and pygame.mixer.get_init():
            pygame.mixer.music.load(bgm_path)
            pygame.mixer.music.set_volume(0.6)
            pygame.mixer.music.play(-1)
    except Exception:
        pass

start_time = time.time()
# time bonus (seconds) gained from generators
bonus_time = 0

# main loop
running = True
camera_x = 0

# for ability durations we use timers via 'active_until' values:
noob_speed_until = 0.0
noob_invis_until = 0.0
coolkid_dash_until = 0.0
noob_reduce_until = 0.0

# fx timers/flags
noob_explosion_until = 0.0
confetti = []  # list of particles: {x,y,vx,vy,color,life}
# Projectiles for 1x1x1x1
projectiles = []  # each: {x,y,vx,vy,ttl,kind}
# Portals between floors (pairs). Each is a dict: rect and target (x,y)
portals = [
    {"rect": pygame.Rect(40, HEIGHT-110, 40, 60),  "to": (2800, 380)},  # Floor1 left -> Floor2 right (to.y is floor top)
    {"rect": pygame.Rect(2920, HEIGHT-110, 40, 60), "to": (80, 380)},   # Floor1 right -> Floor2 left
    {"rect": pygame.Rect(40, 320, 40, 60),          "to": (2800, 210)}, # Floor2 left -> Floor3 right
    {"rect": pygame.Rect(2920, 320, 40, 60),        "to": (80, 210)},   # Floor2 right -> Floor3 left
    # new: back to Floor1 from Floor2 (use slightly offset x to avoid overlapping with existing portals)
    {"rect": pygame.Rect(100, 320, 40, 60),         "to": (2880, HEIGHT-50)}, # Floor2 near-left -> Floor1 near-right
    {"rect": pygame.Rect(2860, 320, 40, 60),        "to": (120, HEIGHT-50)},  # Floor2 near-right -> Floor1 near-left
    # new: back to Floor1 from Floor3
    {"rect": pygame.Rect(40, 150, 40, 60),          "to": (2800, HEIGHT-50)}, # Floor3 left -> Floor1 right
    {"rect": pygame.Rect(2920, 150, 40, 60),        "to": (80, HEIGHT-50)},   # Floor3 right -> Floor1 left
]
# Cute houses placed on floors: (x,y,w,h)
houses = [
    (500, HEIGHT-120, 120, 70), (1300, HEIGHT-120, 120, 70), (2200, HEIGHT-120, 120, 70),
    (800, 330, 120, 70), (1900, 330, 120, 70),
    (600, 160, 120, 70), (1700, 160, 120, 70)
]
# 1x1x1x1 arrow ping state
arrow_hint_until = 0.0
# portal cooldowns to prevent instant re-trigger
noob_portal_cd_until = 0.0
coolkid_portal_cd_until = 0.0

# Generators: 5 brown boxes with green slider
class Generator:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 50, 40)
        self.progress = 0.0
        self.done = False
        self.active = False
        self.sequence = []  # list of pygame key constants
        self.index = 0
    def start_puzzle(self):
        if self.done:
            return
        import random as _r
        keys_pool = [pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_w, pygame.K_q, pygame.K_e]
        self.sequence = [_r.choice(keys_pool) for _ in range(3)]
        self.index = 0
        self.active = True
    def input_key(self, key):
        if not self.active or self.done:
            return False
        expected = self.sequence[self.index]
        if key == expected:
            self.index += 1
            if self.index >= len(self.sequence):
                self.done = True
                self.active = False
            return True
        else:
            # reset on wrong input
            self.index = 0
            return False
    def draw(self, cam_x):
        # base box
        pygame.draw.rect(win, (150,75,0), (self.rect.x - cam_x, self.rect.y, self.rect.w, self.rect.h))
        pygame.draw.rect(win, (80,40,0), (self.rect.x - cam_x, self.rect.y, self.rect.w, self.rect.h), 2)
        # slider/progress bar (kept as visual aid for completion status)
        bar_x, bar_y, bar_w, bar_h = self.rect.x - cam_x + 6, self.rect.y + 12, self.rect.w - 12, 12
        pygame.draw.rect(win, (40,40,40), (bar_x, bar_y, bar_w, bar_h))
        fill = 1.0 if self.done else (self.index / max(1,len(self.sequence)) if self.active else 0.0)
        fill_w = int(bar_w * fill)
        pygame.draw.rect(win, (0,200,60), (bar_x, bar_y, fill_w, bar_h))
        pygame.draw.rect(win, WHITE, (bar_x, bar_y, bar_w, bar_h), 2)
        # sequence text
        if self.active and not self.done:
            labels = {pygame.K_a:'A', pygame.K_s:'S', pygame.K_d:'D', pygame.K_w:'W', pygame.K_q:'Q', pygame.K_e:'E'}
            txt = ' '.join(labels[k] for k in self.sequence)
            col = WHITE
            surf = FONT.render(txt, True, col)
            win.blit(surf, (self.rect.x - cam_x - 10, self.rect.y - 24))
        elif self.done:
            surf = FONT.render('OK', True, (0,220,80))
            win.blit(surf, (self.rect.x - cam_x + 10, self.rect.y - 24))

# instantiate generators
generators = [
    Generator(350, HEIGHT-90),
    Generator(780, 440),
    Generator(1280, 380),
    Generator(1760, 440),
    Generator(2360, 280),
]
# Snap generators to nearest platform top under their x-span
for gen in generators:
    gx_center = gen.rect.centerx
    # find candidate platforms aligned horizontally
    candidates = [p for p in platforms if p.left <= gx_center <= p.right]
    if candidates:
        # choose the highest platform (smallest top) that is below current y
        under = [p for p in candidates if p.top >= 0]
        if under:
            target = min(under, key=lambda p: p.top)
            gen.rect.y = target.top - gen.rect.height

# active generator reference
active_generator = None

while running:
    dt = clock.tick(60) / 1000.0
    now = time.time()
    keys = pygame.key.get_pressed()

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if ev.type == pygame.KEYDOWN:
            # generator puzzle input
            if active_generator and not active_generator.done:
                before = active_generator.index
                progressed = active_generator.input_key(ev.key)
                if active_generator.done and progressed:
                    bonus_time += 10
                    active_generator = None
            # begin puzzle when pressing G near a generator
            if ev.key == pygame.K_g:
                for gen in generators:
                    if gen.done:
                        continue
                    if noob.rect().inflate(30,20).colliderect(gen.rect):
                        gen.start_puzzle()
                        active_generator = gen
                        break
            # CoolKid clones on keydown to improve reliability
            if selected_killer == "CoolKid" and ev.key == pygame.K_m and now > cooldowns["coolkid_clone"]:
                if len(clones) < 3:
                    # spawn one clone per press; alternate sides
                    off = 50 if (len(clones) % 2 == 0) else -50
                    c = Player(coolkid.x + off, coolkid.y, is_noob=False)
                    c.is_clone = True
                    c.base_speed = coolkid.base_speed / 3.0
                    c.speed = c.base_speed
                    clones.append({"p": c, "spawn": now})
                    play(snd_clone, 0.9)
                cooldowns["coolkid_clone"] = now + 10.0
            # CoolKid slash on keydown (comma)
            if selected_killer == "CoolKid" and ev.key == pygame.K_COMMA and now > cooldowns["coolkid_slash"]:
                sx = coolkid.x + coolkid.w // 2
                sy = coolkid.y + coolkid.h // 2
                length = 160
                if getattr(coolkid, 'facing_dir', 1) >= 0:
                    coolkid.slash_line = ((sx, sy), (sx + length, sy))
                else:
                    coolkid.slash_line = ((sx, sy), (sx - length, sy))
                coolkid.slash_spawn_time = now
                coolkid.slash_end_time = now + 0.6
                coolkid.has_hit = False
                cooldowns["coolkid_slash"] = now + 1.0
                play(snd_slash, 0.8)
            # 1x1x1x1 M: arrow ping towards Noob
            if selected_killer == "1x1x1x1" and ev.key == pygame.K_m and now > cooldowns["one_arrow"]:
                arrow_hint_until = now + 15.0
                cooldowns["one_arrow"] = now + 40.0

    # ------- input & abilities -------
    # Noob controls: A D W ; Q (speed), E (invis)
    noob.move_input(keys, pygame.K_a, pygame.K_d, pygame.K_w, barrier)
    # CoolKid controls: arrows ; / is K_SLASH, comma is K_COMMA, m spawn clone
    coolkid.move_input(keys, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, barrier)

    # Determine move directions for camera logic (-1 left, 1 right, 0 idle)
    noob_move_dir = (-1 if keys[pygame.K_a] else 0) + (1 if keys[pygame.K_d] else 0)
    coolkid_move_dir = (-1 if keys[pygame.K_LEFT] else 0) + (1 if keys[pygame.K_RIGHT] else 0)

    # Activate Noob speed Q (dur 5s, cd 10s)
    if keys[pygame.K_q] and now > cooldowns["noob_speed"]:
        noob_speed_until = now + 5.0
        cooldowns["noob_speed"] = now + 10.0
        noob.speed = noob.base_speed * 2

    # Activate Noob invis E (dur 5s, cd 10s)
    if keys[pygame.K_e] and now > cooldowns["noob_invis"]:
        noob_invis_until = now + 5.0
        cooldowns["noob_invis"] = now + 10.0
        noob.invisible = True

    # Activate Noob reduce-damage + slow R (dur 5s, cd 30s)
    if keys[pygame.K_r] and now > cooldowns["noob_reduce"]:
        noob_reduce_until = now + 5.0
        cooldowns["noob_reduce"] = now + 30.0
        noob.speed = max(1, noob.base_speed // 2) if isinstance(noob.base_speed, int) else noob.base_speed * 0.5

    # CoolKid dash (duration 4s, cd 40s) bound to slash key (/)
    if keys[pygame.K_SLASH] and now > cooldowns["coolkid_dash"] and selected_killer == "CoolKid":
        coolkid_dash_until = now + 4.0
        cooldowns["coolkid_dash"] = now + 40.0
        coolkid.dash_active = True
        coolkid.dash_end = coolkid_dash_until
        coolkid.speed = coolkid.base_speed * 5
        coolkid.dash_has_hit = False
        play(snd_dash, 0.9)

    # 1x1x1x1 abilities
    if selected_killer == "1x1x1x1":
        # comma: little flying sword that stuns Noob (no damage)
        if keys[pygame.K_COMMA] and now > cooldowns["one_stun"]:
            sx = coolkid.x + coolkid.w//2
            sy = coolkid.y + coolkid.h//3
            dirx = 1 if getattr(coolkid,'facing_dir',1) >= 0 else -1
            projectiles.append({
                "kind":"stun_blade",
                "x": sx,
                "y": sy,
                "vx": 12*dirx,
                "vy": 0,
                "ttl": now + 1.0,
                "len": 60,
                "wid": 12,
                "angle": 0.0,
                "spin": 12.0 * dirx,
                "trail": []
            })
            cooldowns["one_stun"] = now + 0.8
        # slash: period '.' melee slash like CoolKid
        if keys[pygame.K_PERIOD] and now > cooldowns["one_slash"]:
            sx = coolkid.x + coolkid.w // 2
            sy = coolkid.y + coolkid.h // 2
            length = 160
            if getattr(coolkid, 'facing_dir', 1) >= 0:
                coolkid.slash_line = ((sx, sy), (sx + length, sy))
            else:
                coolkid.slash_line = ((sx, sy), (sx - length, sy))
            coolkid.slash_spawn_time = now
            coolkid.slash_end_time = now + 0.6
            coolkid.has_hit = False
            cooldowns["one_slash"] = now + 1.0
        # mass infection: anime blade projectile on '/' key, uses coolkid_dash cooldown slot
        if keys[pygame.K_SLASH] and now > cooldowns["coolkid_dash"]:
            sx = coolkid.x + coolkid.w//2
            sy = coolkid.y + coolkid.h//2
            dirx = 1 if getattr(coolkid,'facing_dir',1) >= 0 else -1
            projectiles.append({
                "kind":"blade",
                "x": sx,
                "y": sy,
                "vx": 14*dirx,
                "vy": 0,
                "ttl": now + 1.2,
                "len": 90,
                "wid": 18,
                "angle": 0.0,
                "spin": 9.0 * dirx,
                "trail": []
            })
            cooldowns["coolkid_dash"] = now + 3.0
        # black sword slash (N key) short range
        if keys[pygame.K_n] and now > cooldowns["clone_slash"]:
            sx = coolkid.x + coolkid.w // 2
            sy = coolkid.y + coolkid.h // 2
            length = 140
            if getattr(coolkid, 'facing_dir', 1) >= 0:
                coolkid.slash_line = ((sx, sy), (sx + length, sy))
            else:
                coolkid.slash_line = ((sx, sy), (sx - length, sy))
            coolkid.slash_spawn_time = now
            coolkid.slash_end_time = now + 0.5
            coolkid.has_hit = False
            cooldowns["clone_slash"] = now + 1.0

    # Spawn clones (M) cd 10s, create up to 3 clones
    if selected_killer == "CoolKid" and keys[pygame.K_m] and now > cooldowns["coolkid_clone"]:
        # clear old clones if too many
        if len(clones) < 3:
            spawn_offsets = [50, -50, 100, -100]
            for off in spawn_offsets:
                if len(clones) >= 3:
                    break
                c = Player(coolkid.x + off, coolkid.y, is_noob=False)
                c.is_clone = True
                c.base_speed = coolkid.base_speed / 3.0
                c.speed = c.base_speed
                clones.append({"p": c, "spawn": now})
        cooldowns["coolkid_clone"] = now + 10.0

    # ------- durations expiry -------
    if noob_speed_until and now >= noob_speed_until:
        noob.speed = noob.base_speed
        noob_speed_until = 0.0
    if noob_invis_until and now >= noob_invis_until:
        noob.invisible = False
        noob_invis_until = 0.0
    # reset speed after R ends (but don't override active speed boost)
    if noob_reduce_until and now >= noob_reduce_until:
        noob_reduce_until = 0.0
        if not noob_speed_until or now >= noob_speed_until:
            noob.speed = noob.base_speed
    if coolkid.dash_active and now >= coolkid.dash_end:
        coolkid.dash_active = False
        coolkid.speed = coolkid.base_speed
        coolkid.dash_has_hit = False

    # ------- physics -------
    # apply gravity and collisions
    moving_entities = [noob, coolkid] + [c["p"] for c in clones]
    for p in moving_entities:
        if p:
            p.apply_gravity()
            p.check_platforms(platforms)
    # Portal teleport (only way between floors)
    def try_teleport(player, who):
        global noob_portal_cd_until, coolkid_portal_cd_until
        prect = player.rect()
        # respect per-player cooldown
        if who == 'noob' and now < noob_portal_cd_until:
            return
        if who == 'coolkid' and now < coolkid_portal_cd_until:
            return
        for prt in portals:
            if prect.colliderect(prt["rect"]):
                tx, ty = prt["to"]
                # spawn BESIDE destination portal to avoid immediate re-trigger
                # decide offset direction based on destination x (left or right edge portals)
                if tx <= 200:
                    spawn_x = tx + 80  # to the right of the portal
                elif tx >= 2800:
                    spawn_x = tx - 80 - player.w  # to the left of the portal
                else:
                    spawn_x = tx + 80
                player.x = spawn_x
                player.y = ty - player.h  # stand on floor top
                player.vel_y = 0
                # set cooldown
                if who == 'noob':
                    noob_portal_cd_until = now + 0.6
                elif who == 'coolkid':
                    coolkid_portal_cd_until = now + 0.6
                break
    try_teleport(noob, 'noob')
    try_teleport(coolkid, 'coolkid')
    for cinfo in clones:
        try_teleport(cinfo["p"], 'clone')

    # Update projectiles (1x1x1x1)
    if projectiles:
        kept_proj = []
        for pr in projectiles:
            # motion
            pr["x"] += pr.get("vx",0) * (1)
            pr["y"] += pr.get("vy",0) * (1)
            if pr["kind"] in ("blade","stun_blade"):
                pr["angle"] += pr.get("spin", 8.0) * (dt*60/60)
                pr["trail"].append((pr["x"], pr["y"]))
                if len(pr["trail"]) > 6:
                    pr["trail"].pop(0)
                # collision AABB approx
                half_l = pr.get("len", 80) * 0.5
                half_w = pr.get("wid", 16) * 0.5
                aabb = pygame.Rect(int(pr["x"] - half_l) - camera_x, int(pr["y"] - half_w), int(half_l*2), int(half_w*2))
                nr = noob.rect(); nr.x -= camera_x
                if aabb.colliderect(nr) and not noob.invisible:
                    if pr["kind"] == "stun_blade":
                        noob.stun_until = max(noob.stun_until, now + 5.0)
                    else:
                        dmg = 30
                        if noob_reduce_until and now < noob_reduce_until:
                            dmg = max(1, int(dmg * 0.1))
                        noob.hp -= dmg
                        noob.stun_until = max(noob.stun_until, now + 0.4)
                    continue
            elif pr["kind"] == "stun":
                pass
            # ttl bounds
            if now < pr["ttl"] and -200 <= pr["x"] <= 5000 and -200 <= pr["y"] <= HEIGHT+200:
                kept_proj.append(pr)
        projectiles = kept_proj

    # Generator puzzle visuals are handled in draw; logic handled on keydown

    # CoolKid falls out of map -> Noob wins
    if coolkid.y > HEIGHT + 200:
        winner = "Noob"
        game_over = True

    # ------- clone AI -------
    kept = []
    for cinfo in clones:
        c = cinfo["p"]
        # despawn after 15s
        if now - cinfo["spawn"] > 15.0:
            continue
        # horizontal chase (simple)
        if noob.x + noob.w/2 < c.x + c.w/2:
            c.x -= c.speed
        elif noob.x + noob.w/2 > c.x + c.w/2:
            c.x += c.speed
        # small vertical hop if target higher and on ground
        if noob.y + 10 < c.y and c.on_ground:
            c.vel_y = -18
            c.on_ground = False
        # auto-slash when in range and clone's own cooldown ready
        if abs((noob.x + noob.w/2) - (c.x + c.w/2)) < 80 and now > cooldowns["clone_slash"]:
            sx = c.x + c.w // 2
            sy = c.y + c.h // 2
            if noob.x + noob.w/2 >= c.x + c.w/2:
                c.slash_line = ((sx, sy), (sx + 80, sy))
            else:
                c.slash_line = ((sx, sy), (sx - 80, sy))
            c.slash_end_time = now + 0.3
            c.has_hit = False
            cooldowns["clone_slash"] = now + 1.0
        kept.append(cinfo)
    clones = kept

    # ------- slash lifecycle & hit detection -------
    attackers = [coolkid] + [c["p"] for c in clones]
    for attacker in attackers:
        if attacker.slash_line and now > getattr(attacker, "slash_end_time", 0):
            attacker.slash_line = None
            attacker.has_hit = False

        if attacker.slash_line and not noob.invisible:
            a0, a1 = attacker.slash_line
            minx = min(a0[0], a1[0])
            maxx = max(a0[0], a1[0])
            midy = a0[1]
            # simple collision: check noob center in horizontal range and vertical closeness
            noob_cx = noob.x + noob.w/2
            noob_cy = noob.y + noob.h/2
            if (minx <= noob_cx <= maxx) and abs(noob_cy - midy) < 40:
                if not attacker.has_hit:
                    dmg = 10
                    if noob_reduce_until and now < noob_reduce_until:
                        dmg = max(1, int(dmg * 0.1))
                    noob.hp -= dmg
                    noob.stun_until = now + 0.3
                    attacker.has_hit = True
                    # keep slash until timeout for visibility

    # ------- dash contact damage -------
    # if coolkid dashing and touches noob, deal damage once per dash activation
    if coolkid.dash_active:
        if coolkid.rect().colliderect(noob.rect()):
            # stop dash immediately
            coolkid.dash_active = False
            coolkid.speed = coolkid.base_speed
            if not coolkid.dash_has_hit:
                dmg = 40
                if noob_reduce_until and now < noob_reduce_until:
                    dmg = max(1, int(dmg * 0.1))
                noob.hp -= dmg
                noob.stun_until = now + 0.3
                coolkid.dash_has_hit = True
                # explosion FX at noob for 0.45s
                noob_explosion_until = now + 0.45
                play(snd_explosion, 1.0)
                if noob.hp <= 0:
                    winner = "CoolKid"
                    game_over = True

    # ------- camera follow with dynamic zoom -------
    # Split-screen: compute two camera positions (no zoom)
    noob_center_x = noob.x + noob.w/2
    cool_center_x = coolkid.x + coolkid.w/2
    render_w = WIDTH//2
    render_h = HEIGHT
    camera_left = int(noob_center_x - render_w//2)
    camera_right = int(cool_center_x - render_w//2)
    if camera_left < 0: camera_left = 0
    if camera_right < 0: camera_right = 0

    # ------- draw (split screen) -------
    def draw_world(camera_x):
        # background
        win.fill(SKY)
        pygame.draw.circle(win, (230,230,255), (int(140 - camera_x//6), 90), 28)
        pygame.draw.circle(win, SKY, (int(150 - camera_x//6), 86), 10)
        for sx, sy, sr in stars:
            pygame.draw.circle(win, (240, 240, 200), (int(sx - camera_x*0.2), sy), sr)
        # ground
        pygame.draw.rect(win, DARK_RED, (0 - camera_x, HEIGHT-60, 5000, 60))
        pygame.draw.rect(win, GOLD, (0 - camera_x, HEIGHT-60, 5000, 6))
        # background tents and market
        def draw_tent(base_x, scale):
            tent_base_y = HEIGHT - 80
            tent_w = int(240 * scale)
            tent_h = int(140 * scale)
            tx = int(base_x - camera_x*0.8)
            # tent body
            pygame.draw.polygon(win, RED, [(tx, tent_base_y), (tx+tent_w, tent_base_y), (tx+tent_w-24, tent_base_y - tent_h//2), (tx+24, tent_base_y - tent_h//2)])
            # roof
            pygame.draw.polygon(win, (220,0,0), [(tx+24, tent_base_y - tent_h//2), (tx+tent_w-24, tent_base_y - tent_h//2), (tx+tent_w//2, tent_base_y - tent_h)])
            # rainbow stripes
            rainbow = [(255,0,0),(255,127,0),(255,255,0),(0,200,0),(0,120,255),(75,0,130),(148,0,211)]
            tip = (tx+tent_w//2, tent_base_y - tent_h)
            step = max(6, tent_w // (len(rainbow)*6))
            for i, x in enumerate(range(0, tent_w, step)):
                col = rainbow[i % len(rainbow)]
                pygame.draw.line(win, col, (tx+x, tent_base_y), tip, 2)
            # flag
            pygame.draw.line(win, WHITE, (tx+tent_w//2, tent_base_y - tent_h), (tx+tent_w//2, tent_base_y - tent_h - int(20*scale)), 2)
            pygame.draw.polygon(win, GOLD, [(tx+tent_w//2, tent_base_y - tent_h - int(20*scale)), (tx+tent_w//2 + int(12*scale), tent_base_y - tent_h - int(14*scale)), (tx+tent_w//2, tent_base_y - tent_h - int(8*scale))])
        # Place several tents across background
        all_tents = [(250,0.9),(700,0.8),(1150,0.7),(1600,0.85),(2100,0.75),(2550,0.8)]
        for base_x, sc in all_tents:
            if sc >= 0.85:
                continue  # skip largest tents that may block
            draw_tent(base_x, sc)
        # Market stalls (behind platforms)
        def draw_stall(x):
            sx = int(x - camera_x*0.9)
            sy = HEIGHT - 90
            pygame.draw.rect(win, (180,80,40), (sx, sy, 80, 40))
            pygame.draw.polygon(win, (220,0,0), [(sx-6, sy), (sx+86, sy), (sx+40, sy-24)])
            for i in range(6):
                col = (255,220,0) if i%2==0 else (255,255,255)
                pygame.draw.circle(win, col, (sx+10+i*12, sy+6), 3)
        for bx in [400, 900, 1350, 1750, 2200, 2650]:
            draw_stall(bx)
        # platforms (draw beams with stripes)
        for p in platforms:
            base = pygame.Rect(p.x - camera_x, p.y, p.w, p.h)
            pygame.draw.rect(win, MID_BLUE, base)
            for i in range(0, p.w, 20):
                col = GOLD if (i//20)%2==0 else PURPLE
                pygame.draw.rect(win, col, (p.x - camera_x + i, p.y, 10, p.h))
        # portals
        for prt in portals:
            r = prt["rect"]
            pygame.draw.rect(win, (80,20,100), (r.x - camera_x, r.y, r.w, r.h))
            pygame.draw.rect(win, (200,160,255), (r.x - camera_x+4, r.y+4, r.w-8, r.h-8))
        # barrier
        pygame.draw.rect(win, GOLD, (barrier.x - camera_x, barrier.y, barrier.w, barrier.h))
        pygame.draw.rect(win, (255,255,255), (barrier.x - camera_x+2, barrier.y+2, barrier.w-4, barrier.h-4), 2)
        # players and generators
        if not noob.invisible:
            noob.draw(camera_x)
        else:
            noob.draw(camera_x)
        if noob_reduce_until and now < noob_reduce_until:
            overlay = pygame.Surface((noob.w, noob.h), pygame.SRCALPHA)
            overlay.fill((100,100,100,120))
            win.blit(overlay, (noob.x - camera_x, noob.y))
        coolkid.draw(camera_x)
        for cinfo in clones:
            c = cinfo["p"]
            c.draw(camera_x)
        # cooldown bars above heads
        draw_cooldowns(int(noob.x - camera_x), int(noob.y - 30), ["noob_speed","noob_invis","noob_reduce"], 0, 0)
        if selected_killer == "CoolKid":
            draw_cooldowns(int(coolkid.x - camera_x), int(coolkid.y - 30), ["coolkid_dash","coolkid_clone","coolkid_slash"], 0, 0)
        else:
            draw_cooldowns(int(coolkid.x - camera_x), int(coolkid.y - 30), ["one_stun","one_slash","coolkid_dash","one_arrow"], 0, 0)
        for cinfo in clones:
            c = cinfo["p"]
            draw_cooldowns(int(c.x - camera_x), int(c.y - 30), ["clone_slash"], 0, 0)
        for gen in generators:
            gen.draw(camera_x)
        # draw houses last so they occlude characters
        for hx, hy, hw, hh in houses:
            pygame.draw.rect(win, (180,80,40), (hx - camera_x, hy, hw, hh))
            pygame.draw.polygon(win, (150,50,30), [(hx - camera_x, hy), (hx - camera_x + hw, hy), (hx - camera_x + hw//2, hy - 30)])
            # window
            wx, wy, ww, wh = hx - camera_x + 20, hy + 20, 24, 18
            in_window = noob.rect().colliderect(pygame.Rect(hx, hy, hw, hh))
            pygame.draw.rect(win, (255,255,120) if in_window else (80,80,80), (wx, wy, ww, wh))
            pygame.draw.rect(win, BLACK, (wx, wy, ww, wh), 2)
        # 1x1x1x1 arrow render
        if selected_killer == '1x1x1x1' and now < arrow_hint_until:
            # vector from killer to noob
            vx = (noob.x + noob.w/2) - (coolkid.x + coolkid.w/2)
            vy = (noob.y + noob.h/2) - (coolkid.y + coolkid.h/2)
            ang = math.atan2(vy, vx)
            # arrow at killer head
            base_x = int(coolkid.x + coolkid.w/2 - camera_x)
            base_y = int(coolkid.y + 10)
            L = 60
            tip_x = base_x + int(math.cos(ang) * L)
            tip_y = base_y + int(math.sin(ang) * L)
            # simple triangle arrow
            left = (tip_x + int(math.cos(ang + 2.5) * 14), tip_y + int(math.sin(ang + 2.5) * 14))
            right = (tip_x + int(math.cos(ang - 2.5) * 14), tip_y + int(math.sin(ang - 2.5) * 14))
            pygame.draw.line(win, (0,255,0), (base_x, base_y), (tip_x, tip_y), 4)
            pygame.draw.polygon(win, (0,255,0), [(tip_x, tip_y), left, right])
        # draw projectiles
        for pr in projectiles:
            if pr["kind"] == "stun":
                pygame.draw.circle(win, (0,255,0), (int(pr["x"]) - camera_x, int(pr["y"])) , 6)
                pygame.draw.circle(win, (255,255,255), (int(pr["x"]) - camera_x, int(pr["y"])) , 9, 2)
            elif pr["kind"] == "blade":
                for i in range(len(pr["trail"]) - 1):
                    x1,y1 = pr["trail"][i]
                    x2,y2 = pr["trail"][i+1]
                    pygame.draw.line(win, (80,80,80), (int(x1) - camera_x, int(y1)), (int(x2) - camera_x, int(y2)), 3)
                cx = pr["x"] - camera_x
                cy = pr["y"]
                L = pr.get("len",90)
                W = pr.get("wid",18)
                ang = math.radians(pr.get("angle",0))
                cosA = math.cos(ang); sinA = math.sin(ang)
                pts = []
                for px, py in [( -L/2, -W/2 ), ( L/2, -W/2 ), ( L/2, W/2 ), ( -L/2, W/2 )]:
                    rx = px*cosA - py*sinA + cx
                    ry = px*sinA + py*cosA + cy
                    pts.append((int(rx), int(ry)))
                pygame.draw.polygon(win, (0,0,0), pts)
                pygame.draw.polygon(win, (255,0,0), pts, 2)
            elif pr["kind"] == "stun_blade":
                for i in range(len(pr["trail"]) - 1):
                    x1,y1 = pr["trail"][i]
                    x2,y2 = pr["trail"][i+1]
                    pygame.draw.line(win, (80,80,80), (int(x1) - camera_x, int(y1)), (int(x2) - camera_x, int(y2)), 3)
                cx = pr["x"] - camera_x
                cy = pr["y"]
                L = pr.get("len",60)
                W = pr.get("wid",12)
                ang = math.radians(pr.get("angle",0))
                cosA = math.cos(ang); sinA = math.sin(ang)
                pts = []
                for px, py in [( -L/2, -W/2 ), ( L/2, -W/2 ), ( L/2, W/2 ), ( -L/2, W/2 )]:
                    rx = px*cosA - py*sinA + cx
                    ry = px*sinA + py*cosA + cy
                    pts.append((int(rx), int(ry)))
                pygame.draw.polygon(win, (0,0,0), pts)
                pygame.draw.polygon(win, (0,200,0), pts, 2)
        # dash explosion FX (render inside each view)
        if noob_explosion_until and now < noob_explosion_until:
            t = 1.0 - ((noob_explosion_until - now) / 0.45)
            cxp = int(noob.x + noob.w/2 - camera_x)
            cyp = int(noob.y + noob.h/2)
            r1 = int(20 + 40 * t)
            r2 = int(10 + 30 * t)
            pygame.draw.circle(win, (255,120,0), (cxp, cyp), r1)
            pygame.draw.circle(win, (255,220,0), (cxp, cyp), r2)
            pygame.draw.circle(win, (255,255,255), (cxp, cyp), max(2, int(6 * (1-t))), 2)
        # slashes
        attackers = [coolkid] + [c["p"] for c in clones]
        for attacker in attackers:
            if attacker.slash_line:
                a0, a1 = attacker.slash_line
                if getattr(attacker,'variant','CoolKid') == '1x1x1x1':
                    pygame.draw.line(win, (0,0,0), (a0[0] - camera_x, a0[1]), (a1[0] - camera_x, a1[1]), 12)
                else:
                    pygame.draw.line(win, (0,0,0), (a0[0] - camera_x, a0[1]), (a1[0] - camera_x, a1[1]), 12)
                    pygame.draw.line(win, (255,255,255), (a0[0] - camera_x, a0[1]), (a1[0] - camera_x, a1[1]), 8)
                    pygame.draw.line(win, (255,215,0), (a0[0] - camera_x, a0[1]), (a1[0] - camera_x, a1[1]), 4)
                if now - getattr(attacker, 'slash_spawn_time', 0) < 0.2:
                    cxp = (a0[0] + a1[0]) // 2 - camera_x
                    cyp = (a0[1] + a1[1]) // 2
                    pygame.draw.circle(win, (255,255,0), (cxp, cyp), 10)
                    pygame.draw.circle(win, (255,255,255), (cxp, cyp), 16, 3)
        # foreground platform edges
        for p in platforms:
            pygame.draw.line(win, WHITE, (p.x - camera_x, p.y), (p.x - camera_x + p.w, p.y), 3)
            pygame.draw.line(win, (0,0,0), (p.x - camera_x, p.y + p.h - 1), (p.x - camera_x + p.w, p.y + p.h - 1), 2)

    # render both views
    display_surface = win
    # left view (Noob)
    scene_left = pygame.Surface((render_w, render_h))
    win = scene_left
    draw_world(camera_left)
    # right view (Killer)
    scene_right = pygame.Surface((render_w, render_h))
    win = scene_right
    draw_world(camera_right)
    # back to display and blit halves without scaling
    win = display_surface
    win.blit(scene_left, (0, 0))
    win.blit(scene_right, (WIDTH//2, 0))
    # divider
    pygame.draw.rect(win, (20,20,20), (WIDTH//2 - 2, 0, 4, HEIGHT))

    # UI overlay (fixed to screen): timer at top center
    elapsed = now - start_time
    time_left = max(0, int(GAME_DURATION - elapsed - bonus_time))
    timer_text = FONT.render(f"Survive: {time_left}s", True, WHITE)
    win.blit(timer_text, (WIDTH//2 - timer_text.get_width()//2, 20))
    # UI overlay: Noob health bar (fixed)
    ui_bar_x, ui_bar_y, ui_bar_w, ui_bar_h = 20, 50, 220, 18
    pygame.draw.rect(win, (90,0,0), (ui_bar_x, ui_bar_y, ui_bar_w, ui_bar_h))
    hp_w = max(0, int(ui_bar_w * (noob.hp / NOOB_MAX_HP)))
    pygame.draw.rect(win, (20,200,60), (ui_bar_x, ui_bar_y, hp_w, ui_bar_h))
    pygame.draw.rect(win, WHITE, (ui_bar_x, ui_bar_y, ui_bar_w, ui_bar_h), 2)
    hp_text = FONT.render(f"Noob HP: {noob.hp}", True, WHITE)
    win.blit(hp_text, (ui_bar_x, ui_bar_y - 22))

    # check win/lose
    game_over = False
    winner = None
    if noob.hp <= 0:
        game_over = True
        winner = "CoolKid"
    elif time_left <= 0:
        game_over = True
        winner = "Noob"

    if game_over:
        # spawn confetti once
        if not confetti:
            import random as _r
            if winner == "Noob":
                colors = [(0,200,0),(0,120,255),(255,215,0)]
            else:
                # killer wins: green if 1x1x1x1, red if CoolKid
                colors = [(0,200,0)] if selected_killer == "1x1x1x1" else [(255,0,0)]
            for _ in range(120):
                cx = WIDTH//2 + _r.randint(-80,80)
                cy = HEIGHT//3
                vx = _r.uniform(-2.5, 2.5)
                vy = _r.uniform(-5.0, -1.0)
                col = colors[_r.randrange(len(colors))]
                confetti.append({"x":cx, "y":cy, "vx":vx, "vy":vy, "color":col, "life":_r.uniform(1.0, 2.0)})
        # animate confetti for 2 seconds (or until rematch)
        end_until = now + 2.0
        rematch = False
        button_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 20, 200, 48)
        while True:
            # fade overlay
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0,60))
            win.blit(overlay, (0,0))
            # update and draw confetti
            for p in confetti:
                p["vy"] += 0.15
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                pygame.draw.rect(win, p["color"], (int(p["x"]), int(p["y"]), 4, 6))
            # custom win text for 1x1x1x1
            if winner == "Noob":
                end_col = WHITE
                win_text = f"{winner} Wins!"
            else:
                if selected_killer == "1x1x1x1":
                    end_col = (0,200,0)
                    win_text = "1x1x1x wins!!!"
                else:
                    end_col = RED
                    win_text = "CoolKid Wins!"
            end_txt = BIG.render(win_text, True, end_col)
            win.blit(end_txt, (WIDTH//2 - end_txt.get_width()//2, HEIGHT//2 - 60))
            # Rematch button
            pygame.draw.rect(win, (30,30,30), button_rect)
            pygame.draw.rect(win, WHITE, button_rect, 2)
            btn_txt = PRESS_FONT.render("Rematch (R)", True, WHITE)
            win.blit(btn_txt, (button_rect.centerx - btn_txt.get_width()//2, button_rect.centery - btn_txt.get_height()//2))
            pygame.display.update()
            clock.tick(60)
            # events
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                    rematch = True
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if button_rect.collidepoint(ev.pos):
                        rematch = True
            if rematch or time.time() >= end_until:
                break
        if rematch:
            # reset round state without quitting
            confetti.clear()
            # reset players
            noob.hp = NOOB_MAX_HP
            noob.x, noob.y = random.choice(NOOB_SPAWNS)
            noob.vel_y = 0; noob.on_ground = False; noob.invisible = False; noob.stun_until = 0.0
            coolkid.x, coolkid.y = 300, HEIGHT - 150
            coolkid.vel_y = 0; coolkid.on_ground = False; coolkid.stun_until = 0.0
            # clear effects
            clones.clear()
            projectiles.clear()
            noob_explosion_until = 0.0
            arrow_hint_until = 0.0
            # reset generators
            for gen in generators:
                gen.done = False
                gen.active = False
                gen.index = 0
                gen.sequence = []
            bonus_time = 0
            # reset cooldowns
            for k in cooldowns.keys():
                cooldowns[k] = 0.0
            # timer
            start_time = time.time()
            game_over = False
            winner = None
            continue
        # otherwise end the program (fade out music first)
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.fadeout(1500)
        except Exception:
            pass
        pygame.quit()
        sys.exit()

    pygame.display.update()
