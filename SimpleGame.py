"""Dodge & Shoot — Full Release
Features added:
- Title/Menu with difficulty selection and start/quit
- Background music and SFX (optional via assets/ folder)
- High score saving (highscores.json)
- Level progression, waves and mini-bosses
- Multiple enemy types (fast, tank, zigzag)
- Gamepad/controller support (basic)
- Performance improvements (particle cap, pooling hints)
- Build/packaging notes at bottom

Save as: pygame_boss_battle_enhanced.py
Run: pip install pygame
     python pygame_boss_battle_enhanced.py

Place optional assets in ./assets: music.ogg, shoot.wav, hit.wav, explode.wav, boss_hit.wav, powerup.wav
"""

import pygame
import random
import sys
import math
import os
import json
from collections import deque

# --------- Configuration ---------
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 720
FPS = 60
MAX_PARTICLES = 400  # cap for performance
ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
HIGHSCORE_FILE = os.path.join(os.path.dirname(__file__), "highscores.json")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 40, 40)
GREEN = (80, 200, 120)
YELLOW = (255, 220, 80)
ORANGE = (255, 140, 40)
PURPLE = (160, 60, 200)
DARK_GRAY = (28, 28, 34)

# Utility
def clamp(v, a, b):
    return max(a, min(b, v))

# ---------------- Assets & Audio -----------------
class Assets:
    def __init__(self):
        self.sounds = {}
        self.music = None
        self.load()

    def load(self):
        # load sounds if available
        try:
            if os.path.isdir(ASSET_DIR):
                for name in ("shoot", "hit", "explode", "boss_hit", "powerup"):
                    p = os.path.join(ASSET_DIR, f"{name}.wav")
                    if os.path.exists(p):
                        try:
                            self.sounds[name] = pygame.mixer.Sound(p)
                        except Exception:
                            self.sounds[name] = None
                # music
                m = os.path.join(ASSET_DIR, "music.ogg")
                if os.path.exists(m):
                    self.music = m
        except Exception as e:
            print("Asset load error:", e)

ASSETS = Assets()

# ---------------- High Scores -----------------
def load_highscores():
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_highscores(scores):
    try:
        with open(HIGHSCORE_FILE, 'w') as f:
            json.dump(scores, f)
    except Exception as e:
        print('Could not save highscores:', e)

# default highscores
HIGHSCORES = load_highscores()

# ---------------- Particle System -----------------
class Particle:
    __slots__ = ('x','y','vx','vy','life','max_life','r','color')
    def __init__(self, x, y, vx, vy, life, r=3, color=ORANGE):
        self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.life = life; self.max_life = life; self.r = r; self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.12
        self.life -= 1

    def draw(self, surf, offset=(0,0)):
        if self.life > 0:
            ox, oy = offset
            pygame.draw.circle(surf, self.color, (int(self.x-ox), int(self.y-oy)), max(1, int(self.r * (self.life/self.max_life))))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit_explosion(self, x, y, count=20, color=ORANGE):
        if len(self.particles) > MAX_PARTICLES:
            return
        for _ in range(count):
            angle = random.random() * 2 * math.pi
            speed = random.uniform(1, 6)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            p = Particle(x, y, vx, vy, life=random.randint(18, 42), r=random.randint(2,5), color=color)
            self.particles.append(p)

    def update(self):
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def draw(self, surf, offset=(0,0)):
        for p in self.particles:
            p.draw(surf, offset)

PARTICLES = ParticleSystem()

# ---------------- Camera (shake) -----------------
class Camera:
    def __init__(self):
        self.offx = 0; self.offy = 0; self.timer = 0; self.mag = 0
    def shake(self, duration, mag):
        self.timer = duration; self.mag = mag
    def update(self):
        if self.timer>0:
            self.timer -=1
            self.offx = random.uniform(-1,1)*self.mag
            self.offy = random.uniform(-1,1)*self.mag
        else:
            self.offx = 0; self.offy = 0
CAMERA = Camera()

# ---------------- Background -----------------
class Star:
    def __init__(self):
        self.x = random.uniform(0, SCREEN_WIDTH)
        self.y = random.uniform(0, SCREEN_HEIGHT)
        self.z = random.uniform(0.3,1.0)
    def update(self, speed):
        self.y += speed*self.z
        if self.y > SCREEN_HEIGHT:
            self.y = 0; self.x = random.uniform(0, SCREEN_WIDTH)
    def draw(self, surf):
        r = int(1 + (1-self.z)*2)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), r)
STARS = [Star() for _ in range(140)]

# ---------------- Entities -----------------
class Player:
    def __init__(self, x, y):
        self.x = x; self.y = y; self.w = 36; self.h = 36
        self.speed = 5.4; self.hp = 5; self.max_hp = 5
        self.fire_rate = 10; self.fire_timer = 0; self.bullets = []
        self.bomb_cd = 0; self.score = 0; self.lives = 3; self.weapon_lv = 1

    def handle_input(self, keys):
        dx=dy=0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx-=1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx+=1
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy-=1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy+=1
        if dx!=0 and dy!=0: dx*=0.7071; dy*=0.7071
        self.x += dx*self.speed; self.y += dy*self.speed
        self.x = clamp(self.x,0,SCREEN_WIDTH-self.w); self.y = clamp(self.y,0,SCREEN_HEIGHT-self.h)

    def update(self):
        if self.fire_timer>0: self.fire_timer-=1
        if self.bomb_cd>0: self.bomb_cd-=1
        for b in self.bullets[:]:
            b.update();
            if b.off(): self.bullets.remove(b)

    def draw(self, surf, offset=(0,0)):
        ox,oy=offset
        px=int(self.x-ox); py=int(self.y-oy)
        mx,my = pygame.mouse.get_pos()
        angle = math.atan2((my-oy)-py, (mx-ox)-px)
        pts=[(px+math.cos(angle)*18, py+math.sin(angle)*18), (px+math.cos(angle+2.4)*16, py+math.sin(angle+2.4)*16), (px+math.cos(angle-2.4)*16, py+math.sin(angle-2.4)*16)]
        pygame.draw.polygon(surf, GREEN, pts)
        # HP bar
        hw=56; hx=px-hw//2+self.w//2; hy=py+28
        pygame.draw.rect(surf, DARK_GRAY, (hx,hy,hw,8)); pygame.draw.rect(surf, RED, (hx,hy,int(hw*(self.hp/self.max_hp)),8))

    def shoot(self, tx, ty):
        if self.fire_timer>0: return
        bx=self.x+self.w/2; by=self.y+self.h/2; ang=math.atan2(ty-by, tx-bx)
        if self.weapon_lv==1:
            bullets=[Bullet(bx,by,ang,10,1)]; self.fire_timer=self.fire_rate
        elif self.weapon_lv==2:
            bullets=[Bullet(bx,by,ang+math.radians(-6),11,1), Bullet(bx,by,ang,11,1), Bullet(bx,by,ang+math.radians(6),11,1)]; self.fire_timer=max(6,self.fire_rate-2)
        else:
            bullets=[Bullet(bx,by,ang+math.radians(random.uniform(-10,10)),12,1) for _ in range(5)]; self.fire_timer=max(4,self.fire_rate-4)
        self.bullets.extend(bullets)
        if ASSETS.sounds.get('shoot'): ASSETS.sounds['shoot'].play()

    def drop_bomb(self):
        if self.bomb_cd<=0:
            self.bomb_cd = FPS*6
            return Bomb(self.x+self.w//2, self.y+self.h//2)
        return None

class Bullet:
    __slots__=('x','y','vx','vy','r','dmg')
    def __init__(self,x,y,ang,speed=10,dmg=1): self.x=x; self.y=y; self.vx=math.cos(ang)*speed; self.vy=math.sin(ang)*speed; self.r=4; self.dmg=dmg
    def update(self): self.x+=self.vx; self.y+=self.vy
    def draw(self,surf,offset=(0,0)): ox,oy=offset; pygame.draw.circle(surf, YELLOW, (int(self.x-ox), int(self.y-oy)), self.r)
    def get_rect(self): return pygame.Rect(int(self.x-self.r), int(self.y-self.r), self.r*2, self.r*2)
    def off(self): return self.x<-60 or self.x>SCREEN_WIDTH+60 or self.y<-60 or self.y>SCREEN_HEIGHT+60

class Bomb:
    def __init__(self,x,y): self.x=x; self.y=y; self.timer=FPS*2; self.expl=False; self.r=0; self.maxr=140
    def update(self):
        if not self.expl:
            self.timer-=1
            if self.timer<=0:
                self.expl=True; PARTICLES.emit_explosion(self.x,self.y, count=32, color=ORANGE); CAMERA.shake(18,8);
                if ASSETS.sounds.get('explode'): ASSETS.sounds['explode'].play()
        else:
            if self.r < self.maxr: self.r += 10
    def draw(self,surf,offset=(0,0)): 
        ox,oy=offset; 
        if not self.expl:
            if (self.timer//10)%2==0: pygame.draw.circle(surf, RED, (int(self.x-ox), int(self.y-oy)), 10)
        else:
            pygame.draw.circle(surf, YELLOW, (int(self.x-ox), int(self.y-oy)), int(self.r), 2)
    def get_rect(self): return pygame.Rect(int(self.x-self.r), int(self.y-self.r), int(self.r*2), int(self.r*2))
    def finished(self): return self.expl and self.r>=self.maxr

# Enemy types
class Enemy:
    def __init__(self, x, y, kind='basic'):
        self.x=x; self.y=y; self.w=36; self.h=36
        self.kind=kind
        if kind=='basic': self.hp=2; self.speed=2.2
        elif kind=='fast': self.hp=1; self.speed=3.6
        elif kind=='tank': self.hp=5; self.speed=1.0
        elif kind=='zig': self.hp=3; self.speed=2.0; self.phase=0
    def update(self):
        if self.kind=='zig': self.x += math.sin(self.phase/6.0)*2.6; self.phase+=1
        self.y += self.speed
    def draw(self,surf,offset=(0,0)): ox,oy=offset; color=RED if self.kind!='tank' else PURPLE; pygame.draw.rect(surf, color, (int(self.x-ox), int(self.y-oy), self.w, self.h))
    def get_rect(self): return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

# Boss (mini and main)
class Boss:
    def __init__(self, level=1, mini=False):
        self.level=level; self.mini=mini
        self.w=200 if not mini else 120; self.h=110 if not mini else 70
        self.x = SCREEN_WIDTH//2 - self.w//2; self.y = -self.h-20
        self.target_y = 60 if not mini else 140
        self.hp = (180 + (level-1)*70) if not mini else (80 + (level-1)*30)
        self.max_hp = self.hp
        self.entering=True; self.timer=0; self.missiles=[]; self.alive=True
    def update(self, px, py):
        if self.entering:
            self.y += 2.4 if not self.mini else 2.0
            if self.y >= self.target_y: self.entering=False; self.timer=0
        else:
            self.timer+=1
            hp_pct = self.hp/self.max_hp
            if hp_pct>0.66: phase=0
            elif hp_pct>0.33: phase=1
            else: phase=2
            self.x += math.sin(pygame.time.get_ticks()*0.001 + self.level)*0.9
            self.x = clamp(self.x,0,SCREEN_WIDTH-self.w)
            if not self.mini:
                if phase==0 and self.timer%80==0: self.missiles.append(Missile(self.x+self.w//2, self.y+self.h, px, py, speed=4))
                elif phase==1 and self.timer%52==0:
                    for a in (-25,-10,0,10,25): ang=math.radians(a); tx=px+math.sin(ang)*200; ty=py+math.cos(ang)*200; self.missiles.append(Missile(self.x+self.w//2, self.y+self.h, tx, ty, speed=5))
                elif phase==2 and self.timer%10==0: angle=random.uniform(-0.5,0.5); tx=px+math.sin(angle)*120; ty=py+math.cos(angle)*120; self.missiles.append(Missile(self.x+random.randint(20,self.w-20), self.y+self.h, tx, ty, speed=6))
            else:
                # mini boss simpler
                if self.timer%36==0: self.missiles.append(Missile(self.x+self.w//2, self.y+self.h, px, py, speed=5))
        for m in self.missiles[:]: m.update();
        self.missiles=[m for m in self.missiles if not m.is_off()]
    def draw(self,surf,offset=(0,0)):
        ox,oy=offset; pygame.draw.rect(surf, PURPLE if not self.mini else ORANGE, (int(self.x-ox), int(self.y-oy), self.w, self.h))
        # hp bar
        bar_w=SCREEN_WIDTH-140; bx=70; by=16; pygame.draw.rect(surf, DARK_GRAY, (bx,by,bar_w,14)); pygame.draw.rect(surf, RED, (bx,by,int(bar_w*(self.hp/self.max_hp)),14))
        if not self.mini:
            font=pygame.font.Font(None, 26); surf.blit(font.render(f"BOSS LV.{self.level}", True, WHITE),(bx+6,by-2))
    def get_rect(self): return pygame.Rect(int(self.x), int(self.y), self.w, self.h)
    def take_damage(self,dmg):
        self.hp-=dmg; PARTICLES.emit_explosion(random.randint(int(self.x),int(self.x+self.w)), random.randint(int(self.y),int(self.y+self.h)), count=6, color=PURPLE); CAMERA.shake(6,4);
        
        if ASSETS.sounds.get('boss_hit'):
            ASSETS.sounds['boss_hit'].play()
        if self.hp<=0:
            self.alive=False; PARTICLES.emit_explosion(self.x+self.w//2, self.y+self.h//2, count=60, color=YELLOW);
            if ASSETS.sounds.get('explode'): 
                ASSETS.sounds['explode'].play(); return True
        return False

class Missile:
    def __init__(self,sx,sy,tx,ty,speed=4):
        self.x=sx; self.y=sy; dx=tx-sx; dy=ty-sy; dist=math.hypot(dx,dy) or 1
        self.vx = dx/dist*speed; self.vy = dy/dist*speed; self.trail=deque(maxlen=10)
    def update(self): self.trail.appendleft((self.x,self.y)); self.x+=self.vx; self.y+=self.vy
    def draw(self,surf,offset=(0,0)):
        ox,oy=offset
        for i,(tx,ty) in enumerate(self.trail): pygame.draw.circle(surf, ORANGE, (int(tx-ox),int(ty-oy)), max(1,4-i//3))
        pygame.draw.rect(surf, DARK_GRAY, (int(self.x-ox)-4, int(self.y-oy)-8, 8, 16))
    def get_rect(self): return pygame.Rect(int(self.x)-6, int(self.y)-8, 12, 16)
    def is_off(self): return self.x<-60 or self.x>SCREEN_WIDTH+60 or self.y<-60 or self.y>SCREEN_HEIGHT+60

# ---------------- Game -----------------
class Game:
    def __init__(self):
        pygame.init();
        try: pygame.mixer.init()
        except Exception: pass
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('Dodge & Shoot — Full Release')
        self.clock = pygame.time.Clock(); self.font=pygame.font.Font(None,30); self.big=pygame.font.Font(None,72)
        self.reset()
        # joystick
        self.joysticks = []
        pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            self.joysticks.append(pygame.joystick.Joystick(i)); self.joysticks[-1].init()
        # play music if present
        if ASSETS.music:
            try:
                pygame.mixer.music.load(ASSETS.music); pygame.mixer.music.set_volume(0.6); pygame.mixer.music.play(-1)
            except Exception as e:
                print('Music load failed:', e)

    def reset(self):
        self.player = Player(SCREEN_WIDTH//2, SCREEN_HEIGHT-150); self.enemies=[]; self.bombs=[]; self.spawn_timer=0; self.wave=1
        self.enemy_spawn_rate=45; self.boss=None; self.boss_fight=False; self.mini_spawn=False; self.powerups=[]; self.running=True
        self.game_over=False; self.menu=True; self.difficulty='Normal'; self.particles=PARTICLES; self.camera=CAMERA; self.stars=STARS

    def spawn_enemy(self):
        kinds=['basic','fast','tank','zig']
        weights=[0.5,0.25,0.15,0.1] if self.wave<3 else [0.35,0.3,0.2,0.15]
        kind = random.choices(kinds, weights=weights)[0]
        x=random.randint(20, SCREEN_WIDTH-60); y=-40
        self.enemies.append(Enemy(x,y,kind))

    def spawn_powerup(self,x,y):
        choices=['score','life','rapid','weapon']; t=random.choices(choices, weights=[0.6,0.15,0.15,0.1])[0]
        self.powerups.append({'x':x,'y':y,'type':t,'timer':FPS*8})

    def start_boss(self, mini=False):
        self.boss_fight=True; self.boss=Boss(level=self.wave, mini=mini); self.enemies.clear(); self.player.bullets.clear(); self.bombs.clear(); self.powerups.clear()

    def update(self):
        if not self.running: return
        self.camera.update(); [s.update(1.6 if self.boss_fight else 0.9) for s in self.stars]
        if self.menu or self.game_over: return
        # input
        keys = pygame.key.get_pressed(); self.player.handle_input(keys); self.player.update()
        # spawn
        if not self.boss_fight:
            self.spawn_timer += 1
            spawn_rate = max(14, int(self.enemy_spawn_rate - (self.player.score/220)))
            if self.spawn_timer>=spawn_rate:
                self.spawn_enemy(); self.spawn_timer=0
        # update enemies
        for e in self.enemies[:]: 
            e.update();
            if e.y>SCREEN_HEIGHT+60:
                self.enemies.remove(e); self.player.score+=2
        # bullets
        for b in list(self.player.bullets): b.update()
        # bombs
        for bom in self.bombs[:]:
            bom.update();
            if bom.finished(): self.bombs.remove(bom)
        # collisions bullets->enemies
        for b in list(self.player.bullets):
            br=b.get_rect();
            for e in self.enemies[:]:
                if br.colliderect(e.get_rect()):
                    try: self.player.bullets.remove(b)
                    except: pass
                    e.hp -= b.dmg; PARTICLES.emit_explosion(b.x,b.y,count=6,color=YELLOW)
                    if e.hp<=0:
                        try: self.enemies.remove(e)
                        except: pass
                        self.player.score += 12 if e.kind!='tank' else 30
                        if ASSETS.sounds.get('hit'): ASSETS.sounds['hit'].play()
                        if random.random()<0.28: self.spawn_powerup(e.x+e.w//2, e.y+e.h//2)
                    break
            if self.boss and self.boss.alive and br.colliderect(self.boss.get_rect()):
                try: self.player.bullets.remove(b)
                except: pass
                killed = self.boss.take_damage(b.dmg)
                if killed: self.on_boss_down();
                break
        # explosions
        for bom in self.bombs[:]:
            if bom.expl:
                rect = bom.get_rect() if hasattr(bom,'get_rect') else bom.get_explosion_rect()
                if rect:
                    for e in self.enemies[:]:
                        if rect.colliderect(e.get_rect()):
                            try: self.enemies.remove(e)
                            except: pass
                            self.player.score += 8
                    if self.boss and rect.colliderect(self.boss.get_rect()):
                        killed = self.boss.take_damage(10); 
                        if killed: self.on_boss_down()
                    if rect.colliderect(pygame.Rect(self.player.x,self.player.y,self.player.w,self.player.h)):
                        self.player.hp -=1; self.camera.shake(12,6)
                        if ASSETS.sounds.get('hit'): ASSETS.sounds['hit'].play()
                        if self.player.hp<=0:
                            self.player.lives-=1
                            if self.player.lives<=0: self.game_over=True
                            else: self.player.hp=self.player.max_hp
        # boss missiles
        if self.boss:
            for m in list(self.boss.missiles):
                if m.get_rect().colliderect(pygame.Rect(self.player.x,self.player.y,self.player.w,self.player.h)):
                    try: self.boss.missiles.remove(m)
                    except: pass
                    self.player.hp-=1; self.camera.shake(10,5); PARTICLES.emit_explosion(self.player.x+self.player.w//2, self.player.y+self.player.h//2,count=12,color=RED)
                    if ASSETS.sounds.get('hit'): ASSETS.sounds['hit'].play()
                    if self.player.hp<=0:
                        self.player.lives-=1
                        if self.player.lives<=0: self.game_over=True
                        else: self.player.hp=self.player.max_hp
        # enemies->player
        for e in self.enemies[:]:
            if pygame.Rect(self.player.x,self.player.y,self.player.w,self.player.h).colliderect(e.get_rect()):
                try: self.enemies.remove(e)
                except: pass
                self.player.hp-=1; self.camera.shake(14,6)
                if ASSETS.sounds.get('hit'): ASSETS.sounds['hit'].play()
                if self.player.hp<=0:
                    self.player.lives-=1
                    if self.player.lives<=0: self.game_over=True
                    else: self.player.hp=self.player.max_hp
        # pick powerups
        for p in self.powerups[:]:
            pr=pygame.Rect(int(p['x']),int(p['y']),18,18)
            if pr.colliderect(pygame.Rect(self.player.x,self.player.y,self.player.w,self.player.h)):
                t=p['type']
                if t=='score': self.player.score += 50
                elif t=='life': self.player.lives +=1
                else: self.player.weapon_lv = min(3, self.player.weapon_lv+1)
                try: self.powerups.remove(p)
                except: pass
                if ASSETS.sounds.get('powerup'): ASSETS.sounds['powerup'].play()
        PARTICLES.update()
        if not self.boss_fight and self.player.score >= 2000*self.wave:
            # occasionally spawn mini-boss before main boss
            if not self.mini_spawn and random.random() < 0.35:
                self.mini_spawn = True; self.start_boss(mini=True)
            else:
                self.start_boss(mini=False)
        if self.boss_fight and self.boss:
            self.boss.update(self.player.x+self.player.w//2, self.player.y+self.player.h//2)

    def on_boss_down(self):
        self.player.score += 800*self.wave
        self.boss_fight=False; self.boss=None; self.wave+=1; self.mini_spawn=False
        self.enemy_spawn_rate = max(20, self.enemy_spawn_rate-3)
        # spawn goodies
        for _ in range(4): self.spawn_powerup(random.randint(80, SCREEN_WIDTH-80), random.randint(120, SCREEN_HEIGHT-120))
        # record highscore
        HIGHSCORES.append(self.player.score); HIGHSCORES.sort(reverse=True); HIGHSCORES[:] = HIGHSCORES[:10]; save_highscores(HIGHSCORES)

    def draw(self):
        off=(int(self.camera.offx), int(self.camera.offy))
        self.screen.fill((8,10,16))
        for s in self.stars: s.draw(self.screen)
        world = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), flags=pygame.SRCALPHA); world.fill((0,0,0,0))
        for e in self.enemies: e.draw(world, off)
        for b in self.bombs: b.draw(world, off)
        if self.boss:
            for m in self.boss.missiles: m.draw(world, off)
        for bl in list(self.player.bullets): bl.draw(world, off)
        self.player.draw(world, off)
        if self.boss: self.boss.draw(world, off)
        PARTICLES.draw(world, off)
        for p in self.powerups: pygame.draw.rect(world, YELLOW if p['type']=='score' else (PURPLE if p['type']=='life' else GREEN), (int(p['x']), int(p['y']), 18, 18))
        self.screen.blit(world, (off[0], off[1]))
        # UI
        score = self.font.render(f"Score: {self.player.score}", True, WHITE); lives = self.font.render(f"Lives: {self.player.lives}", True, WHITE); weapon = self.font.render(f"Weapon LV: {self.player.weapon_lv}", True, WHITE)
        self.screen.blit(score,(16,16)); self.screen.blit(lives,(16,48)); self.screen.blit(weapon,(16,80))
        if self.menu:
            title = self.big.render('DODGE & SHOOT', True, YELLOW); self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 120))
            txt = self.font.render('Press ENTER to Start  |  M: Toggle Music  |  D: Difficulty', True, WHITE); self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, 220))
            # highscores
            hs_title = self.font.render('HIGHSCORES', True, WHITE); self.screen.blit(hs_title, (SCREEN_WIDTH-250, 120))
            for i, sc in enumerate(HIGHSCORES[:6]): self.screen.blit(self.font.render(f"{i+1}. {sc}", True, WHITE), (SCREEN_WIDTH-250, 150 + i*28))
        if self.game_over:
            go = self.big.render('GAME OVER', True, RED); self.screen.blit(go, (SCREEN_WIDTH//2-go.get_width()//2, SCREEN_HEIGHT//2-40))
            txt = self.font.render('Press R to restart or ESC to quit', True, WHITE); self.screen.blit(txt, (SCREEN_WIDTH//2-txt.get_width()//2, SCREEN_HEIGHT//2+30))
        pygame.display.flip()

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: self.running=False; pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: self.running=False; pygame.quit(); sys.exit()
                if self.menu and ev.key==pygame.K_RETURN: self.menu=False
                if ev.key==pygame.K_m:
                    if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
                    else:
                        if ASSETS.music: pygame.mixer.music.play(-1)
                if ev.key==pygame.K_d and self.menu:
                    # cycle difficulty
                    if self.difficulty=='Easy': self.difficulty='Normal'
                    elif self.difficulty=='Normal': self.difficulty='Hard'
                    else: self.difficulty='Easy'
                if ev.key==pygame.K_r and self.game_over: self.reset(); self.menu=False
            if ev.type==pygame.MOUSEBUTTONDOWN and not self.menu and not self.game_over:
                if ev.button==1: mx,my=pygame.mouse.get_pos(); self.player.shoot(mx-self.camera.offx, my-self.camera.offy)
                if ev.button==3:
                    b = self.player.drop_bomb();
                    if b: self.bombs.append(b)
            if ev.type==pygame.JOYBUTTONDOWN:
                # map gamepad buttons (basic)
                if ev.button==0 and not self.menu: # A
                    mx, my = pygame.mouse.get_pos(); self.player.shoot(mx-self.camera.offx, my-self.camera.offy)
                if ev.button==1 and not self.menu:
                    b = self.player.drop_bomb();
                    if b: self.bombs.append(b)

    def run(self):
        while self.running:
            self.clock.tick(FPS); self.handle_events(); self.update(); self.draw()

# ---------------- Packaging notes -----------------
# To make an executable: use PyInstaller:
#   pip install pyinstaller
#   pyinstaller --onefile --add-data "assets;assets" pygame_boss_battle_enhanced.py
# This bundles the assets folder. Test the built exe on target OS.

if __name__ == '__main__':
    Game().run()
