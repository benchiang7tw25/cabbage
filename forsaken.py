import pygame, sys, time, random

pygame.init()
WIDTH, HEIGHT = 900, 600
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Forsaken")

# Colors
WHITE = (255,255,255)
BLACK = (0,0,0)
SKY = (135,206,235)
YELLOW = (255,255,0)
BLUE = (0,0,255)
GREEN = (0,200,0)
RED = (200,0,0)
GRAY = (150,150,150)

clock = pygame.time.Clock()
FONT = pygame.font.SysFont("Arial", 24)
BIG = pygame.font.SysFont("Arial", 72, bold=True)

# Map / platforms
platforms = [
    pygame.Rect(0, HEIGHT-50, 3000, 50),  # long ground
    pygame.Rect(200, 450, 200, 20),
    pygame.Rect(500, 350, 200, 20),
    pygame.Rect(850, 250, 200, 20),
]
# clouds (for parallax)
clouds = [(random.randint(0, 2000), random.randint(40, 130), random.randint(100,180), 60) for _ in range(6)]

# Starting barrier
barrier = pygame.Rect(50, HEIGHT-150, 20, 100)

# Game constants
GRAVITY = 0.6
NOOB_MAX_HP = 100
GAME_DURATION = 100  # seconds to survive

# cooldown dict stores next-ready timestamps
cooldowns = {
    "noob_speed": 0.0,     # Q: duration 5s, cd 10s
    "noob_invis": 0.0,     # E: duration 5s, cd 10s
    "coolkid_dash": 0.0,   # /: duration 4s, cd 10s
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
        max_cd = 10 if ab not in ("coolkid_slash","clone_slash") else 1
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

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def apply_gravity(self):
        self.y += self.vel_y
        self.vel_y += GRAVITY
        if self.vel_y > 12:
            self.vel_y = 12

    def check_platforms(self, plats):
        r = self.rect()
        self.on_ground = False
        for p in plats:
            if r.colliderect(p) and self.vel_y >= 0:
                # only snap if landing on top
                if r.bottom - self.vel_y <= p.top + 1:
                    self.y = p.top - self.h
                    self.vel_y = 0
                    self.on_ground = True

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
            self.vel_y = -12
            self.on_ground = False

    def draw(self, offset_x):
        # draw player; if noob, split head/torso/pants
        if self.is_noob:
            # head (yellow)
            pygame.draw.rect(win, YELLOW, (self.x - offset_x + 4, self.y, self.w-8, 18))
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
            pygame.draw.rect(win, RED, (self.x - offset_x, self.y, self.w, self.h))
        # slash drawing (if active)
        if self.slash_line:
            a, b = self.slash_line
            pygame.draw.line(win, BLACK, (a[0] - offset_x, a[1]), (b[0] - offset_x, b[1]), 8)

# Slash as lightweight struct in this code base (we draw lines directly on owner.slash_line)
# We'll keep slashes attached to owners

# Create players
noob = Player(100, HEIGHT - 150, is_noob=True)
coolkid = Player(300, HEIGHT - 150, is_noob=False)
clone = None
clone_spawn_time = 0.0

# Title screen
def title_screen():
    flash = 0
    while True:
        win.fill(SKY)
        # sun and clouds
        pygame.draw.circle(win, (255,255,0), (100,80), 50)
        for cx, cy, cw, ch in clouds:
            pygame.draw.ellipse(win, WHITE, (cx, cy, cw, ch))
        title_text = BIG.render("FORSAKEN", True, BLACK)
        win.blit(title_text, (WIDTH//2 - title_text.get_width()//2, 150))
        flash += 1
        if (flash // 30) % 2 == 0:
            press = FONT.render("Press ENTER to Start", True, (50,0,0))
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

    # CoolKid dash (duration 4s, cd 10s) bound to slash key (/) - pygame.K_SLASH
    if keys[pygame.K_SLASH] and now > cooldowns["coolkid_dash"]:
        coolkid_dash_until = now + 4.0
        cooldowns["coolkid_dash"] = now + 10.0
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

    # Spawn clone (M) cd 10s
    if keys[pygame.K_m] and now > cooldowns["coolkid_clone"] and clone is None:
        # spawn clone to the right of coolkid
        clone = Player(coolkid.x + 50, coolkid.y, is_noob=False)
        clone.is_clone = True
        # make clone slower: 1/3 speed
        clone.base_speed = coolkid.base_speed / 3.0
        clone.speed = clone.base_speed
        clone_spawn_time = now
        cooldowns["coolkid_clone"] = now + 10.0
        # clone gets its own slash cooldown tracked by cooldowns["clone_slash"]

    # ------- durations expiry -------
    if noob_speed_until and now >= noob_speed_until:
        noob.speed = noob.base_speed
        noob_speed_until = 0.0
    if noob_invis_until and now >= noob_invis_until:
        noob.invisible = False
        noob_invis_until = 0.0
    if coolkid.dash_active and now >= coolkid.dash_end:
        coolkid.dash_active = False
        coolkid.speed = coolkid.base_speed
        coolkid.dash_has_hit = False

    # ------- physics -------
    # apply gravity and collisions
    for p in (noob, coolkid, clone) if clone else (noob, coolkid):
        if p:
            p.apply_gravity()
            p.check_platforms(platforms)

    # ------- clone AI -------
    if clone:
        # despawn after 15s
        if now - clone_spawn_time > 15.0:
            clone = None
        else:
            # horizontal chase (simple)
            if noob.x + noob.w/2 < clone.x + clone.w/2:
                clone.x -= clone.speed
            elif noob.x + noob.w/2 > clone.x + clone.w/2:
                clone.x += clone.speed
            # small vertical hop if target higher and on ground
            if noob.y + 10 < clone.y and clone.on_ground:
                clone.vel_y = -12
                clone.on_ground = False
            # auto-slash when in range and clone's own cooldown ready
            if abs((noob.x + noob.w/2) - (clone.x + clone.w/2)) < 80 and now > cooldowns["clone_slash"]:
                sx = clone.x + clone.w // 2
                sy = clone.y + clone.h // 2
                # direction toward noob
                if noob.x + noob.w/2 >= clone.x + clone.w/2:
                    clone.slash_line = ((sx, sy), (sx + 80, sy))
                else:
                    clone.slash_line = ((sx, sy), (sx - 80, sy))
                clone.slash_end_time = now + 0.3
                clone.has_hit = False
                cooldowns["clone_slash"] = now + 1.0

    # ------- slash lifecycle & hit detection -------
    # collect owners to check: coolkid and clone (if present)
    attackers = [coolkid]
    if clone:
        attackers.append(clone)

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
                    noob.hp -= 10
                    noob.stun_until = now + 0.3
                    attacker.has_hit = True
                    # keep slash until timeout for visibility

    # ------- dash contact damage -------
    # if coolkid dashing and touches noob, deal damage once per dash activation
    if coolkid.dash_active:
        if coolkid.rect().colliderect(noob.rect()):
            if not coolkid.dash_has_hit:
                noob.hp -= 10
                noob.stun_until = now + 0.3
                coolkid.dash_has_hit = True
                if noob.hp <= 0:
                    # immediate win
                    winner = "CoolKid"
                    game_over = True
    # Ensure rect method exists: add it to Player by monkey patch if not present (we used .rect() above)
    # (we have Player.rect defined earlier)

    # ------- camera follow -------
    camera_x = int(noob.x + noob.w/2 - WIDTH//2)
    if camera_x < 0: camera_x = 0

    # ------- draw -------
    win.fill(SKY)
    # sun
    pygame.draw.circle(win, (255,255,0), (100 - camera_x//6, 80), 50)
    # clouds
    for cx, cy, cw, ch in clouds:
        pygame.draw.ellipse(win, WHITE, (cx - camera_x//3, cy, cw, ch))
    # platforms
    for p in platforms:
        pygame.draw.rect(win, GRAY, (p.x - camera_x, p.y, p.w, p.h))
    # barrier
    pygame.draw.rect(win, BLACK, (barrier.x - camera_x, barrier.y, barrier.w, barrier.h))

    # draw players
    if not noob.invisible:
        noob.draw(camera_x)
    else:
        # still draw faded shape for positioning
        noob.draw(camera_x)
    coolkid.draw(camera_x)
    if clone:
        clone.draw(camera_x)

    # draw slash lines (for attacker(s))
    for attacker in attackers:
        if attacker.slash_line:
            a0, a1 = attacker.slash_line
            # outline/shadow
            pygame.draw.line(win, (0,0,0), (a0[0] - camera_x, a0[1]), (a1[0] - camera_x, a1[1]), 12)
            # bright core
            pygame.draw.line(win, (255,255,255), (a0[0] - camera_x, a0[1]), (a1[0] - camera_x, a1[1]), 8)
            pygame.draw.line(win, (255,215,0), (a0[0] - camera_x, a0[1]), (a1[0] - camera_x, a1[1]), 4)
            # flash at center for first 0.2s
            if now - getattr(attacker, 'slash_spawn_time', 0) < 0.2:
                cx = (a0[0] + a1[0]) // 2 - camera_x
                cy = (a0[1] + a1[1]) // 2
                pygame.draw.circle(win, (255,255,0), (cx, cy), 10)
                pygame.draw.circle(win, (255,255,255), (cx, cy), 16, 3)

    # draw health bar for noob
    pygame.draw.rect(win, (150,0,0), (20, 20, 200, 20))
    hp_w = max(0, int(200 * (noob.hp / NOOB_MAX_HP)))
    pygame.draw.rect(win, (0,200,0), (20, 20, hp_w, 20))
    hp_text = FONT.render(f"Noob HP: {noob.hp}", True, BLACK)
    win.blit(hp_text, (20, 45))

    # draw cooldown bars above players
    draw_cooldowns(int(noob.x - camera_x), int(noob.y - 30), ["noob_speed","noob_invis"], 0, 0)
    draw_cooldowns(int(coolkid.x - camera_x), int(coolkid.y - 30), ["coolkid_dash","coolkid_clone","coolkid_slash"], 0, 0)
    if clone:
        draw_cooldowns(int(clone.x - camera_x), int(clone.y - 30), ["clone_slash"], 0, 0)

    # draw timer
    elapsed = now - start_time
    time_left = max(0, int(GAME_DURATION - elapsed))
    timer_text = FONT.render(f"Survive: {time_left}s", True, BLACK)
    win.blit(timer_text, (WIDTH//2 - 60, 20))

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
        # end screen
        win.fill(WHITE)
        end_txt = BIG.render(f"{winner} Wins!", True, BLACK if winner=="Noob" else RED)
        win.blit(end_txt, (WIDTH//2 - end_txt.get_width()//2, HEIGHT//2 - 50))
        pygame.display.update()
        pygame.time.wait(3000)
        pygame.quit()
        sys.exit()

    pygame.display.update()
