"""Enhanced Dodge & Shoot - Big Version
Modular, polished, particle effects, sound hooks, boss phases, mouse-aim + WASD,
screen shake, background parallax, multiple weapons, and upgrade pickups.

Save as: pygame_boss_battle_enhanced.py
Run: pip install pygame
     python pygame_boss_battle_enhanced.py

Notes: optional assets folder supported (images/sfx). If not present, game falls back to shapes/no sound.
"""

import pygame
import random
import sys
import math
import os
from collections import deque

# --------- Configuration ---------
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 720
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 40, 40)
GREEN = (80, 200, 120)
YELLOW = (255, 220, 80)
ORANGE = (255, 140, 40)
PURPLE = (160, 60, 200)
DARK_GRAY = (30, 30, 40)

ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")

# --------- Utility helpers ---------

def load_sound(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None


def clamp(v, a, b):
    return max(a, min(b, v))


# --------- Asset Manager (optional assets) ---------
class Assets:
    def __init__(self):
        self.player_img = None
        self.bullet_img = None
        self.boss_img = None
        self.sounds = {}
        self.load()

    def load(self):
        # Try to load images and sounds from assets folder; silently continue if missing
        try:
            if os.path.isdir(ASSET_DIR):
                pi = os.path.join(ASSET_DIR, "player.png")
                bi = os.path.join(ASSET_DIR, "bullet.png")
                boss_i = os.path.join(ASSET_DIR, "boss.png")
                if os.path.exists(pi):
                    self.player_img = pygame.image.load(pi).convert_alpha()
                if os.path.exists(bi):
                    self.bullet_img = pygame.image.load(bi).convert_alpha()
                if os.path.exists(boss_i):
                    self.boss_img = pygame.image.load(boss_i).convert_alpha()

                # sounds
                for name in ("shoot", "hit", "explode", "boss_hit", "powerup"):
                    p = os.path.join(ASSET_DIR, f"{name}.wav")
                    if os.path.exists(p):
                        self.sounds[name] = load_sound(p)
        except Exception as e:
            print("Asset load warning:", e)


ASSETS = Assets()

# --------- Particle System ---------
class Particle:
    def __init__(self, x, y, vx, vy, life, radius=3, color=ORANGE):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.radius = radius
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.12  # gravity
        self.life -= 1

    def draw(self, surf, offset=(0, 0)):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            surf.set_alpha(None)
            r = max(1, int(self.radius * (self.life / self.max_life)))
            pygame.draw.circle(surf, self.color, (int(self.x - offset[0]), int(self.y - offset[1])), r)


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit_explosion(self, x, y, count=20, color=ORANGE):
        for _ in range(count):
            angle = random.random() * 2 * math.pi
            speed = random.uniform(1, 6)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            p = Particle(x, y, vx, vy, life=random.randint(20, 50), radius=random.randint(2, 5), color=color)
            self.particles.append(p)

    def update(self):
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def draw(self, surf, offset=(0, 0)):
        for p in self.particles:
            p.draw(surf, offset)


PARTICLES = ParticleSystem()

# --------- Camera (for screen shake) ---------
class Camera:
    def __init__(self):
        self.offset_x = 0
        self.offset_y = 0
        self.shake_timer = 0
        self.shake_mag = 0

    def shake(self, duration, magnitude):
        self.shake_timer = duration
        self.shake_mag = magnitude

    def update(self):
        if self.shake_timer > 0:
            self.shake_timer -= 1
            self.offset_x = random.uniform(-1, 1) * self.shake_mag
            self.offset_y = random.uniform(-1, 1) * self.shake_mag
        else:
            self.offset_x = 0
            self.offset_y = 0


CAMERA = Camera()

# --------- Background (stars parallax) ---------
class Star:
    def __init__(self):
        self.x = random.uniform(0, SCREEN_WIDTH)
        self.y = random.uniform(0, SCREEN_HEIGHT)
        self.z = random.uniform(0.3, 1.0)

    def update(self, speed):
        self.y += speed * self.z
        if self.y > SCREEN_HEIGHT:
            self.y = 0
            self.x = random.uniform(0, SCREEN_WIDTH)

    def draw(self, surf):
        r = int(1 + (1 - self.z) * 2)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), r)


STARS = [Star() for _ in range(120)]

# --------- Entities ---------
class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.w = 38
        self.h = 38
        self.speed = 5.2
        self.color = GREEN
        self.hp = 5
        self.max_hp = 5
        self.fire_rate = 10  # frames between shots
        self.fire_timer = 0
        self.bullets = []
        self.bomb_cooldown = 0
        self.score = 0
        self.lives = 3
        self.weapon_level = 1

    def handle_input(self, keys, mouse_pos):
        dx = 0
        dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1

        # normalize
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.x += dx * self.speed
        self.y += dy * self.speed

        self.x = clamp(self.x, 0, SCREEN_WIDTH - self.w)
        self.y = clamp(self.y, 0, SCREEN_HEIGHT - self.h)

    def update(self):
        if self.fire_timer > 0:
            self.fire_timer -= 1
        if self.bomb_cooldown > 0:
            self.bomb_cooldown -= 1

        # Update bullets
        for b in self.bullets[:]:
            b.update()
            if b.is_off():
                self.bullets.remove(b)

    def draw(self, surf, offset=(0, 0)):
        ox, oy = offset
        px = int(self.x - ox)
        py = int(self.y - oy)
        # Draw player as triangle pointing to mouse
        mx, my = pygame.mouse.get_pos()
        mx += CAMERA.offset_x * -1
        my += CAMERA.offset_y * -1
        angle = math.atan2(my - py, mx - px)
        # body
        points = [
            (px + math.cos(angle) * 20, py + math.sin(angle) * 20),
            (px + math.cos(angle + 2.3) * 18, py + math.sin(angle + 2.3) * 18),
            (px + math.cos(angle - 2.3) * 18, py + math.sin(angle - 2.3) * 18),
        ]
        pygame.draw.polygon(surf, self.color, points)
        # HP bar
        hp_w = 60
        hx = px - hp_w // 2 + self.w // 2
        hy = py + 30
        pygame.draw.rect(surf, DARK_GRAY, (hx, hy, hp_w, 8))
        pygame.draw.rect(surf, RED, (hx, hy, int(hp_w * (self.hp / self.max_hp)), 8))

    def shoot(self, target_x, target_y):
        if self.fire_timer > 0:
            return None
        # base bullet
        bx = self.x + self.w / 2
        by = self.y + self.h / 2
        dx = target_x - bx
        dy = target_y - by
        ang = math.atan2(dy, dx)
        # weapon levels alter spread and count
        if self.weapon_level == 1:
            bullets = [Bullet(bx, by, ang, speed=10, dmg=1)]
            self.fire_timer = self.fire_rate
        elif self.weapon_level == 2:
            bullets = [Bullet(bx, by, ang + math.radians(-6), speed=11, dmg=1),
                       Bullet(bx, by, ang, speed=11, dmg=1),
                       Bullet(bx, by, ang + math.radians(6), speed=11, dmg=1)]
            self.fire_timer = max(6, self.fire_rate - 2)
        else:
            bullets = [Bullet(bx, by, ang + math.radians(random.uniform(-10, 10)), speed=12, dmg=1) for _ in range(5)]
            self.fire_timer = max(4, self.fire_rate - 4)

        self.bullets.extend(bullets)
        if ASSETS.sounds.get('shoot'):
            ASSETS.sounds['shoot'].play()

    def drop_bomb(self):
        if self.bomb_cooldown <= 0:
            self.bomb_cooldown = FPS * 6
            return Bomb(self.x + self.w // 2, self.y + self.h // 2)
        return None


class Bullet:
    def __init__(self, x, y, angle, speed=10, dmg=1):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.radius = 4
        self.dmg = dmg

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def draw(self, surf, offset=(0, 0)):
        ox, oy = offset
        pygame.draw.circle(surf, YELLOW, (int(self.x - ox), int(self.y - oy)), self.radius)

    def get_rect(self):
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

    def is_off(self):
        return self.x < -50 or self.x > SCREEN_WIDTH + 50 or self.y < -50 or self.y > SCREEN_HEIGHT + 50


class Bomb:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.timer = FPS * 2  # 2 seconds till explode
        self.exploded = False
        self.explosion_radius = 0
        self.max_radius = 140

    def update(self):
        if not self.exploded:
            self.timer -= 1
            if self.timer <= 0:
                self.exploded = True
                PARTICLES.emit_explosion(self.x, self.y, count=30, color=ORANGE)
                CAMERA.shake(18, 8)
                if ASSETS.sounds.get('explode'):
                    ASSETS.sounds['explode'].play()
        else:
            if self.explosion_radius < self.max_radius:
                self.explosion_radius += 8

    def draw(self, surf, offset=(0, 0)):
        ox, oy = offset
        if not self.exploded:
            # blinking
            if (self.timer // 10) % 2 == 0:
                pygame.draw.circle(surf, RED, (int(self.x - ox), int(self.y - oy)), 10)
        else:
            pygame.draw.circle(surf, YELLOW, (int(self.x - ox), int(self.y - oy)), int(self.explosion_radius), 2)

    def get_explosion_rect(self):
        if self.exploded:
            return pygame.Rect(int(self.x - self.explosion_radius), int(self.y - self.explosion_radius),
                               int(self.explosion_radius * 2), int(self.explosion_radius * 2))
        return None

    def finished(self):
        return self.exploded and self.explosion_radius >= self.max_radius


class Enemy:
    def __init__(self, x, y, w=36, h=36, hp=2, speed=2):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.hp = hp
        self.max_hp = hp
        self.speed = speed

    def update(self):
        self.y += self.speed

    def draw(self, surf, offset=(0, 0)):
        ox, oy = offset
        pygame.draw.rect(surf, RED, (int(self.x - ox), int(self.y - oy), self.w, self.h))

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)


class Boss:
    def __init__(self, level=1):
        self.level = level
        self.w = 180
        self.h = 110
        self.x = SCREEN_WIDTH // 2 - self.w // 2
        self.y = -self.h - 20
        self.target_y = 60
        self.hp = 150 + (level - 1) * 60
        self.max_hp = self.hp
        self.phase = 0
        self.entering = True
        self.timer = 0
        self.missiles = []
        self.alive = True

    def update(self, player_x, player_y):
        if self.entering:
            self.y += 2.2
            if self.y >= self.target_y:
                self.entering = False
                self.timer = 0
        else:
            # phase selection
            self.timer += 1
            # phases depend on hp
            hp_pct = self.hp / self.max_hp
            if hp_pct > 0.66:
                # phase 0: slow targeted missiles
                self.phase = 0
            elif hp_pct > 0.33:
                # phase 1: spread shots
                self.phase = 1
            else:
                # phase 2: aggressive rapid volleys
                self.phase = 2

            # movement
            self.x += math.sin(pygame.time.get_ticks() * 0.001 + self.level) * 0.8
            self.x = clamp(self.x, 0, SCREEN_WIDTH - self.w)

            # shooting patterns
            if self.phase == 0 and self.timer % 80 == 0:
                # single big missile
                self.missiles.append(Missile(self.x + self.w // 2, self.y + self.h, player_x, player_y, speed=4))
            elif self.phase == 1 and self.timer % 50 == 0:
                # spread
                for a in (-25, -10, 0, 10, 25):
                    ang = math.radians(a)
                    tx = player_x + math.sin(ang) * 200
                    ty = player_y + math.cos(ang) * 200
                    self.missiles.append(Missile(self.x + self.w // 2, self.y + self.h, tx, ty, speed=5))
            elif self.phase == 2 and self.timer % 12 == 0:
                # rapid small missiles
                angle = random.uniform(-0.4, 0.4)
                tx = player_x + math.sin(angle) * 120
                ty = player_y + math.cos(angle) * 120
                self.missiles.append(Missile(self.x + random.randint(20, self.w - 20), self.y + self.h, tx, ty, speed=6))

        for m in self.missiles[:]:
            m.update()
            if m.is_off():
                self.missiles.remove(m)

    def draw(self, surf, offset=(0, 0)):
        ox, oy = offset
        pygame.draw.rect(surf, PURPLE, (int(self.x - ox), int(self.y - oy), self.w, self.h))
        # windows
        pygame.draw.circle(surf, YELLOW, (int(self.x + 40 - ox), int(self.y + 30 - oy)), 12)
        pygame.draw.circle(surf, YELLOW, (int(self.x + self.w - 40 - ox), int(self.y + 30 - oy)), 12)
        # hp bar
        bar_w = SCREEN_WIDTH - 120
        bx = 60
        by = 18
        pygame.draw.rect(surf, DARK_GRAY, (bx, by, bar_w, 14))
        pygame.draw.rect(surf, RED, (bx, by, int(bar_w * (self.hp / self.max_hp)), 14))
        font = pygame.font.Font(None, 28)
        text = font.render(f"BOSS LV.{self.level}", True, WHITE)
        surf.blit(text, (bx + 6, by - 2))

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def take_damage(self, dmg):
        self.hp -= dmg
        if ASSETS.sounds.get('boss_hit'):
            ASSETS.sounds['boss_hit'].play()
        PARTICLES.emit_explosion(random.randint(int(self.x), int(self.x + self.w)), random.randint(int(self.y), int(self.y + self.h)), count=6, color=PURPLE)
        CAMERA.shake(6, 4)
        if self.hp <= 0:
            self.alive = False
            PARTICLES.emit_explosion(self.x + self.w // 2, self.y + self.h // 2, count=60, color=YELLOW)
            if ASSETS.sounds.get('explode'):
                ASSETS.sounds['explode'].play()
            return True
        return False


class Missile:
    def __init__(self, sx, sy, tx, ty, speed=4):
        self.x = sx
        self.y = sy
        self.speed = speed
        dx = tx - sx
        dy = ty - sy
        dist = math.hypot(dx, dy)
        if dist == 0:
            dist = 1
        self.vx = dx / dist * speed
        self.vy = dy / dist * speed
        self.trail = deque(maxlen=10)

    def update(self):
        self.trail.appendleft((self.x, self.y))
        self.x += self.vx
        self.y += self.vy

    def draw(self, surf, offset=(0, 0)):
        ox, oy = offset
        for i, (tx, ty) in enumerate(self.trail):
            a = 255 * (1 - i / max(1, len(self.trail)))
            r = max(1, 4 - i // 3)
            pygame.draw.circle(surf, ORANGE, (int(tx - ox), int(ty - oy)), r)
        pygame.draw.rect(surf, DARK_GRAY, (int(self.x - ox) - 4, int(self.y - oy) - 8, 8, 16))

    def get_rect(self):
        return pygame.Rect(int(self.x) - 6, int(self.y) - 8, 12, 16)

    def is_off(self):
        return self.x < -50 or self.x > SCREEN_WIDTH + 50 or self.y < -50 or self.y > SCREEN_HEIGHT + 50


# --------- Game Class ---------
class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Dodge & Shoot - Enhanced")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 30)
        self.big_font = pygame.font.Font(None, 72)

        # game objects
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 140)
        self.enemies = []
        self.bullets = self.player.bullets  # alias
        self.bombs = []
        self.spawn_timer = 0
        self.enemy_spawn_rate = 45
        self.particles = PARTICLES
        self.camera = CAMERA
        self.stars = STARS

        # boss
        self.boss = None
        self.boss_level = 1
        self.boss_fight = False
        self.boss_defeat_timer = 0

        # powerups
        self.powerups = []

        # UI
        self.running = True
        self.game_over = False
        self.victory = False

    def spawn_enemy(self):
        x = random.randint(20, SCREEN_WIDTH - 60)
        y = -40
        hp = random.choice([1, 2, 3])
        speed = random.uniform(1.2, 3.5)
        self.enemies.append(Enemy(x, y, hp=hp, speed=speed))

    def spawn_powerup(self, x, y):
        choices = ["score", "life", "rapid", "weapon"]
        t = random.choices(choices, weights=[0.6, 0.15, 0.15, 0.1])[0]
        self.powerups.append({'x': x, 'y': y, 'type': t, 'timer': FPS * 8})

    def update(self):
        if not self.running:
            return

        self.camera.update()
        for s in self.stars:
            s.update(1.6 if self.boss_fight else 0.8)

        if self.game_over:
            return

        mx, my = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys, (mx, my))
        self.player.update()

        # spawn regular enemies if not in boss fight
        if not self.boss_fight:
            self.spawn_timer += 1
            spawn_rate = max(18, self.enemy_spawn_rate - int(self.player.score / 200))
            if self.spawn_timer >= spawn_rate:
                self.spawn_enemy()
                self.spawn_timer = 0

        # update enemies
        for e in self.enemies[:]:
            e.update()
            if e.y > SCREEN_HEIGHT + 50:
                self.enemies.remove(e)
                self.player.score += 2

        # update bullets
        for b in list(self.bullets):
            b.update()

        # update bombs
        for bomb in self.bombs[:]:
            bomb.update()
            if bomb.finished():
                self.bombs.remove(bomb)

        # collisions: bullets -> enemies
        for b in list(self.bullets):
            br = b.get_rect()
            # enemies
            for e in self.enemies[:]:
                if br.colliderect(e.get_rect()):
                    try:
                        self.bullets.remove(b)
                    except ValueError:
                        pass
                    e.hp -= b.dmg
                    PARTICLES.emit_explosion(b.x, b.y, count=6, color=YELLOW)
                    if e.hp <= 0:
                        try:
                            self.enemies.remove(e)
                        except ValueError:
                            pass
                        self.player.score += 12
                        if ASSETS.sounds.get('hit'):
                            ASSETS.sounds['hit'].play()
                        if random.random() < 0.25:
                            self.spawn_powerup(e.x + e.w // 2, e.y + e.h // 2)
                    break

            # boss
            if self.boss and self.boss.alive and br.colliderect(self.boss.get_rect()):
                try:
                    self.bullets.remove(b)
                except ValueError:
                    pass
                killed = self.boss.take_damage(b.dmg)
                if killed:
                    self.boss_defeated()
                break

        # explosions collide
        for bomb in self.bombs[:]:
            if bomb.exploded:
                rect = bomb.get_explosion_rect()
                if rect:
                    # enemies
                    for e in self.enemies[:]:
                        if rect.colliderect(e.get_rect()):
                            try:
                                self.enemies.remove(e)
                            except ValueError:
                                pass
                            self.player.score += 8
                    # missiles
                    if self.boss:
                        if rect.colliderect(self.boss.get_rect()):
                            killed = self.boss.take_damage(8)
                            if killed:
                                self.boss_defeated()
                    # player
                    if rect.colliderect(pygame.Rect(self.player.x, self.player.y, self.player.w, self.player.h)):
                        self.player.hp -= 1
                        self.camera.shake(12, 6)
                        if self.player.hp <= 0:
                            self.player.lives -= 1
                            if self.player.lives <= 0:
                                self.game_over = True
                            else:
                                self.player.hp = self.player.max_hp

        # boss missiles -> player
        if self.boss:
            for m in list(self.boss.missiles):
                if m.get_rect().colliderect(pygame.Rect(self.player.x, self.player.y, self.player.w, self.player.h)):
                    try:
                        self.boss.missiles.remove(m)
                    except ValueError:
                        pass
                    self.player.hp -= 1
                    self.camera.shake(10, 5)
                    PARTICLES.emit_explosion(self.player.x + self.player.w // 2, self.player.y + self.player.h // 2, count=12, color=RED)
                    if ASSETS.sounds.get('hit'):
                        ASSETS.sounds['hit'].play()
                    if self.player.hp <= 0:
                        self.player.lives -= 1
                        if self.player.lives <= 0:
                            self.game_over = True
                        else:
                            self.player.hp = self.player.max_hp

        # enemies -> player
        for e in self.enemies[:]:
            if pygame.Rect(self.player.x, self.player.y, self.player.w, self.player.h).colliderect(e.get_rect()):
                try:
                    self.enemies.remove(e)
                except ValueError:
                    pass
                self.player.hp -= 1
                self.camera.shake(14, 6)
                if ASSETS.sounds.get('hit'):
                    ASSETS.sounds['hit'].play()
                if self.player.hp <= 0:
                    self.player.lives -= 1
                    if self.player.lives <= 0:
                        self.game_over = True
                    else:
                        self.player.hp = self.player.max_hp

        # player pick powerups
        for p in self.powerups[:]:
            pr = pygame.Rect(int(p['x']), int(p['y']), 18, 18)
            if pr.colliderect(pygame.Rect(self.player.x, self.player.y, self.player.w, self.player.h)):
                t = p['type']
                if t == 'score':
                    self.player.score += 50
                elif t == 'life':
                    self.player.lives += 1
                elif t == 'rapid':
                    self.player.weapon_level = min(3, self.player.weapon_level + 1)
                elif t == 'weapon':
                    self.player.weapon_level = min(3, self.player.weapon_level + 1)
                try:
                    self.powerups.remove(p)
                except ValueError:
                    pass
                if ASSETS.sounds.get('powerup'):
                    ASSETS.sounds['powerup'].play()

        # update particles
        self.particles.update()

        # spawn boss if needed
        if not self.boss_fight and self.player.score >= 2000 * self.boss_level:
            self.start_boss_fight()

        if self.boss_fight and self.boss:
            self.boss.update(self.player.x + self.player.w // 2, self.player.y + self.player.h // 2)

    def boss_defeated(self):
        self.player.score += 800 * self.boss_level
        self.boss_fight = False
        self.boss = None
        self.boss_level += 1
        self.boss_defeat_timer = FPS * 2
        # spawn several powerups
        for _ in range(4):
            self.spawn_powerup(random.randint(80, SCREEN_WIDTH - 80), random.randint(120, SCREEN_HEIGHT - 120))

    def start_boss_fight(self):
        self.boss_fight = True
        self.boss = Boss(level=self.boss_level)
        # clear many things
        self.enemies.clear()
        self.bullets.clear()
        self.bombs.clear()
        self.powerups.clear()

    def draw(self):
        offs = (int(self.camera.offset_x), int(self.camera.offset_y))
        # background
        self.screen.fill((10, 12, 20))
        for s in self.stars:
            s.draw(self.screen)

        # world surface for camera offset
        world = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), flags=pygame.SRCALPHA)
        world.fill((0, 0, 0, 0))

        # draw enemies
        for e in self.enemies:
            e.draw(world, offs)

        # draw bombs
        for b in self.bombs:
            b.draw(world, offs)

        # draw boss missiles
        if self.boss:
            for m in self.boss.missiles:
                m.draw(world, offs)

        # draw player bullets
        for b in self.bullets:
            b.draw(world, offs)

        # draw player
        self.player.draw(world, offs)

        # draw boss
        if self.boss:
            self.boss.draw(world, offs)

        # draw particles
        self.particles.draw(world, offs)

        # draw powerups
        for p in self.powerups:
            pygame.draw.rect(world, YELLOW if p['type'] == 'score' else (PURPLE if p['type'] == 'life' else GREEN), (int(p['x']), int(p['y']), 18, 18))

        # blit world with camera offset
        self.screen.blit(world, (offs[0], offs[1]))

        # UI overlays
        score_text = self.font.render(f"Score: {self.player.score}", True, WHITE)
        lives_text = self.font.render(f"Lives: {self.player.lives}", True, WHITE)
        weapon_text = self.font.render(f"Weapon LV: {self.player.weapon_level}", True, WHITE)
        self.screen.blit(score_text, (16, 16))
        self.screen.blit(lives_text, (16, 48))
        self.screen.blit(weapon_text, (16, 80))

        if self.game_over:
            go = self.big_font.render("GAME OVER", True, RED)
            r = go.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
            self.screen.blit(go, r)
            t = self.font.render("Press R to restart or ESC to quit", True, WHITE)
            self.screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

        if self.boss_fight and self.boss and not self.boss.alive:
            win = self.big_font.render("BOSS DOWN!", True, YELLOW)
            self.screen.blit(win, (SCREEN_WIDTH // 2 - win.get_width() // 2, SCREEN_HEIGHT // 2 - 80))

        pygame.display.flip()

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
                pygame.quit()
                sys.exit()
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.running = False
                    pygame.quit()
                    sys.exit()
                if ev.key == pygame.K_r and self.game_over:
                    self.__init__()
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1 and not self.game_over:
                    mx, my = pygame.mouse.get_pos()
                    self.player.shoot(mx - self.camera.offset_x, my - self.camera.offset_y)
                if ev.button == 3 and not self.game_over:
                    b = self.player.drop_bomb()
                    if b:
                        self.bombs.append(b)

    def run(self):
        while self.running:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()


if __name__ == '__main__':
    Game().run()
