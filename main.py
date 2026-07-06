import pygame
import random
import math
import sys
import os

# Configuraciones globales
WIDTH, HEIGHT = 1100, 800
FPS = 60

# Paleta de colores (Un poco de estilo no hace daño)
C_BG = (10, 12, 25)
C_PLAYER = (0, 255, 200)
C_DASH = (255, 50, 150)
C_OBS = (40, 180, 140)
C_ENEMY = (200, 40, 255)
C_COIN = (255, 215, 0)
C_TEXT = (255, 255, 255)

# Diccionario global de assets
IMAGES = {}

def cargar_imagenes():
    """Carga y escala las imágenes para que coincidan con las dimensiones lógicas."""
    try:
        IMAGES['fondo'] = pygame.transform.scale(pygame.image.load('fondo.png').convert(), (WIDTH, HEIGHT))
        IMAGES['personaje'] = pygame.transform.scale(pygame.image.load('personaje.png').convert_alpha(), (32, 32))
        IMAGES['dash'] = pygame.transform.scale(pygame.image.load('dash.png').convert_alpha(), (32, 32))
        IMAGES['enemigo'] = pygame.transform.scale(pygame.image.load('enemigo.png').convert_alpha(), (32, 32))
        IMAGES['moneda'] = pygame.transform.scale(pygame.image.load('moneda.png').convert_alpha(), (20, 20))
        IMAGES['obstaculo'] = pygame.image.load('obstaculo.png').convert_alpha()
        
        # UI
        IMAGES['menu'] = pygame.transform.scale(pygame.image.load('menu.png').convert_alpha(), (WIDTH, HEIGHT)) 
        IMAGES['game_over'] = pygame.transform.scale(pygame.image.load('game over.png').convert_alpha(), (WIDTH, HEIGHT))
        IMAGES['barra_dash'] = pygame.transform.scale(pygame.image.load('barra dash.png').convert_alpha(), (200, 20))
        
    except FileNotFoundError as e:
        print(f"Error crítico: Falta la imagen {e.filename}.")
        print("Revisa que los archivos estén en la misma carpeta que el script principal.")
        sys.exit()

class Player:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = 150
        self.y = HEIGHT // 2
        self.vel_y = 0
        self.energy = 100
        self.dashing = False
        self.dash_timer = 0
        self.trail = []
        # Aplicando un poco de cinemática básica para la gravedad (Física III me persigue)
        self.gravity = 0.6
        self.boost_gravity = 0.2

    def update(self, boost):
        if self.dashing:
            self.dash_timer -= 1
            if self.dash_timer <= 0:
                self.dashing = False
        else:
            self.vel_y += self.boost_gravity if boost else self.gravity
            self.vel_y = min(self.vel_y, 12)
            self.y += self.vel_y
            self.energy = min(100, self.energy + 0.2)

        # Efecto de rastro
        self.trail.append((self.y, self.dashing))
        if len(self.trail) > 8:
            self.trail.pop(0)

    def draw(self, surface):
        for i, (ty, dash) in enumerate(self.trail):
            color = C_DASH if dash else C_PLAYER
            size = i * 1.5
            pygame.draw.circle(surface, color, (int(self.x) - (8 - i) * 6, int(ty)), int(size))

        img = IMAGES['dash'] if self.dashing else IMAGES['personaje']
        surface.blit(img, (int(self.x) - 16, int(self.y) - 16))

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.base_y = y
        self.y = y
        self.time = random.uniform(0, 10)
        self.radius = 16

    def update(self, speed):
        self.x -= speed * 1.2
        self.time += 0.05
        self.y = self.base_y + math.sin(self.time) * 45

    def collides(self, px, py, radius):
        dist = math.hypot(self.x - px, self.y - py) # Optimizado usando hypot
        return dist < (self.radius + radius)

    def draw(self, surface):
        surface.blit(IMAGES['enemigo'], (int(self.x) - 16, int(self.y) - 16))
        # Hitbox visual (TODO: quitar esto en la versión de producción)
        # pygame.draw.circle(surface, (255, 60, 60), (int(self.x), int(self.y)), self.radius + 2, 2)

class Obstacle:
    def __init__(self, x, gap_y, gap_size):
        self.x = x
        self.gap_y = gap_y
        self.gap_size = gap_size
        self.width = 60
        self.passed = False
        
        # Pre-calculamos las imágenes para no hacer escalado en cada frame (Optimización)
        img_top_raw = pygame.transform.scale(IMAGES['obstaculo'], (self.width, self.gap_y))
        self.img_top = pygame.transform.flip(img_top_raw, False, True) 
        
        bot_height = HEIGHT - (self.gap_y + self.gap_size)
        self.img_bot = pygame.transform.scale(IMAGES['obstaculo'], (self.width, bot_height))

    def update(self, speed):
        self.x -= speed

    def collides(self, px, py, radius):
        rect_top = pygame.Rect(self.x, 0, self.width, self.gap_y)
        rect_bot = pygame.Rect(self.x, self.gap_y + self.gap_size, self.width, HEIGHT)
        p_rect = pygame.Rect(px - radius, py - radius, radius * 2, radius * 2)
        return rect_top.colliderect(p_rect) or rect_bot.colliderect(p_rect)

    def draw(self, surface):
        surface.blit(self.img_top, (self.x, 0))
        surface.blit(self.img_bot, (self.x, self.gap_y + self.gap_size))

class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def update(self, speed):
        self.x -= speed

    def collides(self, px, py, radius):
        dist = math.hypot(self.x - px, self.y - py)
        return dist < (10 + radius)

    def draw(self, surface):
        surface.blit(IMAGES['moneda'], (int(self.x) - 10, int(self.y) - 10))

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Quantum Flapper")
        self.clock = pygame.time.Clock()
        
        cargar_imagenes()
        self._cargar_sonidos() 
        
        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.title_font = pygame.font.SysFont("Arial Black", 48)
        
        self.player = Player()
        # Generamos estrellas de fondo de forma aleatoria
        self.stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), r % 3 + 1] for r in range(50)]
        self.high_score = self._load_hs()
        
        self.shake_timer = 0 # Para el efecto de temblor de cámara
        self.reset()
        self.state = "MENU" 

    def _cargar_sonidos(self):
        self.sfx = {}
        try:
            self.sfx['jump'] = pygame.mixer.Sound('jump.mp3')
            self.sfx['collect'] = pygame.mixer.Sound('collect.mp3')
            self.sfx['game_over'] = pygame.mixer.Sound('game over.mp3')
            
            try: self.sfx['dash'] = pygame.mixer.Sound('dash.mp3')
            except FileNotFoundError: self.sfx['dash'] = None
            
            pygame.mixer.music.load('musica juego.mp3')
        except pygame.error as e:
            print(f"Advertencia: No se cargó un audio. {e}")

    def play_sfx(self, name):
        if name in self.sfx and self.sfx[name] is not None:
            self.sfx[name].play()

    def _load_hs(self):
        if os.path.exists("hs.txt"):
            with open("hs.txt", "r") as f: return float(f.read())
        return 0.0

    def _save_hs(self):
        with open("hs.txt", "w") as f: f.write(str(float(self.high_score)))

    def reset(self):
        self.player.reset()
        self.score = 0.0
        self.nivel = 1
        self.base_speed = 5.0
        self.next_level_score = 500.0
        
        self.obstacles = []
        self.coins = []
        self.enemies = []
        self.spawn_timer = 0
        self.shake_timer = 0

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

    def handle_events(self):
        boost = False
        dash = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE: boost = True
                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_d): dash = True
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: boost = True
                if event.button == 3: dash = True

        if self.state in ("MENU", "GAME_OVER") and boost:
            self.reset()
            self.state = "PLAYING"
            pygame.mixer.music.play(-1)
            
        elif self.state == "PLAYING":
            if boost and not self.player.dashing:
                self.player.vel_y = -8
                self.play_sfx('jump') 
                
            if dash and self.player.energy >= 30 and not self.player.dashing:
                self.player.energy -= 30
                self.player.dashing = True
                self.player.dash_timer = 15
                self.player.vel_y = 0
                self.play_sfx('dash') 
                self.shake_timer = 10 # Magia para el game feel

    def update(self):
        if self.state != "PLAYING":
            return
            
        keys = pygame.key.get_pressed()
        is_boosting = keys[pygame.K_SPACE] or pygame.mouse.get_pressed()[0]
        
        self.player.update(is_boosting)
        
        if self.player.y < -20 or self.player.y > HEIGHT + 20:
            self._die()

        current_speed = self.base_speed * (2.5 if self.player.dashing else 1)
        self.score += current_speed * 0.05
        
        # Lógica de niveles
        if self.score >= self.next_level_score:
            self.nivel += 1
            self.base_speed += 1.5
            self.next_level_score += 500.0
            self.play_sfx('collect') # Feedback auditivo al subir nivel
            self.shake_timer = 15

        self.spawn_timer -= current_speed
        
        # Paralaje del fondo (estrellas)
        for star in self.stars:
            star[0] -= star[2] * (2 if self.player.dashing else 1)
            if star[0] < 0:
                star[0], star[1] = WIDTH, random.randint(0, HEIGHT)

        if self.spawn_timer <= 0:
            if random.random() < 0.3:
                self.enemies.append(Enemy(WIDTH + 20, random.randint(100, HEIGHT - 100)))
            else:
                gap_size = 170 - (self.nivel * 5) # El hueco se hace más pequeño cada nivel
                gap_size = max(90, gap_size) # Pero nunca menos de 90 píxeles
                gap_y = random.randint(50, HEIGHT - 50 - gap_size)
                self.obstacles.append(Obstacle(WIDTH, gap_y, gap_size))
                
                if random.random() < 0.6:
                    self.coins.append(Coin(WIDTH + 30, gap_y + gap_size // 2))
                    
            # Aumentamos la frecuencia de aparición en niveles altos
            r_max = max(150, 350 - (self.nivel * 20))
            self.spawn_timer = random.randint(150, r_max)

        self._check_collisions(current_speed)

    def _check_collisions(self, speed):
        for obs in self.obstacles[:]:
            obs.update(speed)
            if obs.x < -100:
                self.obstacles.remove(obs)
            elif not self.player.dashing and obs.collides(self.player.x, self.player.y, 14):
                self._die()
            elif not obs.passed and obs.x + obs.width < self.player.x:
                obs.passed = True
                self.score += 50.0
                
        for coin in self.coins[:]:
            coin.update(speed)
            if coin.x < -50:
                self.coins.remove(coin)
            elif coin.collides(self.player.x, self.player.y, 16):
                self.coins.remove(coin)
                self.score += 100.0
                self.player.energy = min(100, self.player.energy + 20)
                self.play_sfx('collect') 

        for enemy in self.enemies[:]:
            enemy.update(speed)
            if enemy.x < -50:
                self.enemies.remove(enemy)
            elif enemy.collides(self.player.x, self.player.y, 16):
                if self.player.dashing:
                    self.enemies.remove(enemy)
                    self.score += 150.0 
                    self.shake_timer = 5
                else:
                    self.play_sfx('game_over')
                    self._die()

    def _die(self):
        if self.state != "GAME_OVER": 
            pygame.mixer.music.stop()     
            self.play_sfx('game_over')    
            
        self.state = "GAME_OVER"
        if self.score > self.high_score:
            self.high_score = self.score
            self._save_hs()

    # Función helper para dar formato a los números (usa ',' como separador)
    def _format_num(self, value):
        return f"{value:.3g}".replace('.', ',')

    def draw(self):
        # Lógica de Screen Shake
        offset_x, offset_y = 0, 0
        if self.shake_timer > 0:
            offset_x = random.randint(-5, 5)
            offset_y = random.randint(-5, 5)
            self.shake_timer -= 1
            
        # Dibujamos todo en una superficie temporal si quisiéramos escalar, 
        # pero para optimizar aplicamos el offset directamente
        self.screen.fill(C_BG)
        self.screen.blit(IMAGES['fondo'], (offset_x, offset_y))
        
        for s in self.stars:
            pygame.draw.rect(self.screen, (100, 100, 130), (s[0] + offset_x, s[1] + offset_y, s[2], s[2]))

        if self.state in ("PLAYING", "GAME_OVER"):
            # Dedicado a Firu y Milo 🐶 - TODO: Hacer skins para ellos después
            for obs in self.obstacles: obs.draw(self.screen)
            for coin in self.coins: coin.draw(self.screen)
            for enemy in self.enemies: enemy.draw(self.screen)
            self.player.draw(self.screen)
            self._draw_hud()

        if self.state == "MENU":
            self.screen.blit(IMAGES['menu'], (0, 0))
            self._draw_center_text(f"MEJOR PUNTUACIÓN: {self._format_num(self.high_score)}", HEIGHT // 2 + 50, self.font, C_COIN)
            self._draw_center_text("Pulsa SALTAR para iniciar", HEIGHT - 80, self.font, C_DASH)
            
        elif self.state == "GAME_OVER":
            self.screen.blit(IMAGES['game_over'], (0, 0))
            self._draw_center_text(f"PUNTUACIÓN: {self._format_num(self.score)}", HEIGHT // 2, self.font, C_TEXT)
            color_hs = C_COIN if self.score >= self.high_score else C_TEXT
            self._draw_center_text(f"MEJOR: {self._format_num(self.high_score)}", HEIGHT // 2 + 40, self.font, color_hs)
            self._draw_center_text("Pulsa SALTAR para reintentar", HEIGHT - 80, self.font, C_PLAYER)

        pygame.display.flip()

    def _draw_hud(self):
        score_txt = self.font.render(f"PUNTOS: {self._format_num(self.score)}", True, C_TEXT)
        lvl_txt = self.font.render(f"NIVEL: {self._format_num(self.nivel)}", True, C_COIN)
        
        self.screen.blit(score_txt, (20, 20))
        self.screen.blit(lvl_txt, (WIDTH - 120, 20))
        
        if self.player.energy > 0:
            ancho_actual = int(200 * (self.player.energy / 100.0))
            area_recorte = (0, 0, ancho_actual, 20)
            self.screen.blit(IMAGES['barra_dash'], (20, HEIGHT - 40), area_recorte)
            
        pygame.draw.rect(self.screen, C_TEXT, (20, HEIGHT - 40, 200, 20), 2, border_radius=5)

    def _draw_center_text(self, text, y, font, color):
        img = font.render(text, True, color)
        self.screen.blit(img, (WIDTH // 2 - img.get_width() // 2, y))

if __name__ == "__main__":
    Game().run()