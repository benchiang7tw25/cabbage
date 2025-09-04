import pygame, sys, time, random

pygame.init()
WIDTH, HEIGHT = 900, 600
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
platforms = [
    pygame.Rect(0, HEIGHT-50, 3000, 50),  # long ground
    pygame.Rect(200, 480, 220, 20),
    pygame.Rect(520, 420, 200, 20),
    pygame.Rect(820, 360, 220, 20),
    pygame.Rect(1140, 300, 200, 20),
    pygame.Rect(1460, 360, 200, 20),
    pygame.Rect(1780, 420, 240, 20),
    pygame.Rect(2120, 320, 260, 20),
    pygame.Rect(2480, 260, 220, 20),
]
# clouds (for parallax) -> convert to stars for night
stars = [(random.randint(0, 3000), random.randint(20, 180), random.randint(1,3)) for _ in range(120)]

# Starting barrier
barrier = pygame.Rect(50, HEIGHT-150, 20, 100)

# Game constants
GRAVITY = 0.65
NOOB_MAX_HP = 100
GAME_DURATION = 100  # seconds to survive

# cooldown dict stores next-ready timestamps
cooldowns = {
    "noob_speed": 0.0,     # Q: duration 5s, cd 10s
    "noob_invis": 0.0,     # E: duration 5s, cd 10s
    "noob_reduce": 0.0,    # R: duration 5s, cd 30s (slow + 90% damage reduction)
    "coolkid_dash": 0.0,   # /: duration 4s, cd 40s
    "coolkid_slash": 0.0,  # ,: cd 1s
    "coolkid_clone": 0.0,  # m: cd 10s
    "clone_slash": 0.0     # clone own slash cd 1s
}

ability_colors = {
    "noob_speed": (0,255,0),
    "noob_invis": (0,255,255),
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
            # big face covering whole body region
            body_rect = pygame.Rect(self.x - offset_x, self.y, self.w, self.h)
            # base skin fill (red)
            pygame.draw.rect(win, RED, body_rect)
            # outline
            pygame.draw.rect(win, (120,0,0), body_rect, 2)
            # side shading (right side)
            shade = pygame.Surface((self.w//3, self.h), pygame.SRCALPHA)
            shade.fill((0,0,0,60))
            win.blit(shade, (self.x - offset_x + 2*self.w//3, self.y))
            # large eyes
            eye_r = 6
            eye_y = self.y + self.h//3
            eye_lx = self.x - offset_x + self.w//3
            eye_rx = self.x - offset_x + 2*self.w//3
            pygame.draw.circle(win, BLACK, (int(eye_lx), int(eye_y)), eye_r)
            pygame.draw.circle(win, BLACK, (int(eye_rx), int(eye_y)), eye_r)
            # small highlights on eyes
            pygame.draw.circle(win, WHITE, (int(eye_lx - 2), int(eye_y - 2)), 2)
            pygame.draw.circle(win, WHITE, (int(eye_rx - 2), int(eye_y - 2)), 2)
            # wide smile
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
coolkid = Player(300, HEIGHT - 150, is_noob=False)
clones = []

# Title screen
def title_screen():
    flash = 0
    while True:
        win.fill(SKY)
        # night sky with stars
        pygame.draw.circle(win, (255,255,0), (100,80), 50)
        for sx, sy, sr in stars:
            pygame.draw.circle(win, (240, 240, 200), (sx, sy), sr)
        title_text = BIG.render("FORSAKEN", True, WHITE)
        win.blit(title_text, (WIDTH//2 - title_text.get_width()//2, 150))
        # Always-visible white bold prompt (no flashing)
        press = PRESS_FONT.render("Press ENTER to Start", True, WHITE)
        win.blit(press, (WIDTH//2 - press.get_width()//2, 350))
        pygame.display.update()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                return

# start
title_screen()
start_time = time.time()

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

# main
while running:
    dt = clock.tick(60) / 1000.0
    now = time.time()
    keys = pygame.key.get_pressed()

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit(); sys.exit()

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
    if keys[pygame.K_SLASH] and now > cooldowns["coolkid_dash"]:
        coolkid_dash_until = now + 4.0
        cooldowns["coolkid_dash"] = now + 40.0
        coolkid.dash_active = True
        coolkid.dash_end = coolkid_dash_until
        coolkid.speed = coolkid.base_speed * 5
        coolkid.dash_has_hit = False

    # CoolKid manual slash (comma key) cd 1s
    if keys[pygame.K_COMMA] and now > cooldowns["coolkid_slash"]:
        # set slash line based on facing direction
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

    # Spawn clones (M) cd 10s, create up to 3 clones
    if keys[pygame.K_m] and now > cooldowns["coolkid_clone"]:
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
                if noob.hp <= 0:
                    winner = "CoolKid"
                    game_over = True

    # ------- camera follow with dynamic zoom -------
    # Base camera centered on Noob; zoom out so CoolKid is not cut off
    noob_center_x = noob.x + noob.w/2
    cool_center_x = coolkid.x + coolkid.w/2
    left_x = min(noob_center_x, cool_center_x)
    right_x = max(noob_center_x, cool_center_x)
    margin = 420  # more aggressive margin so CoolKid is seen before cutoff
    desired_left = left_x - margin//2
    desired_right = right_x + margin//2
    needed_width = desired_right - desired_left
    if needed_width > WIDTH:
        view_scale = WIDTH / float(needed_width)
    else:
        view_scale = 1.0
    if view_scale < 0.6:
        view_scale = 0.6
        needed_width = int(WIDTH / view_scale)
    render_w = int(WIDTH / view_scale)
    render_h = int(HEIGHT / view_scale)
    camera_x = int(noob_center_x - render_w//2)
    # keep CoolKid within inner margins even when no zoom
    inner = margin//2
    if (cool_center_x - camera_x) > (render_w - inner):
        camera_x = int(cool_center_x - (render_w - inner))
    if (cool_center_x - camera_x) < inner:
        camera_x = int(cool_center_x - inner)
    if camera_x < 0: camera_x = 0

    # ------- draw -------
    # draw to offscreen scene then scale to window
    display_surface = win
    scene = pygame.Surface((render_w, render_h))
    win = scene

    win.fill(SKY)
    # night moon
    pygame.draw.circle(win, (230,230,255), (int(140 - camera_x//6), 90), 28)
    pygame.draw.circle(win, SKY, (int(150 - camera_x//6), 86), 10)
    # stars (parallax slight)
    for sx, sy, sr in stars:
        pygame.draw.circle(win, (240, 240, 200), (int(sx - camera_x*0.2), sy), sr)

    # ground as circus ring
    pygame.draw.rect(win, DARK_RED, (0 - camera_x, HEIGHT-60, render_w+camera_x, 60))
    pygame.draw.rect(win, GOLD, (0 - camera_x, HEIGHT-60, render_w+camera_x, 6))

    # BACKGROUND: multiple circus tents (parallax) and a small market
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
    for base_x, sc in [(250,0.9),(700,0.8),(1150,0.7),(1600,0.85),(2100,0.75),(2550,0.8)]:
        draw_tent(base_x, sc)

    # Market stalls (behind platforms)
    def draw_stall(x):
        sx = int(x - camera_x*0.9)
        sy = HEIGHT - 90
        # booth base
        pygame.draw.rect(win, (180,80,40), (sx, sy, 80, 40))
        # roof
        pygame.draw.polygon(win, (220,0,0), [(sx-6, sy), (sx+86, sy), (sx+40, sy-24)])
        # lights
        for i in range(6):
            col = (255,220,0) if i%2==0 else (255,255,255)
            pygame.draw.circle(win, col, (sx+10+i*12, sy+6), 3)

    for bx in [400, 900, 1350, 1750, 2200, 2650]:
        draw_stall(bx)

    # platforms with colorful stripes (draw AFTER background so they are in front)
    for p in platforms:
        base = pygame.Rect(p.x - camera_x, p.y, p.w, p.h)
        pygame.draw.rect(win, MID_BLUE, base)
        # stripes
        for i in range(0, p.w, 20):
            col = GOLD if (i//20)%2==0 else PURPLE
            pygame.draw.rect(win, col, (p.x - camera_x + i, p.y, 10, p.h))

    # barrier like ticket booth gate
    pygame.draw.rect(win, GOLD, (barrier.x - camera_x, barrier.y, barrier.w, barrier.h))
    pygame.draw.rect(win, (255,255,255), (barrier.x - camera_x+2, barrier.y+2, barrier.w-4, barrier.h-4), 2)

    # circus tent in background
    tent_base_y = HEIGHT - 60
    tent_x = int(400 - camera_x*0.8)
    tent_w = 300
    tent_h = 180
    # tent body
    pygame.draw.polygon(win, RED, [(tent_x, tent_base_y), (tent_x+tent_w, tent_base_y), (tent_x+tent_w-30, tent_base_y - tent_h//2), (tent_x+30, tent_base_y - tent_h//2)])
    # roof
    pygame.draw.polygon(win, (220,0,0), [(tent_x+30, tent_base_y - tent_h//2), (tent_x+tent_w-30, tent_base_y - tent_h//2), (tent_x+tent_w//2, tent_base_y - tent_h)])
    # rainbow stripes on tent (vertical fans to roof tip)
    rainbow = [(255,0,0),(255,127,0),(255,255,0),(0,200,0),(0,120,255),(75,0,130),(148,0,211)]
    tip = (tent_x+tent_w//2, tent_base_y - tent_h)
    step = max(6, tent_w // (len(rainbow)*6))
    for i, x in enumerate(range(0, tent_w, step)):
        col = rainbow[i % len(rainbow)]
        pygame.draw.line(win, col, (tent_x+x, tent_base_y), tip, 3)
    # flag
    pygame.draw.line(win, WHITE, (tent_x+tent_w//2, tent_base_y - tent_h), (tent_x+tent_w//2, tent_base_y - tent_h - 30), 2)
    pygame.draw.polygon(win, GOLD, [(tent_x+tent_w//2, tent_base_y - tent_h - 30), (tent_x+tent_w//2 + 18, tent_base_y - tent_h - 22), (tent_x+tent_w//2, tent_base_y - tent_h - 14)])

    # draw players
    if not noob.invisible:
        noob.draw(camera_x)
    else:
        noob.draw(camera_x)
    # Noob R visual: grey overlay while active
    if noob_reduce_until and now < noob_reduce_until:
        overlay = pygame.Surface((noob.w, noob.h), pygame.SRCALPHA)
        overlay.fill((100,100,100,120))
        win.blit(overlay, (noob.x - camera_x, noob.y))

    coolkid.draw(camera_x)
    for cinfo in clones:
        c = cinfo["p"]
        c.draw(camera_x)

    # explosion FX
    if noob_explosion_until and now < noob_explosion_until:
        t = 1.0 - ((noob_explosion_until - now) / 0.45)
        cxp = int(noob.x + noob.w/2 - camera_x)
        cyp = int(noob.y + noob.h/2)
        r1 = int(20 + 40 * t)
        r2 = int(10 + 30 * t)
        pygame.draw.circle(win, (255,120,0), (cxp, cyp), r1)
        pygame.draw.circle(win, (255,220,0), (cxp, cyp), r2)
        pygame.draw.circle(win, (255,255,255), (cxp, cyp), max(2, int(6 * (1-t))), 2)

    # draw slash lines (for attacker(s))
    for attacker in attackers:
        if attacker.slash_line:
            a0, a1 = attacker.slash_line
            pygame.draw.line(win, (0,0,0), (a0[0] - camera_x, a0[1]), (a1[0] - camera_x, a1[1]), 12)
            pygame.draw.line(win, (255,255,255), (a0[0] - camera_x, a0[1]), (a1[0] - camera_x, a1[1]), 8)
            pygame.draw.line(win, (255,215,0), (a0[0] - camera_x, a0[1]), (a1[0] - camera_x, a1[1]), 4)
            if now - getattr(attacker, 'slash_spawn_time', 0) < 0.2:
                cxp = (a0[0] + a1[0]) // 2 - camera_x
                cyp = (a0[1] + a1[1]) // 2
                pygame.draw.circle(win, (255,255,0), (cxp, cyp), 10)
                pygame.draw.circle(win, (255,255,255), (cxp, cyp), 16, 3)

    # draw cooldown bars above players
    draw_cooldowns(int(noob.x - camera_x), int(noob.y - 30), ["noob_speed","noob_invis","noob_reduce"], 0, 0)
    draw_cooldowns(int(coolkid.x - camera_x), int(coolkid.y - 30), ["coolkid_dash","coolkid_clone","coolkid_slash"], 0, 0)
    for cinfo in clones:
        c = cinfo["p"]
        draw_cooldowns(int(c.x - camera_x), int(c.y - 30), ["clone_slash"], 0, 0)

    # restore global win and blit scaled scene
    win = display_surface
    scaled = pygame.transform.smoothscale(scene, (WIDTH, HEIGHT))
    win.blit(scaled, (0, 0))

    # UI overlay (fixed to screen): timer at top center
    elapsed = now - start_time
    time_left = max(0, int(GAME_DURATION - elapsed))
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
            colors = [(255,0,0)] if winner == "CoolKid" else [(0,200,0),(0,120,255),(255,215,0)]
            for _ in range(120):
                cx = WIDTH//2 + _r.randint(-80,80)
                cy = HEIGHT//3
                vx = _r.uniform(-2.5, 2.5)
                vy = _r.uniform(-5.0, -1.0)
                col = colors[_r.randrange(len(colors))]
                confetti.append({"x":cx, "y":cy, "vx":vx, "vy":vy, "color":col, "life":_r.uniform(1.0, 2.0)})
        # animate confetti for 2 seconds
        end_until = now + 2.0
        while time.time() < end_until:
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
            end_txt = BIG.render(f"{winner} Wins!", True, WHITE if winner=="Noob" else RED)
            win.blit(end_txt, (WIDTH//2 - end_txt.get_width()//2, HEIGHT//2 - 50))
            pygame.display.update()
            clock.tick(60)
        pygame.quit()
        sys.exit()

    pygame.display.update()
