#!/usr/bin/env python3
"""
DOOM 4D - Python Remastered with OpenGL
Originally created by Denis Astahov (ADV-IT) in 2004
Visual Basic 6 + DirectX 7 -> Python + Pygame + PyOpenGL

Bachelor Degree Project - Score: 95/100
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

import math
import random
from pathlib import Path
from typing import List, Dict

# ============== CONSTANTS (from original VB6) ==============
COMPSTEP = 100
TREE_MAX = 40
FIRESMOKE = 40
PI = 3.14159265358979
POLE = 100  # Arena size from -100 to 100 (from original!)

SCREEN_W = 1024
SCREEN_H = 768
TITLE = "DOOM 4D - Remastered (c) 2004 Denis Astahov"


class TextureLoader:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.textures: Dict[str, int] = {}
        
    def load_texture(self, name: str, relative_path: str) -> bool:
        full_path = self.base_path / relative_path
        
        for ext in ['', '.bmp', '.BMP', '.jpg', '.JPG', '.jpeg', '.JPEG', '.png']:
            test_path = Path(str(full_path) + ext) if ext else full_path
            if test_path.exists():
                full_path = test_path
                break
        else:
            return False
            
        try:
            surface = pygame.image.load(str(full_path))
            surface = pygame.transform.flip(surface, False, True)
            data = pygame.image.tostring(surface, "RGBA", True)
            width, height = surface.get_size()
            
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            
            self.textures[name] = texture_id
            print(f"Loaded: {name} ({width}x{height})")
            return True
        except Exception as e:
            print(f"Error loading {relative_path}: {e}")
            return False
            
    def bind(self, name: str):
        if name in self.textures:
            glBindTexture(GL_TEXTURE_2D, self.textures[name])
        else:
            glBindTexture(GL_TEXTURE_2D, 0)


class SoundManager:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.music_sounds: Dict[int, pygame.mixer.Sound] = {}
        self.current_music = None
        
    def load_sound(self, name: str, relative_path: str) -> bool:
        full_path = self.base_path / relative_path
        for ext in ['', '.wav', '.WAV']:
            test_path = Path(str(full_path) + ext) if ext else full_path
            if test_path.exists():
                try:
                    self.sounds[name] = pygame.mixer.Sound(str(test_path))
                    print(f"Loaded sound: {name}")
                    return True
                except Exception as e:
                    print(f"Error sound {relative_path}: {e}")
        return False
        
    def load_music_list(self, music_dir: str):
        music_path = self.base_path / music_dir
        if music_path.exists():
            for f in sorted(music_path.glob("Music*.wav")):
                num = ''.join(filter(str.isdigit, f.stem))
                if num:
                    try:
                        sound = pygame.mixer.Sound(str(f))
                        self.music_sounds[int(num)] = sound
                        print(f"Loaded music track {num}")
                    except Exception as e:
                        print(f"Could not load music {f.name}: {e}")
                    
    def play_sound(self, name: str):
        if name in self.sounds:
            self.sounds[name].play()
            
    def play_music(self, num: int):
        if num in self.music_sounds:
            try:
                if self.current_music and self.current_music in self.music_sounds:
                    self.music_sounds[self.current_music].stop()
                self.music_sounds[num].play(-1)
                self.current_music = num
                print(f"Playing music track {num}")
            except Exception as e:
                print(f"Error playing music: {e}")


class Sprite3D:
    def __init__(self, x: float, z: float, height: float, width: float):
        self.x = x
        self.z = z
        self.height = height
        self.width = width


class Player:
    def __init__(self):
        self.x = 0.0
        self.y = 10.0
        self.z = -80.0  # Start back
        self.angle = 0.0
        
        self.step = 1.0
        self.rotate_speed = 0.03
        
        self.energy = 100
        self.max_energy = 100
        self.wins = 0
        
        self.fire_now = False
        self.last_shoot = False


class Computer:
    def __init__(self):
        self.x = 0.0
        self.y = 4.0
        self.z = 0.0
        
        self.dx = 0.0
        self.dz = 0.0
        self.step_count = COMPSTEP
        
        self.energy = 100
        self.max_energy = 100
        
        self.rotate_x = 0.0
        self.rotate_y = 0.0
        self.rotate_z = 0.0
        
    def spawn_target(self):
        new_x = random.randint(-85, 85)
        new_z = random.randint(-85, 85)
        self.dx = (new_x - self.x) / COMPSTEP
        self.dz = (new_z - self.z) / COMPSTEP
        self.step_count = 0
        
    def update(self):
        if self.step_count >= COMPSTEP:
            self.spawn_target()
            
        self.x += self.dx
        self.z += self.dz
        self.step_count += 1
        
        self.x = max(-90, min(90, self.x))
        self.z = max(-90, min(90, self.z))
        
        self.rotate_x = (self.rotate_x + 1) % 360
        self.rotate_y = (self.rotate_y + 5) % 360


class Doom4D:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), DOUBLEBUF | OPENGL)
        pygame.display.set_caption(TITLE)
        
        self.running = True
        self.game_type = 1
        self.in_menu = True
        self.game_over = False
        
        # Intro animation
        self.intro_stage = 0
        self.intro_timer = 0
        self.intro_zoom = 100
        self.intro_running = True
        
        self.player = Player()
        self.computer = Computer()
        
        self.trees1: List[Sprite3D] = []
        self.trees2: List[Sprite3D] = []
        self.smokes: List[Sprite3D] = []
        self.fires: List[Sprite3D] = []
        
        self.clock = pygame.time.Clock()
        self.play_time = 0
        self.time_ms = 0
        
        self.nizz_angle = 0.0  # Rotating floor underneath
        
        self.init_opengl()
        
        self.base_path = Path(__file__).parent
        self.texture_loader = TextureLoader(self.base_path / "Image")
        self.sound = SoundManager(self.base_path)
        
        self.load_all_textures()
        self.load_sounds()
        
    def init_opengl(self):
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(90, SCREEN_W / SCREEN_H, 1.0, 2000.0)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glClearColor(0.0, 0.0, 0.0, 1.0)
        
    def load_all_textures(self):
        """Load ALL textures from both areas"""
        print("\n=== Loading ALL textures ===")
        
        # Load from both Earth and Death
        area = "Earth" if self.game_type == 1 else "Death"
        
        # Current area
        self.texture_loader.load_texture("ground", f"{area}/Ground")
        self.texture_loader.load_texture("wall1", f"{area}/Stena1")
        self.texture_loader.load_texture("wall2", f"{area}/Stena2")
        
        # Sky from Earth
        self.texture_loader.load_texture("sky", "Earth/Nebo")
        
        # ALL tree textures
        self.texture_loader.load_texture("tree1", "Earth/Tree1")
        self.texture_loader.load_texture("tree2", "Death/Tree2")
        
        # ALL fire/smoke textures
        self.texture_loader.load_texture("smoke", "Earth/Smoke")
        self.texture_loader.load_texture("fire", "Death/Faire")
        
        # Nizz (floor underneath)
        self.texture_loader.load_texture("nizz", f"{area}/Nizz")
        
        # Computer
        self.texture_loader.load_texture("computer", "CompKub")
        
        # Intro/Logo
        self.texture_loader.load_texture("intro", f"{area}/Intro1")
        self.texture_loader.load_texture("logo", "IntroD4D")
        
    def load_sounds(self):
        print("\n=== Loading sounds ===")
        self.sound.load_sound("select", "Sound/Select")
        self.sound.load_sound("start", "Sound/Start")
        self.sound.load_sound("laser", "Sound/Laser")
        self.sound.load_sound("pain", "Sound/Pain")
        self.sound.load_sound("dead", "Sound/Dead")
        self.sound.load_sound("killcomp", "Sound/Killcomp")
        self.sound.load_sound("teleport", "Sound/Teleport")
        for i in range(5):
            self.sound.load_sound(f"intro{i}", f"Sound/Intro{i}")
        self.sound.load_music_list("Music")
        
    def init_geometry(self):
        """Initialize trees and fire/smoke - ORIGINAL COORDINATES"""
        self.trees1 = []
        self.trees2 = []
        self.smokes = []
        self.fires = []
        
        random.seed()
        
        # Trees at -95 to 95 (from original!)
        for i in range(TREE_MAX):
            x = random.randint(-95, 95)
            z = random.randint(-95, 95)
            if abs(x) > 5 or abs(z) > 5:  # Avoid center
                self.trees1.append(Sprite3D(x, z, height=20, width=3))
            
            x = random.randint(-95, 95)
            z = random.randint(-95, 95)
            if abs(x) > 5 or abs(z) > 5:
                self.trees2.append(Sprite3D(x, z, height=12, width=5))
            
        # Fire/Smoke at -98 to 98
        for i in range(FIRESMOKE):
            x = random.randint(-98, 98)
            z = random.randint(-98, 98)
            if abs(x) > 10 or abs(z) > 10:
                self.smokes.append(Sprite3D(x, z, height=3, width=1))
                self.fires.append(Sprite3D(x, z, height=3, width=1))
            
    def start_game(self, game_type: int):
        self.game_type = game_type
        self.player = Player()
        self.computer = Computer()
        self.play_time = 0
        self.time_ms = 0
        self.game_over = False
        self.in_menu = False
        self.intro_running = False
        
        # Reload area-specific textures
        area = "Earth" if self.game_type == 1 else "Death"
        self.texture_loader.load_texture("ground", f"{area}/Ground")
        self.texture_loader.load_texture("wall1", f"{area}/Stena1")
        self.texture_loader.load_texture("wall2", f"{area}/Stena2")
        self.texture_loader.load_texture("nizz", f"{area}/Nizz")
        self.texture_loader.load_texture("intro", f"{area}/Intro1")
        
        self.init_geometry()
        
        if self.game_type == 1:
            glClearColor(0.5, 0.7, 1.0, 1.0)
        else:
            glClearColor(0.3, 0.1, 0.1, 1.0)
            
        self.sound.play_sound("start")
        print(f"\nGame started! Area: {'Earth' if game_type == 1 else 'Hell'}")
        
    def draw_ground(self):
        """Draw ground plane"""
        self.texture_loader.bind("ground")
        glColor4f(1, 1, 1, 1)
        
        size = POLE  # -100 to 100
        
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(-size, 0, -size)
        glTexCoord2f(4, 0); glVertex3f(size, 0, -size)
        glTexCoord2f(4, 4); glVertex3f(size, 0, size)
        glTexCoord2f(0, 4); glVertex3f(-size, 0, size)
        glEnd()
        
    def draw_nizz(self):
        """Draw rotating floor underneath (NIZZ from original)"""
        self.texture_loader.bind("nizz")
        glColor4f(1, 1, 1, 0.8)
        
        glPushMatrix()
        glTranslatef(0, -10, 0)  # Below ground
        glRotatef(self.nizz_angle, 0, 1, 0)  # Rotate around Y
        
        size = 500  # Large area
        
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(-size, 0, -size)
        glTexCoord2f(5, 0); glVertex3f(size, 0, -size)
        glTexCoord2f(5, 5); glVertex3f(size, 0, size)
        glTexCoord2f(0, 5); glVertex3f(-size, 0, size)
        glEnd()
        
        glPopMatrix()
        
    def draw_sky(self):
        self.texture_loader.bind("sky")
        glColor4f(1, 1, 1, 1)
        
        dist = 400
        height = 200
        
        glBegin(GL_QUADS)
        # Front
        glTexCoord2f(0, 1); glVertex3f(-dist, 0, dist)
        glTexCoord2f(1, 1); glVertex3f(dist, 0, dist)
        glTexCoord2f(1, 0); glVertex3f(dist, height, dist)
        glTexCoord2f(0, 0); glVertex3f(-dist, height, dist)
        # Back
        glTexCoord2f(0, 1); glVertex3f(dist, 0, -dist)
        glTexCoord2f(1, 1); glVertex3f(-dist, 0, -dist)
        glTexCoord2f(1, 0); glVertex3f(-dist, height, -dist)
        glTexCoord2f(0, 0); glVertex3f(dist, height, -dist)
        # Left
        glTexCoord2f(0, 1); glVertex3f(-dist, 0, -dist)
        glTexCoord2f(1, 1); glVertex3f(-dist, 0, dist)
        glTexCoord2f(1, 0); glVertex3f(-dist, height, dist)
        glTexCoord2f(0, 0); glVertex3f(-dist, height, -dist)
        # Right
        glTexCoord2f(0, 1); glVertex3f(dist, 0, dist)
        glTexCoord2f(1, 1); glVertex3f(dist, 0, -dist)
        glTexCoord2f(1, 0); glVertex3f(dist, height, -dist)
        glTexCoord2f(0, 0); glVertex3f(dist, height, dist)
        glEnd()
        
    def draw_walls(self):
        wall_height = 60
        size = POLE
        
        glColor4f(1, 1, 1, 1)
        
        # Back wall (+Z)
        self.texture_loader.bind("wall1")
        glBegin(GL_QUADS)
        for i in range(10):
            x1 = -size + i * 20
            x2 = -size + (i+1) * 20
            glTexCoord2f(0, 1); glVertex3f(x1, 0, size)
            glTexCoord2f(1, 1); glVertex3f(x2, 0, size)
            glTexCoord2f(1, 0); glVertex3f(x2, wall_height, size)
            glTexCoord2f(0, 0); glVertex3f(x1, wall_height, size)
        glEnd()
        
        # Front wall (-Z)
        glBegin(GL_QUADS)
        for i in range(10):
            x1 = -size + i * 20
            x2 = -size + (i+1) * 20
            glTexCoord2f(0, 1); glVertex3f(x2, 0, -size)
            glTexCoord2f(1, 1); glVertex3f(x1, 0, -size)
            glTexCoord2f(1, 0); glVertex3f(x1, wall_height, -size)
            glTexCoord2f(0, 0); glVertex3f(x2, wall_height, -size)
        glEnd()
        
        # Left wall (-X)
        self.texture_loader.bind("wall2")
        glBegin(GL_QUADS)
        for i in range(10):
            z1 = -size + i * 20
            z2 = -size + (i+1) * 20
            glTexCoord2f(0, 1); glVertex3f(-size, 0, z1)
            glTexCoord2f(1, 1); glVertex3f(-size, 0, z2)
            glTexCoord2f(1, 0); glVertex3f(-size, wall_height, z2)
            glTexCoord2f(0, 0); glVertex3f(-size, wall_height, z1)
        glEnd()
        
        # Right wall (+X)
        glBegin(GL_QUADS)
        for i in range(10):
            z1 = -size + i * 20
            z2 = -size + (i+1) * 20
            glTexCoord2f(0, 1); glVertex3f(size, 0, z2)
            glTexCoord2f(1, 1); glVertex3f(size, 0, z1)
            glTexCoord2f(1, 0); glVertex3f(size, wall_height, z1)
            glTexCoord2f(0, 0); glVertex3f(size, wall_height, z2)
        glEnd()
        
    def draw_sprite_billboard(self, sprite: Sprite3D):
        dx = self.player.x - sprite.x
        dz = self.player.z - sprite.z
        angle = math.atan2(dx, dz)
        
        sx = sprite.width * math.sin(angle)
        sz = sprite.width * math.cos(angle)
        
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex3f(sprite.x - sx, 0, sprite.z - sz)
        glTexCoord2f(1, 1); glVertex3f(sprite.x + sx, 0, sprite.z + sz)
        glTexCoord2f(1, 0); glVertex3f(sprite.x + sx, sprite.height, sprite.z + sz)
        glTexCoord2f(0, 0); glVertex3f(sprite.x - sx, sprite.height, sprite.z - sz)
        glEnd()
        
    def draw_trees(self):
        glColor4f(1, 1, 1, 1)
        
        if "tree1" in self.texture_loader.textures:
            self.texture_loader.bind("tree1")
            for tree in self.trees1:
                self.draw_sprite_billboard(tree)
                
        if "tree2" in self.texture_loader.textures:
            self.texture_loader.bind("tree2")
            for tree in self.trees2:
                self.draw_sprite_billboard(tree)
                    
    def draw_fire_smoke(self):
        if self.game_type == 1 and "smoke" in self.texture_loader.textures:
            glColor4f(1, 1, 1, 0.8)
            self.texture_loader.bind("smoke")
            for smoke in self.smokes[:30]:
                self.draw_sprite_billboard(smoke)
        elif self.game_type == 2 and "fire" in self.texture_loader.textures:
            glColor4f(1, 1, 1, 0.9)
            self.texture_loader.bind("fire")
            for fire in self.fires[:30]:
                self.draw_sprite_billboard(fire)
                
    def draw_computer(self):
        glPushMatrix()
        
        glTranslatef(self.computer.x, self.computer.y, self.computer.z)
        glRotatef(self.computer.rotate_x, 1, 0, 0)
        glRotatef(self.computer.rotate_y, 0, 1, 0)
        glRotatef(self.computer.rotate_z, 0, 0, 1)
        
        size = 10
        self.texture_loader.bind("computer")
        glColor4f(1, 1, 1, 1)
        
        glBegin(GL_QUADS)
        # Front
        glTexCoord2f(0, 1); glVertex3f(-size, -size, -size)
        glTexCoord2f(1, 1); glVertex3f(size, -size, -size)
        glTexCoord2f(1, 0); glVertex3f(size, size, -size)
        glTexCoord2f(0, 0); glVertex3f(-size, size, -size)
        # Back
        glTexCoord2f(1, 1); glVertex3f(size, -size, size)
        glTexCoord2f(0, 1); glVertex3f(-size, -size, size)
        glTexCoord2f(0, 0); glVertex3f(-size, size, size)
        glTexCoord2f(1, 0); glVertex3f(size, size, size)
        # Left
        glTexCoord2f(1, 1); glVertex3f(-size, -size, size)
        glTexCoord2f(0, 1); glVertex3f(-size, -size, -size)
        glTexCoord2f(0, 0); glVertex3f(-size, size, -size)
        glTexCoord2f(1, 0); glVertex3f(-size, size, size)
        # Right
        glTexCoord2f(0, 1); glVertex3f(size, -size, -size)
        glTexCoord2f(1, 1); glVertex3f(size, -size, size)
        glTexCoord2f(1, 0); glVertex3f(size, size, size)
        glTexCoord2f(0, 0); glVertex3f(size, size, -size)
        # Top
        glTexCoord2f(0, 1); glVertex3f(-size, size, -size)
        glTexCoord2f(1, 1); glVertex3f(size, size, -size)
        glTexCoord2f(1, 0); glVertex3f(size, size, size)
        glTexCoord2f(0, 0); glVertex3f(-size, size, size)
        # Bottom
        glTexCoord2f(0, 0); glVertex3f(-size, -size, size)
        glTexCoord2f(1, 0); glVertex3f(size, -size, size)
        glTexCoord2f(1, 1); glVertex3f(size, -size, -size)
        glTexCoord2f(0, 1); glVertex3f(-size, -size, -size)
        glEnd()
        
        glPopMatrix()
        
    def draw_laser(self):
        if not self.player.fire_now:
            return
            
        glDisable(GL_TEXTURE_2D)
        glColor4f(1.0, 0.3, 0.0, 1.0)
        glLineWidth(4.0)
        
        start_x = self.player.x - math.sin(self.player.angle) * 5
        start_z = self.player.z + math.cos(self.player.angle) * 5
        end_x = self.player.x - math.sin(self.player.angle) * 150
        end_z = self.player.z + math.cos(self.player.angle) * 150
        
        glBegin(GL_LINES)
        glVertex3f(start_x, self.player.y, start_z)
        glVertex3f(end_x, self.player.y, end_z)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        
    def draw_crosshair(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_W, SCREEN_H, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_TEXTURE_2D)
        
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        color = (1, 0, 0) if self.player.fire_now else (0, 1, 0)
        glColor3f(*color)
        glLineWidth(2)
        
        glBegin(GL_LINES)
        glVertex2i(cx - 20, cy); glVertex2i(cx - 5, cy)
        glVertex2i(cx + 5, cy); glVertex2i(cx + 20, cy)
        glVertex2i(cx, cy - 20); glVertex2i(cx, cy - 5)
        glVertex2i(cx, cy + 5); glVertex2i(cx, cy + 20)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def draw_energy_bars(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_W, SCREEN_H, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_TEXTURE_2D)
        
        bar_w, bar_h = 200, 25
        margin = 30
        
        # Player
        px, py = margin, SCREEN_H - bar_h - margin
        glColor3f(0.2, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex2i(px, py); glVertex2i(px + bar_w, py)
        glVertex2i(px + bar_w, py + bar_h); glVertex2i(px, py + bar_h)
        glEnd()
        
        pw = int(bar_w * (self.player.energy / self.player.max_energy))
        glColor3f(0, 0.8, 0)
        glBegin(GL_QUADS)
        glVertex2i(px, py); glVertex2i(px + pw, py)
        glVertex2i(px + pw, py + bar_h); glVertex2i(px, py + bar_h)
        glEnd()
        
        glColor3f(1, 1, 1)
        glLineWidth(2)
        glBegin(GL_LINE_LOOP)
        glVertex2i(px, py); glVertex2i(px + bar_w, py)
        glVertex2i(px + bar_w, py + bar_h); glVertex2i(px, py + bar_h)
        glEnd()
        
        # Computer
        cx = SCREEN_W - bar_w - margin
        cy = SCREEN_H - bar_h - margin
        glColor3f(0.2, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex2i(cx, cy); glVertex2i(cx + bar_w, cy)
        glVertex2i(cx + bar_w, cy + bar_h); glVertex2i(cx, cy + bar_h)
        glEnd()
        
        cw = int(bar_w * (self.computer.energy / self.computer.max_energy))
        glColor3f(0.8, 0, 0)
        glBegin(GL_QUADS)
        glVertex2i(cx, cy); glVertex2i(cx + cw, cy)
        glVertex2i(cx + cw, cy + bar_h); glVertex2i(cx, cy + bar_h)
        glEnd()
        
        glColor3f(1, 1, 1)
        glBegin(GL_LINE_LOOP)
        glVertex2i(cx, cy); glVertex2i(cx + bar_w, cy)
        glVertex2i(cx + bar_w, cy + bar_h); glVertex2i(cx, cy + bar_h)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def draw_intro(self):
        """Draw intro animation with zoom effect"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_W, 0, SCREEN_H, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        
        # Black background
        glColor3f(0, 0, 0)
        glBegin(GL_QUADS)
        glVertex2i(0, 0); glVertex2i(SCREEN_W, 0)
        glVertex2i(SCREEN_W, SCREEN_H); glVertex2i(0, SCREEN_H)
        glEnd()
        
        self.texture_loader.bind("intro")
        if self.texture_loader.get("intro"):
            glColor3f(1, 1, 1)
            glEnable(GL_TEXTURE_2D)
            
            # Zoom effect
            z = self.intro_zoom
            
            glBegin(GL_QUADS)
            glTexCoord2f(0, 1); glVertex2i(z, z)
            glTexCoord2f(1, 1); glVertex2i(SCREEN_W - z, z)
            glTexCoord2f(1, 0); glVertex2i(SCREEN_W - z, SCREEN_H - z)
            glTexCoord2f(0, 0); glVertex2i(z, SCREEN_H - z)
            glEnd()
            
            # Draw logo on top
            if self.intro_zoom < 80:
                self.texture_loader.bind("logo")
                if self.texture_loader.get("logo"):
                    lz = 150
                    glBegin(GL_QUADS)
                    glTexCoord2f(0, 0); glVertex2i(lz, lz)
                    glTexCoord2f(1, 0); glVertex2i(SCREEN_W - lz, lz)
                    glTexCoord2f(1, 1); glVertex2i(SCREEN_W - lz, SCREEN_H - lz)
                    glTexCoord2f(0, 1); glVertex2i(lz, SCREEN_H - lz)
                    glEnd()
        
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def draw_menu(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_W, 0, SCREEN_H, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        
        glColor3f(0, 0, 0)
        glBegin(GL_QUADS)
        glVertex2i(0, 0); glVertex2i(SCREEN_W, 0)
        glVertex2i(SCREEN_W, SCREEN_H); glVertex2i(0, SCREEN_H)
        glEnd()
        
        self.texture_loader.bind("logo")
        if self.texture_loader.get("logo"):
            glColor3f(1, 1, 1)
            glEnable(GL_TEXTURE_2D)
            lw, lh = 600, 400
            lx, ly = (SCREEN_W - lw) // 2, (SCREEN_H - lh) // 2
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2i(lx, ly)
            glTexCoord2f(1, 0); glVertex2i(lx + lw, ly)
            glTexCoord2f(1, 1); glVertex2i(lx + lw, ly + lh)
            glTexCoord2f(0, 1); glVertex2i(lx, ly + lh)
            glEnd()
        
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def check_hit(self) -> bool:
        dx = self.computer.x - self.player.x
        dz = self.computer.z - self.player.z
        dist = math.sqrt(dx*dx + dz*dz)
        if dist > 120:
            return False
        angle_to = math.atan2(-dx, dz)
        diff = angle_to - self.player.angle
        while diff > PI: diff -= 2*PI
        while diff < -PI: diff += 2*PI
        return abs(diff) < 0.15
        
    def check_collision(self) -> bool:
        dx = self.computer.x - self.player.x
        dz = self.computer.z - self.player.z
        dist = math.sqrt(dx*dx + dz*dz)
        if dist < 18:
            self.player.energy -= 1
            if self.player.energy <= 0:
                self.player.energy = 0
                self.game_over = True
                self.sound.play_sound("dead")
            return True
        return False
        
    def handle_input(self):
        keys = pygame.key.get_pressed()
        
        if self.in_menu or self.game_over:
            return
            
        # Rotation - FIXED
        if keys[K_LEFT]:
            self.player.angle -= self.player.rotate_speed
        if keys[K_RIGHT]:
            self.player.angle += self.player.rotate_speed
            
        while self.player.angle < 0: self.player.angle += 2*PI
        while self.player.angle >= 2*PI: self.player.angle -= 2*PI
            
        # Movement
        if keys[K_UP]:
            self.player.x -= self.player.step * math.sin(self.player.angle)
            self.player.z += self.player.step * math.cos(self.player.angle)
        if keys[K_DOWN]:
            self.player.x += self.player.step * math.sin(self.player.angle)
            self.player.z -= self.player.step * math.cos(self.player.angle)
            
        # Shooting
        shoot = keys[K_SPACE]
        if shoot and not self.player.last_shoot:
            self.player.fire_now = True
            self.sound.play_sound("laser")
            if self.check_hit():
                self.computer.energy -= 8
                if self.computer.energy <= 0:
                    self.player.wins += 1
                    self.sound.play_sound("killcomp")
                    self.game_type = 2 if self.game_type == 1 else 1
                    self.start_game(self.game_type)
        else:
            self.player.fire_now = False
        self.player.last_shoot = shoot
        
        # Boundaries - ORIGINAL SIZE
        limit = POLE - 5
        self.player.x = max(-limit, min(limit, self.player.x))
        self.player.z = max(-limit, min(limit, self.player.z))
        
    def update(self, dt: int):
        if self.in_menu or self.game_over:
            return
            
        # Update play time
        self.time_ms += dt
        if self.time_ms >= 1000:
            self.time_ms -= 1000
            self.play_time += 1
            
        # Update nizz rotation
        self.nizz_angle += 0.5
        
        self.computer.update()
        self.check_collision()
        
    def update_intro(self, dt: int):
        """Update intro animation"""
        if not self.intro_running:
            return
            
        self.intro_timer += dt
        
        # Zoom in effect
        if self.intro_timer > 50:
            self.intro_timer = 0
            if self.intro_zoom > 0:
                self.intro_zoom -= 2
            else:
                self.intro_running = False
        
    def render(self):
        if self.intro_running:
            self.draw_intro()
            pygame.display.flip()
            return
            
        if self.in_menu:
            self.draw_menu()
            pygame.display.flip()
            return
            
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glLoadIdentity()
        look_x = self.player.x - math.sin(self.player.angle) * 100
        look_z = self.player.z + math.cos(self.player.angle) * 100
        
        gluLookAt(
            self.player.x, self.player.y, self.player.z,
            look_x, self.player.y, look_z,
            0, 1, 0
        )
        
        self.draw_nizz()  # Rotating floor underneath
        self.draw_sky()
        self.draw_ground()
        self.draw_walls()
        self.draw_trees()
        self.draw_fire_smoke()
        self.draw_computer()
        self.draw_laser()
        self.draw_crosshair()
        self.draw_energy_bars()
        
        pygame.display.flip()
        
    def run(self):
        print("\n" + "="*50)
        print("DOOM 4D - Python Remastered")
        print("(c) 2004 Denis Astahov")
        print("="*50)
        print("\nControls:")
        print("  1/E - Earth | 2/H - Hell")
        print("  UP/DOWN - Move | LEFT/RIGHT - Rotate")
        print("  SPACE - Shoot | F1-F7 - Music")
        print("  F12 - Teleport | ESC - Exit")
        
        while self.running:
            dt = self.clock.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        if self.game_over or self.in_menu:
                            self.running = False
                        else:
                            self.game_over = True
                            
                    if self.intro_running:
                        if event.key in [K_RETURN, K_SPACE, K_1, K_e]:
                            self.intro_running = False
                        continue
                        
                    if self.in_menu:
                        if event.key in [K_1, K_e, K_RETURN]:
                            self.sound.play_sound("select")
                            self.start_game(1)
                        elif event.key in [K_2, K_h]:
                            self.sound.play_sound("select")
                            self.start_game(2)
                            
                    if not self.in_menu and not self.game_over:
                        if event.key in [K_F1, K_F2, K_F3, K_F4, K_F5, K_F6, K_F7]:
                            self.sound.play_music(event.key - K_F1 + 1)
                        if event.key == K_F12:
                            self.game_type = 2 if self.game_type == 1 else 1
                            self.sound.play_sound("teleport")
                            self.start_game(self.game_type)
                            
                    if self.game_over and event.key == K_n:
                        self.player.wins = 0
                        self.start_game(1)
                            
            if self.intro_running:
                self.update_intro(dt)
            else:
                self.handle_input()
                self.update(dt)
            
            self.render()
            
        pygame.quit()


if __name__ == "__main__":
    game = Doom4D()
    game.run()
