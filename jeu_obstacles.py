try:
    import pygame
except ImportError:
    print("Pygame n'est pas installé. Installation requise:")
    print("1. Ouvrez un terminal/command prompt")
    print("2. Exécutez: pip install pygame")
    print("3. Relancez le programme")
    exit(1)

import random
import os
import math
import json


pygame.init()
# protect audio init so script runs on machines without audio devices
try:
    pygame.mixer.init()
except Exception:
    # no audio available — continue without music
    pass

# --- Added: helper to check mixer status ---
def mixer_available():
    try:
        return pygame.mixer.get_init() is not None
    except Exception:
        return False


# After pygame.init(), add resolution settings
SCALE_FACTOR = 1  # Standard window scale
BASE_WIDTH, BASE_HEIGHT = 800, 600  # Standard window size
LARGEUR, HAUTEUR = BASE_WIDTH, BASE_HEIGHT
FENETRE = pygame.display.set_mode((LARGEUR, HAUTEUR), pygame.RESIZABLE)
pygame.display.set_caption("Jeu de parcours")


# Joueur
PLAYER_SIZE = int(40 * SCALE_FACTOR)
joueur = pygame.Rect(50, HAUTEUR - PLAYER_SIZE - 20, PLAYER_SIZE, PLAYER_SIZE)
vitesse_x = 5 * SCALE_FACTOR
vitesse_y = 0
gravite = 1 * SCALE_FACTOR
saut = -15 * SCALE_FACTOR


# Gravité inversée
gravite_inversee = False
niveau = 1


# Sol/plafond
sol = pygame.Rect(0, HAUTEUR - 20 * SCALE_FACTOR, LARGEUR, 20 * SCALE_FACTOR)
plafond = pygame.Rect(0, 0, LARGEUR, 20 * SCALE_FACTOR)


clock = pygame.time.Clock()
jeu_actif = True


# --- Nouveautés : obstacles, niveaux, musique, HUD ---
# Dossier assets (placez vos musiques ici: level1.ogg, level2.ogg, ...)
ASSETS = os.path.join(os.path.dirname(__file__), "assets")
LEADERBOARD_FILE = os.path.join(os.path.dirname(__file__), "leaderboard.json")


# After pygame.init(), add assets directory creation
if not os.path.exists(ASSETS):
    os.makedirs(ASSETS)


def load_music_for_level(level_id):
    # If mixer isn't available, skip music operations
    if not mixer_available():
        return False
    # cherche level{level_id}.ogg ou .mp3
    for ext in (".ogg", ".mp3", ".wav"):
        path = os.path.join(ASSETS, f"level{level_id}{ext}")
        if os.path.isfile(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play(-1)
                return True
            except Exception:
                return False
    # stop music only if mixer available
    try:
        if mixer_available():
            pygame.mixer.music.stop()
    except Exception:
        pass
    return False


# Définition simple des niveaux (end_x détermine quand on termine le niveau)
LEVELS = {
    1: {"end_x": 600, "gravity_inverted": False, "name": "Plaine"},
    2: {"end_x": 1200, "gravity_inverted": True, "name": "Ciels inversés"},
    3: {"end_x": 1800, "gravity_inverted": False, "name": "Dernier défi"},
}


adventure_mode = False
score = 0


# Obstacles : liste de dicts {rect, speed, color}
obstacles = []
ENEMIES = []  # Initialize enemies list
SPAWN_EVENT = pygame.USEREVENT + 1
ENEMY_EVENT = pygame.USEREVENT + 2  # Add enemy spawn event
pygame.time.set_timer(SPAWN_EVENT, 1200)  # spawn toutes les 1.2s
pygame.time.set_timer(ENEMY_EVENT, 3000)  # spawn enemy every 3s


# Scale fonts
FONT = pygame.font.SysFont(None, int(24 * SCALE_FACTOR))
bigFONT = pygame.font.SysFont(None, int(40 * SCALE_FACTOR))


# --- load visual assets (optional) ---
player_frames = []
try:
    # try to load multiple player frames: player_1.png, player_2.png, ...
    for i in range(1, 5):
        p = os.path.join(ASSETS, f"player_{i}.png")
        if os.path.isfile(p):
            try:
                player_frames.append(pygame.image.load(p).convert_alpha())
            except Exception:
                pass
except Exception:
    pass

obstacle_img = None
p = os.path.join(ASSETS, "obstacle.png")
if os.path.isfile(p):
    try:
        obstacle_img = pygame.image.load(p).convert_alpha()
    except Exception:
        obstacle_img = None

bg_img = None
p = os.path.join(ASSETS, "bg.png")
if os.path.isfile(p):
    try:
        bg_img = pygame.image.load(p).convert()
    except Exception:
        bg_img = None

enemy_img = None
p = os.path.join(ASSETS, "enemy.png")
if os.path.isfile(p):
    try:
        enemy_img = pygame.image.load(p).convert_alpha()
    except Exception:
        enemy_img = None

# Update use_images to include enemy_img
use_images = bool(player_frames or obstacle_img or bg_img or enemy_img)

frame_counter = 0

# --- New: camera smoothing, particles, collision sfx ---
camera_x = 0
camera_target = 0
camera_smooth = 0.12
camera_offset = int(150 * SCALE_FACTOR)


particles = []

class Particle:
    def __init__(self, x, y, vx, vy, color, life):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = int(4 * SCALE_FACTOR)  # Scale particle size

    def update(self, dt=1):
        self.vy += 0.3  # gravity on particles
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surf, camx):
        alpha = max(0, int(255 * (self.life / self.max_life)))
        if alpha <= 0:
            return
        s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        s.fill((*self.color, alpha))
        surf.blit(s, (int(self.x - camx), int(self.y)))

def spawn_particles(x, y, color=(255,200,50), count=12):
    for _ in range(count):
        vx = random.uniform(-4, 4)
        vy = random.uniform(-8, -2)
        life = random.uniform(30, 60)
        # Add rainbow effect to particles
        hue = random.random()
        color = pygame.Color(0)
        color.hsva = (hue * 360, 80, 100, 100)
        particles.append(Particle(x + random.uniform(-8,8), y + random.uniform(-8,8), 
                                vx, vy, (color.r, color.g, color.b), life))

# optional collision sound
sfx_hit = None
if mixer_available():
    p = os.path.join(ASSETS, "hit.wav")
    if os.path.isfile(p):
        try:
            sfx_hit = pygame.mixer.Sound(p)
        except Exception:
            sfx_hit = None


# --- Fonctions du jeu ---

def spawn_obstacle(level_id):
    # taille et position adaptées au niveau
    w = random.randint(20, 40) * SCALE_FACTOR
    h = random.randint(20, 80) * SCALE_FACTOR
    inverted = LEVELS.get(level_id, {}).get("gravity_inverted", False)
    # position y dépend de la gravité du niveau
    y = 20 if inverted else HAUTEUR - 20 - h
    rect = pygame.Rect(LARGEUR, y, w, h)
    speed = random.randint(3, 6) + (level_id - 1)
    color = (200, 100, 50)
    obstacles.append({"rect": rect, "speed": speed, "color": color, "image": obstacle_img})


def spawn_enemy(level_id):
    # simple flying/patrolling enemy that moves left and can float
    w = random.randint(28, 48) * SCALE_FACTOR
    h = random.randint(20, 40) * SCALE_FACTOR
    # pick a y that keeps enemy above ground (or under ceiling if inverted)
    inverted = LEVELS.get(level_id, {}).get("gravity_inverted", False)
    if inverted:
        y = random.randint(plafond.bottom + 20, HAUTEUR // 2)
    else:
        y = random.randint(40, sol.top - h - 10)
    rect = pygame.Rect(LARGEUR, y, w, h)
    speed = random.uniform(2.5, 5.0) + (level_id - 1) * 0.6
    # give enemy a small vertical bobbing amplitude & phase
    bob_amp = random.uniform(4, 12)
    bob_phase = random.uniform(0, 3.14)
    color = (100, 180, 255)
    ENEMIES.append({"rect": rect, "speed": speed, "color": color, "image": enemy_img, "bob_amp": bob_amp, "bob_phase": bob_phase})


# Add after other global variables
current_level_chunks = []

# Replace reset_level function
def reset_level(level_id):
    global vitesse_y, au_sol, obstacles, gravite_inversee, ENEMIES, current_level_chunks
    joueur.x = 50
    gravite_inversee = LEVELS[level_id]["gravity_inverted"]
    joueur.y = plafond.bottom if gravite_inversee else sol.top - joueur.height
    vitesse_y = 0
    au_sol = False
    obstacles = []
    ENEMIES = []
    current_level_chunks = generate_level(level_id)
    load_music_for_level(level_id)


# Charge la musique du niveau initial si présente
load_music_for_level(niveau)


# Add leaderboard functions
def load_leaderboard():
    try:
        if os.path.exists(LEADERBOARD_FILE):
            with open(LEADERBOARD_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return []  # Default empty leaderboard

def save_score(player_name, score):
    scores = load_leaderboard()
    scores.append({"name": player_name, "score": score})
    scores.sort(key=lambda x: x["score"], reverse=True)
    scores = scores[:10]  # Keep top 10
    try:
        with open(LEADERBOARD_FILE, 'w') as f:
            json.dump(scores, f)
    except Exception:
        pass

def draw_leaderboard(surface):
    scores = load_leaderboard()
    title = bigFONT.render("MEILLEURS SCORES", True, (255, 255, 100))
    surface.blit(title, (LARGEUR - 300, 10))
    
    y = 60
    for i, score in enumerate(scores[:5]):  # Show top 5
        text = FONT.render(f"{i+1}. {score['name']}: {score['score']}", True, (230, 230, 230))
        surface.blit(text, (LARGEUR - 280, y))
        y += 30

# Add game over handling
def handle_game_over():
    # Create text input for name
    player_name = ""
    name_entered = False
    
    while not name_entered:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and player_name:
                    save_score(player_name, score)
                    name_entered = True
                elif event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]
                elif len(player_name) < 10:  # Max 10 characters
                    if event.unicode.isalnum():  # Only allow letters and numbers
                        player_name += event.unicode
        
        # Draw game over screen
        FENETRE.fill((0, 0, 0))
        game_over_text = bigFONT.render("GAME OVER", True, (255, 50, 50))
        name_prompt = FONT.render("Entrez votre nom:", True, (230, 230, 230))
        name_text = FONT.render(player_name + "_", True, (230, 230, 230))
        
        FENETRE.blit(game_over_text, (LARGEUR//2 - game_over_text.get_width()//2, HAUTEUR//3))
        FENETRE.blit(name_prompt, (LARGEUR//2 - name_prompt.get_width()//2, HAUTEUR//2))
        FENETRE.blit(name_text, (LARGEUR//2 - name_text.get_width()//2, HAUTEUR//2 + 40))
        
        draw_leaderboard(FENETRE)
        pygame.display.update()
        clock.tick(60)
    
    return True

# Add exit menu and escape key handling
def show_exit_menu():
    exit_menu = True
    while exit_menu:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:  # Press ESC again to cancel
                    return False
                if event.key == pygame.K_RETURN:  # Press Enter to confirm exit
                    return True
                
        # Draw exit menu
        overlay = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Semi-transparent black
        FENETRE.blit(overlay, (0, 0))
        
        exit_text = bigFONT.render("Quitter le jeu ?", True, (255, 255, 255))
        instructions = FONT.render("ENTER: Confirmer  |  ESC: Annuler", True, (200, 200, 200))
        
        FENETRE.blit(exit_text, (LARGEUR//2 - exit_text.get_width()//2, HAUTEUR//2 - 40))
        FENETRE.blit(instructions, (LARGEUR//2 - instructions.get_width()//2, HAUTEUR//2 + 20))
        
        pygame.display.update()
        clock.tick(60)

# Add after COLORS definition
TILES = {
    'GROUND': 0,
    'PLATFORM': 1,
    'PIPE': 2,
    'COIN': 3,
    'GAP': 4
}

def generate_level(level_id):
    chunks = []
    length = LEVELS[level_id]["end_x"]
    chunk_size = 200
    current_x = 0
    
    while current_x < length:
        # Choose a chunk type
        chunk_type = random.choice(['flat', 'platform', 'pipes', 'gap'])
        chunk = []
        
        if chunk_type == 'flat':
            # Flat ground with occasional coins
            for x in range(0, chunk_size, 40):
                if random.random() < 0.2:  # 20% chance for coin
                    chunk.append({'type': TILES['COIN'], 'x': current_x + x, 'y': HAUTEUR - 100})
                chunk.append({'type': TILES['GROUND'], 'x': current_x + x, 'y': HAUTEUR - 20})
        
        elif chunk_type == 'platform':
            # Platforms at different heights
            platform_y = random.randint(HAUTEUR - 150, HAUTEUR - 80)
            platform_width = random.randint(80, 160)
            for x in range(0, platform_width, 40):
                chunk.append({'type': TILES['PLATFORM'], 'x': current_x + x, 'y': platform_y})
                if random.random() < 0.3:  # Coins above platform
                    chunk.append({'type': TILES['COIN'], 'x': current_x + x, 'y': platform_y - 40})
        
        elif chunk_type == 'pipes':
            # Add pipes of varying heights
            pipe_height = random.randint(60, 120)
            chunk.append({'type': TILES['PIPE'], 'x': current_x + chunk_size//2, 
                         'y': HAUTEUR - pipe_height, 'height': pipe_height})
        
        elif chunk_type == 'gap':
            # Create a gap with a platform
            gap_width = random.randint(80, 120)
            platform_x = current_x + (chunk_size - gap_width)//2
            chunk.append({'type': TILES['PLATFORM'], 'x': platform_x, 'y': HAUTEUR - 100,
                         'width': gap_width})
            # Add coins above gap
            for x in range(gap_width):
                if x % 40 == 0:
                    chunk.append({'type': TILES['COIN'], 'x': platform_x + x, 'y': HAUTEUR - 160})
        
        chunks.extend(chunk)
        current_x += chunk_size
    
    return chunks

# Add to the main game loop drawing section, before drawing obstacles:
    # Draw level chunks
    for chunk in current_level_chunks:
        draw_x = chunk['x'] - camera_x
        if draw_x < -50 or draw_x > LARGEUR + 50:  # Simple culling
            continue
            
        if chunk['type'] == TILES['GROUND']:
            pygame.draw.rect(FENETRE, COLORS['ground'], 
                           (draw_x, chunk['y'], 40, HAUTEUR - chunk['y']))
        
        elif chunk['type'] == TILES['PLATFORM']:
            w = chunk.get('width', 40)
            pygame.draw.rect(FENETRE, (139, 69, 19), 
                           (draw_x, chunk['y'], w, 20))
        
        elif chunk['type'] == TILES['PIPE']:
            # Draw pipe
            pygame.draw.rect(FENETRE, (40, 180, 40),
                           (draw_x, chunk['y'], 60, chunk['height']))
            # Pipe top
            pygame.draw.rect(FENETRE, (60, 200, 60),
                           (draw_x - 5, chunk['y'], 70, 20))
        
        elif chunk['type'] == TILES['COIN']:
            # Animate coin
            bounce = math.sin(pygame.time.get_ticks() * 0.008) * 5
            pygame.draw.circle(FENETRE, (255, 215, 0), 
                             (int(draw_x + 10), int(chunk['y'] + bounce + 10)), 10)


# Add after pygame initialization and before game variables
COLORS = {
    'bg_top': (41, 128, 185),      # Bright blue
    'bg_bottom': (142, 68, 173),   # Purple
    'player': (46, 204, 113),      # Emerald green
    'obstacle': (231, 76, 60),     # Bright red
    'enemy': (241, 196, 15),       # Yellow
    'ground': (39, 174, 96)        # Green
}

# Boucle principale du jeu
while jeu_actif:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if show_exit_menu():
                jeu_actif = False
            continue
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if show_exit_menu():
                    jeu_actif = False
                continue
            if event.key == pygame.K_r:
                # restart current level
                reset_level(niveau)
                score = 0
            if event.key == pygame.K_a:
                # toggle adventure mode
                adventure_mode = not adventure_mode
                # reset to level 1 when entering adventure
                if adventure_mode:
                    niveau = 1
                    reset_level(niveau)
                else:
                    # stop music when leaving adventure (guarded)
                    try:
                        if mixer_available():
                            pygame.mixer.music.stop()
                    except Exception:
                        pass


    touches = pygame.key.get_pressed()
    if touches[pygame.K_RIGHT]:
        joueur.x += vitesse_x
    if touches[pygame.K_LEFT]:
        joueur.x -= vitesse_x
    if touches[pygame.K_SPACE] and au_sol:
        vitesse_y = saut if not gravite_inversee else -saut
        au_sol = False


    vitesse_y += -gravite if gravite_inversee else gravite
    joueur.y += vitesse_y

    # clamp vertical position to window to avoid leaving screen
    joueur.y = max(0, min(joueur.y, HAUTEUR - joueur.height))

    # clamp horizontal position to window
    joueur.x = max(0, min(joueur.x, LARGEUR - joueur.width))


    # Niveau basé sur position x (mode aventure)
    if adventure_mode:
        if joueur.x >= LEVELS[niveau]["end_x"]:
            # passe au niveau suivant si existe
            if niveau + 1 in LEVELS:
                niveau += 1
                reset_level(niveau)
            else:
                # fin de l'aventure
                try:
                    if mixer_available():
                        pygame.mixer.music.stop()
                except Exception:
                    pass
                jeu_actif = False
    else:
        # mode libre : inversion selon x (comportement précédent)
        if joueur.x >= 600:
            gravite_inversee = True
            niveau = 2
        else:
            gravite_inversee = False
            niveau = 1


    # Gestion des collisions sol/plafond
    if gravite_inversee:
        if joueur.top <= plafond.bottom:
            joueur.top = plafond.bottom
            vitesse_y = 0
            au_sol = True
    else:
        if joueur.bottom >= sol.top:
            joueur.bottom = sol.top
            vitesse_y = 0
            au_sol = True


    # Obstacles movement & collision
    for ob in obstacles[:]:
        ob["rect"].x -= ob["speed"]
        # collision
        if joueur.colliderect(ob["rect"]):
            # spawn visual feedback
            spawn_particles(joueur.centerx, joueur.centery, color=(220,60,60), count=18)
            # play collision sfx if available
            try:
                if sfx_hit:
                    sfx_hit.play()
            except Exception:
                pass
            # penalize and reset
            score = max(0, score - 5)
            reset_level(niveau)
            break
        # remove if off screen
        if ob["rect"].right < 0:
            obstacles.remove(ob)
            score += 1


    # Enemies movement, collision
    for en in ENEMIES[:]:
        # horizontal movement
        en["rect"].x -= en["speed"]
        # vertical bobbing (visual only)
        en["rect"].y += int(en["bob_amp"] * 0.05 * math.sin(pygame.time.get_ticks() * 0.002 + en["bob_phase"]))
        # collision with player
        if joueur.colliderect(en["rect"]):
            spawn_particles(joueur.centerx, joueur.centery, color=(100,180,255), count=14)
            try:
                if sfx_hit:
                    sfx_hit.play()
            except Exception:
                pass
            score = max(0, score - 8)
            reset_level(niveau)
            break
        # remove if off screen
        if en["rect"].right < 0:
            ENEMIES.remove(en)
            score += 2


    if joueur.x >= 1800 and not adventure_mode:
        jeu_actif = handle_game_over()  # Show game over screen and get player name


    # dessine / visual layer with camera
    # simple camera following player (horizontal only)
    camera_target = max(0, int(joueur.x) - camera_offset)
    camera_x += (camera_target - camera_x) * camera_smooth

    # gradient background
    grad = pygame.Surface((LARGEUR, HAUTEUR))
    top_color = (41, 128, 185)    # Bright blue
    bottom_color = (142, 68, 173)  # Purple
    for i in range(HAUTEUR):
        t = i / HAUTEUR
        r = int(top_color[0] * (1-t) + bottom_color[0] * t)
        g = int(top_color[1] * (1-t) + bottom_color[1] * t)
        b = int(top_color[2] * (1-t) + bottom_color[2] * t)
        pygame.draw.line(grad, (r, g, b), (0, i), (LARGEUR, i))
    FENETRE.blit(grad, (0, 0))

    # parallax "cloud" layer
    cloud_width = int(180 * SCALE_FACTOR)
    cloud_height = int(60 * SCALE_FACTOR)
    cloud_spacing = int(300 * SCALE_FACTOR)
    cloud_color = (255, 255, 255, 40)
    for i in range(6):
        cx = (i * cloud_spacing - (camera_x * 0.25)) % (LARGEUR + cloud_spacing) - cloud_spacing//2
        cy = 60 * SCALE_FACTOR + (i % 3) * 30 * SCALE_FACTOR
        # soft cloud with circles
        c_surf = pygame.Surface((cloud_width, cloud_height), pygame.SRCALPHA)
        for j in range(4):
            alpha = int(180 + 75 * math.sin(pygame.time.get_ticks() * 0.001 + j))
            pygame.draw.ellipse(c_surf, (255,255,255,alpha), (j*30, 0, 110, 40))
        FENETRE.blit(c_surf, (cx, cy))

    # ground texture: tiled rectangles
    pattern_w = 40 * SCALE_FACTOR
    ground_h = 20 * SCALE_FACTOR
    start = - (camera_x % pattern_w)
    x = start
    while x < LARGEUR:
        rect = pygame.Rect(x, HAUTEUR - ground_h, pattern_w - 6, ground_h)
        pygame.draw.rect(FENETRE, COLORS['ground'], rect)
        glow = pygame.Surface((pattern_w, ground_h), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*COLORS['ground'], 40), glow.get_rect())
        FENETRE.blit(glow, (x, HAUTEUR - ground_h - 5))
        x += pattern_w

    # draw obstacles (with world->screen offset)
    for ob in obstacles:
        draw_x = ob["rect"].x - camera_x
        draw_y = ob["rect"].y
        if ob.get("image"):
            try:
                img = pygame.transform.scale(ob["image"], (ob["rect"].width, ob["rect"].height))
                FENETRE.blit(img, (draw_x, draw_y))
            except Exception:
                pygame.draw.rect(FENETRE, ob["color"], pygame.Rect(draw_x, draw_y, ob["rect"].width, ob["rect"].height))
        else:
            # stylized obstacle: rotated rectangle look
            base = pygame.Surface((ob["rect"].width, ob["rect"].height), pygame.SRCALPHA)
            base.fill(ob["color"])
            pygame.draw.rect(base, (40,40,40), base.get_rect(), 2)
            FENETRE.blit(base, (draw_x, draw_y))

    # draw enemies in the visual layer (merge into drawing section where obstacles are drawn)
    for en in ENEMIES:
        draw_x = en["rect"].x - camera_x
        draw_y = en["rect"].y
        if en.get("image"):
            try:
                img = pygame.transform.scale(en["image"], (en["rect"].width, en["rect"].height))
                # optional flip to face left
                img = pygame.transform.flip(img, True, False)
                FENETRE.blit(img, (draw_x, draw_y))
            except Exception:
                pygame.draw.ellipse(FENETRE, en["color"], pygame.Rect(draw_x, draw_y, en["rect"].width, en["rect"].height))
        else:
            # stylized procedural enemy: rounded rect / ellipse with eye
            surf = pygame.Surface((en["rect"].width, en["rect"].height), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, en["color"], surf.get_rect())
            pygame.draw.ellipse(surf, (30,30,30), surf.get_rect(), 2)
            # eye
            ex = int(en["rect"].width * 0.65)
            ey = int(en["rect"].height * 0.35)
            pygame.draw.circle(surf, (255,255,255), (ex, ey), max(2, en["rect"].width//8))
            pygame.draw.circle(surf, (20,20,40), (ex, ey), max(1, en["rect"].width//12))
            FENETRE.blit(surf, (draw_x, draw_y))

    # draw player
    player_draw_x = joueur.x - camera_x
    player_draw_y = joueur.y
    if player_frames:
        idx = (frame_counter // 8) % len(player_frames)
        player_img = player_frames[idx]
        if gravite_inversee:
            player_img = pygame.transform.flip(player_img, False, True)
        try:
            player_surf = pygame.transform.scale(player_img, (joueur.width, joueur.height))
            FENETRE.blit(player_surf, (player_draw_x, player_draw_y))
        except Exception:
            pygame.draw.rect(FENETRE, (255,0,0), pygame.Rect(player_draw_x, player_draw_y, joueur.width, joueur.height))
    else:
        # procedural player: circle with simple squash/stretch based on vertical speed
        h = joueur.height
        w = joueur.width
        stretch = max(0.7, 1 - abs(vitesse_y)/30)
        draw_w = int(w * (1 + (1-stretch)*0.3))
        draw_h = int(h * (1 + (stretch-1)*0.6))
        surf = pygame.Surface((draw_w, draw_h), pygame.SRCALPHA)
        # Add glow effect
        glow_surf = pygame.Surface((draw_w+8, draw_h+8), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_surf, (*COLORS['player'], 60), glow_surf.get_rect())
        FENETRE.blit(glow_surf, (player_draw_x + (w-draw_w)//2 - 4, player_draw_y + (h-draw_h)//2 - 4))
        # Draw player
        pygame.draw.ellipse(surf, COLORS['player'], (0, 0, draw_w, draw_h))
        # Add shine effect
        shine = pygame.Surface((draw_w//2, draw_h//2), pygame.SRCALPHA)
        pygame.draw.ellipse(shine, (255,255,255,100), shine.get_rect())
        surf.blit(shine, (draw_w//4, draw_h//4))
        FENETRE.blit(surf, (player_draw_x + (w-draw_w)//2, player_draw_y + (h-draw_h)//2))

    # update and draw particles
    for p in particles[:]:
        p.update()
        p.draw(FENETRE, camera_x)
        if p.life <= 0:
            particles.remove(p)

    # HUD
    level_name = LEVELS.get(niveau, {}).get("name", f"Niveau {niveau}")
    hud_lines = [
        f"Mode: {'Aventure' if adventure_mode else 'Libre'}  |  Niveau: {niveau} - {level_name}",
        f"Score: {score}  |  Gravité inversée: {gravite_inversee}",
        "Touches: ← → pour bouger, SPACE pour sauter, A pour toggle Adventure, R pour reset level"
    ]
    y = 10
    for line in hud_lines:
        surf = FONT.render(line, True, (230,230,230))
        FENETRE.blit(surf, (10, y))
        y += 20


    # petit message de fin si needed
    draw_leaderboard(FENETRE)
    pygame.display.update()
    clock.tick(60)


pygame.quit()