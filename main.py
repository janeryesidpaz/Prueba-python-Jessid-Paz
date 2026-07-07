import math
import os
import random
import sys
from collections import deque

import pygame

WIDTH, HEIGHT = 1100, 800
FPS = 60

C_BG = (10, 12, 25)
C_PLAYER = (0, 255, 200)
C_DASH = (255, 50, 150)
C_OBS = (40, 180, 140)
C_ENEMY = (200, 40, 255)
C_COIN = (255, 215, 0)
C_TEXT = (255, 255, 255)

IMAGES = {}
def cargar_imagenes():
    try:
        IMAGES['fondo'] = pygame.transform.scale(pygame.image.load('fondo.png').convert(), (WIDTH, HEIGHT))
        IMAGES['personaje'] = pygame.transform.scale(pygame.image.load('personaje.png').convert_alpha(), (32, 32))
        IMAGES['dash'] = pygame.transform.scale(pygame.image.load('dash.png').convert_alpha(), (32, 32))
        IMAGES['enemigo'] = pygame.transform.scale(pygame.image.load('enemigo.png').convert_alpha(), (32, 32))
        IMAGES['moneda'] = pygame.transform.scale(pygame.image.load('moneda.png').convert_alpha(), (20, 20))
        IMAGES['obstaculo'] = pygame.image.load('obstaculo.png').convert_alpha()
        IMAGES['menu'] = pygame.transform.scale(pygame.image.load('menu.png').convert_alpha(), (WIDTH, HEIGHT))
        IMAGES['game_over'] = pygame.transform.scale(pygame.image.load('game over.png').convert_alpha(), (WIDTH, HEIGHT))
        IMAGES['barra_dash'] = pygame.transform.scale(pygame.image.load('barra dash.png').convert_alpha(), (200, 20))
    except FileNotFoundError as e:
        print(f"Error crítico: Falta la imagen {e.filename}.")
        sys.exit(1)

class Player:
    def __init__(self):
        self.gravity = 0.6
        self.boost_gravity = 0.2
        self.reset()

    def reset(self):
        self.x = 150
        self.y = HEIGHT // 2
        self.vel_y = 0
        self.energy = 100
        self.dashing = False
        self.dash_timer = 0
        self.trail = deque(maxlen=8)

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

        self.trail.append((self.y, self.dashing))

    def draw(self, surface):
        for i, (ty, dash) in enumerate(self.trail):
            color = C_DASH if dash else C_PLAYER
            size = i * 1.5
            x_pos = int(self.x) - (8 - i) * 6
            pygame.draw.circle(surface, color, (x_pos, int(ty)), int(size))

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
        return math.hypot(self.x - px, self.y - py) < (self.radius + radius)

    def draw(self, surface):
        surface.blit(IMAGES['enemigo'], (int(self.x) - 16, int(self.y) - 16))

class Obstacle:
    def __init__(self, x, gap_y, gap_size):
        self.x = x
        self.gap_y = gap_y
        self.gap_size = gap_size
        self.width = 60
        self.passed = False
        
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
        return math.hypot(self.x - px, self.y - py) < (10 + radius)

    def draw(self, surface):
        surface.blit(IMAGES['moneda'], (int(self.x) - 10, int(self.y) - 10))

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Future bird")
        self.clock = pygame.time.Clock()
        
        cargar_imagenes()
        self._cargar_sonidos()
        
        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.title_font = pygame.font.SysFont("Arial Black", 48)
        
        self.player = Player()
        self.stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), r % 3 + 1] for r in range(50)]
        
        self.high_score_file = "hs.txt"
        self.high_score = self._load_hs()
        
        self.reset()
        self.state = "MENU"

    def _cargar_sonidos(self):
        self.sfx = {}
        try:
            self.sfx['jump'] = pygame.mixer.Sound('jump.mp3')
            self.sfx['collect'] = pygame.mixer.Sound('collect.mp3')
            self.sfx['game_over'] = pygame.mixer.Sound('game over.mp3')
            
            try:
                self.sfx['dash'] = pygame.mixer.Sound('dash.mp3')
            except FileNotFoundError:
                self.sfx['dash'] = None
                
            pygame.mixer.music.load('musica juego.mp3')
        except pygame.error as e:
            print(f"Advertencia de audio: {e}")

    def play_sfx(self, name):
        if self.sfx.get(name):
            self.sfx[name].play()

    def _load_hs(self):
        if os.path.isfile(self.high_score_file):
            with open(self.high_score_file, "r") as f:
                return float(f.read().strip() or 0.0)
        return 0.0

    def _save_hs(self):
        with open(self.high_score_file, "w") as f:
            f.write(str(float(self.high_score)))

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
        boost = dash = False
        
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
                self.shake_timer = 10

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
        
        if self.score >= self.next_level_score:
            self.nivel += 1
            self.base_speed += 1.5
            self.next_level_score += 500.0
            self.play_sfx('collect')
            self.shake_timer = 15

        self.spawn_timer -= current_speed
        
        for star in self.stars:
            star[0] -= star[2] * (2 if self.player.dashing else 1)
            if star[0] < 0:
                star[0], star[1] = WIDTH, random.randint(0, HEIGHT)

        if self.spawn_timer <= 0:
            if random.random() < 0.3:
                self.enemies.append(Enemy(WIDTH + 20, random.randint(100, HEIGHT - 100)))
            else:
                gap_size = max(90, 170 - (self.nivel * 5))
                gap_y = random.randint(50, HEIGHT - 50 - gap_size)
                self.obstacles.append(Obstacle(WIDTH, gap_y, gap_size))
                
                if random.random() < 0.6:
                    self.coins.append(Coin(WIDTH + 30, gap_y + gap_size // 2))
                    
            r_max = max(150, 350 - (self.nivel * 20))
            self.spawn_timer = random.randint(150, r_max)

        self._check_collisions(current_speed)

    def _check_collisions(self, speed):
        alive_obstacles = []
        for obs in self.obstacles:
            obs.update(speed)
            if obs.x < -100:
                continue
                
            if not self.player.dashing and obs.collides(self.player.x, self.player.y, 14):
                self._die()
            elif not obs.passed and obs.x + obs.width < self.player.x:
                obs.passed = True
                self.score += 50.0
                
            alive_obstacles.append(obs)
        self.obstacles = alive_obstacles
                
        alive_coins = []
        for coin in self.coins:
            coin.update(speed)
            if coin.x < -50:
                continue
                
            if coin.collides(self.player.x, self.player.y, 16):
                self.score += 100.0
                self.player.energy = min(100, self.player.energy + 20)
                self.play_sfx('collect')
            else:
                alive_coins.append(coin)
        self.coins = alive_coins

        alive_enemies = []
        for enemy in self.enemies:
            enemy.update(speed)
            if enemy.x < -50:
                continue
                
            if enemy.collides(self.player.x, self.player.y, 16):
                if self.player.dashing:
                    self.score += 150.0
                    self.shake_timer = 5
                else:
                    self.play_sfx('game_over')
                    self._die()
            else:
                alive_enemies.append(enemy)
        self.enemies = alive_enemies

    def _die(self):
        if self.state != "GAME_OVER":
            pygame.mixer.music.stop()
            self.play_sfx('game_over')
            
        self.state = "GAME_OVER"
        if self.score > self.high_score:
            self.high_score = self.score
            self._save_hs()

    def _format_num(self, value):
        return f"{int(value):,}".replace(',', '.')

    def draw(self):
        offset_x = random.randint(-5, 5) if self.shake_timer > 0 else 0
        offset_y = random.randint(-5, 5) if self.shake_timer > 0 else 0
        if self.shake_timer > 0: 
            self.shake_timer -= 1
            
        self.screen.fill(C_BG)
        self.screen.blit(IMAGES['fondo'], (offset_x, offset_y))
        
        for s in self.stars:
            pygame.draw.rect(self.screen, (100, 100, 130), (s[0] + offset_x, s[1] + offset_y, s[2], s[2]))

        if self.state in ("PLAYING", "GAME_OVER"):
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
        self.screen.blit(score_txt, (20, 20))
        
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
