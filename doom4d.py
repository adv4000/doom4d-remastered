#!/usr/bin/env python3
"""
DOOM 4D - Python Remastered with OpenGL
Originally created by Denis Astahov (ADV-IT) in 2004
Visual Basic 6 + DirectX 7 -> Python + Pygame + PyOpenGL

Bachelor Degree Project - Score: 95/100

Full 3D rendering with OpenGL, original textures and sounds!
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import math
import random
import os
import sys
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# ============== CONSTANTS (from original VB6) ==============
COMPSTEP = 100      # Number of Computer STEPS in one Direction Movement
TREE_MAX = 40       # Counter of Trees - My FOREST :)
FIRESMOKE = 40      # Counter of maximum Fire and Smoke Animations
PI = 3.14159265358979
RADIANS = PI / 180
POLE = 200          # Size of Area from Center to WALLs

# Screen settings
SCREEN_W = 1024
SCREEN_H = 768

# Window title
TITLE = "DOOM 4D - Remastered (c) 2004 Denis Astahov"


# ============== TEXTURE LOADER ==============
class TextureLoader:
    """Load and manage OpenGL textures"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.textures: Dict[str, int] = {}
        
    def load_texture(self, name: str, relative_path: str) -> bool:
        """Load a texture from file"""
        full_path = self.base_path / relative_path
        
        # Try different extensions
        extensions = ['', '.bmp', '.BMP', '.jpg', '.JPG', '.jpeg', '.png']
        
        for ext in extensions:
            test_path = Path(str(full_path) + ext) if ext else full_path
            if test_path.exists():
                full_path = test_path
                break
        else:
            print(f"Texture not found: {relative_path}")
            return False
            
        try:
            # Load image with pygame
            surface = pygame.image.load(str(full_path))
            data = pygame.image.tostring(surface, "RGBA", True)
            width, height = surface.get_size()
            
            # Create OpenGL texture
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, 
                         GL_RGBA, GL_UNSIGNED_BYTE, data)
                         
            self.textures[name] = texture_id
            return True
            
        except Exception as e:
            print(f"Error loading texture {relative_path}: {e}")
            return False
            
    def get(self, name: str) -> int:
        """Get texture ID by name"""
        return self.textures.get(name, 0)
        
    def bind(self, name: str):
        """Bind texture by name"""
        if name in self.textures:
            glBindTexture(GL_TEXTURE_2D, self.textures[name])
        else:
            glBindTexture(GL_TEXTURE_2D, 0)


# ============== SOUND MANAGER ==============
class SoundManager:
    """Handles sound playback with pygame mixer"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.music_files: Dict[str, str] = {}
        self.current_music = None
        
    def load_sound(self, name: str, relative_path: str):
        """Load a sound effect"""
        full_path = self.base_path / relative_path
        
        # Try with extensions
        for ext in ['', '.wav', '.WAV', '.mp3', '.MP3']:
            test_path = Path(str(full_path) + ext) if ext else full_path
            if test_path.exists():
                try:
                    self.sounds[name] = pygame.mixer.Sound(str(test_path))
                    return True
                except Exception as e:
                    print(f"Error loading sound {relative_path}: {e}")
        return False
        
    def load_music_list(self, music_dir: str):
        """Load all music files from directory"""
        music_path = self.base_path / music_dir
        if music_path.exists():
            for i, f in enumerate(sorted(music_path.glob("*.wav"))):
                self.music_files[f"music{i+1}"] = str(f)
                
    def play_sound(self, name: str):
        """Play a sound effect"""
        if name in self.sounds:
            self.sounds[name].play()
            
    def play_music(self, name: str):
        """Play background music"""
        if name in self.music_files:
            try:
                pygame.mixer.music.load(self.music_files[name])
                pygame.mixer.music.play(-1)
                self.current_music = name
            except Exception as e:
                print(f"Error playing music: {e}")
                
    def stop_music(self):
        """Stop background music"""
        pygame.mixer.music.stop()


# ============== 3D SPRITE ==============
class Sprite3D:
    """3D Billboard sprite for trees, fire, smoke"""
    
    def __init__(self, x: float, z: float, height: float, width: float):
        self.x = x
        self.z = z
        self.height = height
        self.width = width
        
    def get_vertices(self, cam_x: float, cam_z: float) -> List[Tuple[float, float, float, float, float]]:
        """Get billboard vertices facing the camera"""
        # Calculate angle from sprite to camera
        dx = cam_x - self.x
        dz = cam_z - self.z
        angle = math.atan2(dx, dz)
        
        # Billboard vertices perpendicular to view direction
        sx = self.width * math.cos(angle)
        sz = self.width * math.sin(angle)
        
        return [
            # Front face
            (self.x - sx, 0, self.z - sz, 0, 1),
            (self.x + sx, 0, self.z + sz, 1, 1),
            (self.x + sx, self.height, self.z + sz, 1, 0),
            (self.x - sx, self.height, self.z - sz, 0, 0),
        ]


# ============== PLAYER ==============
class Player:
    """Player/Camera entity"""
    
    def __init__(self):
        self.x = 0.0
        self.y = 10.0      # Camera height (was 6)
        self.z = -80.0     # Starting position
        self.angle = 0.0   # Rotation angle (alfa)
        
        self.step = 1.0           # Movement speed
        self.rotate_speed = 0.05  # Rotation speed (delta)
        
        self.energy = 100
        self.max_energy = 100
        self.wins = 0
        
        # Shooting
        self.fire_now = False
        self.fire_cooldown = 0
        

# ============== COMPUTER ENEMY ==============
class Computer:
    """AI-controlled enemy cube"""
    
    def __init__(self):
        self.x = 0.0
        self.y = 10.0
        self.z = 0.0
        
        self.new_x = 0
        self.new_z = 0
        self.old_x = 0
        self.old_z = 0
        
        self.dx = 0.0
        self.dz = 0.0
        self.step_count = 0
        
        self.energy = 100
        self.max_energy = 100
        
        self.rotate_x = 0.0
        self.rotate_y = 0.0
        self.rotate_z = 0.0
        
    def spawn_target(self):
        """Set new random target position"""
        self.new_x = random.randint(-90, 90)
        self.new_z = random.randint(-90, 90)
        self.dx = (self.new_x - self.old_x) / COMPSTEP
        self.dz = (self.new_z - self.old_z) / COMPSTEP
        self.old_x = self.new_x
        self.old_z = self.new_z
        self.step_count = 0
        
    def update(self):
        """Update computer position and rotation"""
        if self.step_count >= COMPSTEP:
            self.spawn_target()
            
        self.x += self.dx
        self.z += self.dz
        self.step_count += 1
        
        # Rotate the cube
        self.rotate_x = (self.rotate_x + 1) % 360
        self.rotate_y = (self.rotate_y + 4) % 360  # Faster Y rotation
        self.rotate_z = (self.rotate_z + 1) % 360


# ============== MAIN GAME CLASS ==============
class Doom4D:
    """Main game class with OpenGL rendering"""
    
    def __init__(self):
        # Initialize pygame and OpenGL
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        # Set up display with OpenGL
        self.screen = pygame.display.set_mode(
            (SCREEN_W, SCREEN_H), 
            DOUBLEBUF | OPENGL
        )
        pygame.display.set_caption(TITLE)
        
        # Game state
        self.running = True
        self.game_type = 1  # 1 = Earth, 2 = Hell/Death
        self.in_menu = True
        self.game_over = False
        self.paused = False
        
        # Game objects
        self.player = Player()
        self.computer = Computer()
        self.trees1: List[Sprite3D] = []
        self.trees2: List[Sprite3D] = []
        self.smokes: List[Sprite3D] = []
        self.fires: List[Sprite3D] = []
        
        # Time tracking
        self.clock = pygame.time.Clock()
        self.play_time = 0
        self.time_ms = 0
        
        # Animation
        self.anim_frame = 0
        self.anim_timer = 0
        
        # Initialize OpenGL
        self.init_opengl()
        
        # Load resources
        self.base_path = Path(__file__).parent
        self.texture_loader = TextureLoader(self.base_path / "Image")
        self.sound = SoundManager(self.base_path)
        
        self.load_textures()
        self.load_sounds()
        
        # Mouse state for rotation
        self.mouse_grabbed = False
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)
        
    def init_opengl(self):
        """Initialize OpenGL settings"""
        # Enable depth testing
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        
        # Enable textures
        glEnable(GL_TEXTURE_2D)
        
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Set up perspective projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(90, SCREEN_W / SCREEN_H, 0.1, 1000.0)  # 90° FOV like original
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Set clear color (sky color)
        if self.game_type == 1:
            glClearColor(0.5, 0.7, 1.0, 1.0)  # Light blue for Earth
        else:
            glClearColor(0.3, 0.1, 0.1, 1.0)  # Dark red for Hell
            
    def load_textures(self):
        """Load all game textures"""
        area = "Earth" if self.game_type == 1 else "Death"
        
        # Ground texture
        self.texture_loader.load_texture("ground", f"{area}/Ground")
        
        # Wall textures
        self.texture_loader.load_texture("wall1", f"{area}/Stena1")
        self.texture_loader.load_texture("wall2", f"{area}/Stena2")
        
        # Sky textures
        self.texture_loader.load_texture("sky", f"{area}/Nebo")
        self.texture_loader.load_texture("nizz", f"{area}/Nizz")
        
        # Tree textures
        if self.game_type == 1:
            self.texture_loader.load_texture("tree1", "Earth/Tree1")
        self.texture_loader.load_texture("tree2", f"{area}/Tree2")
        
        # Fire/Smoke
        self.texture_loader.load_texture("fire", f"{area}/Faire")
        self.texture_loader.load_texture("smoke", "Earth/Smoke")
        
        # Interface
        self.texture_loader.load_texture("craft", "CraftStain")
        self.texture_loader.load_texture("craft_fired", "CraftFired")
        self.texture_loader.load_texture("energy_cmp", "EnergyCMP")
        self.texture_loader.load_texture("energy_ply", "EnergyPLY")
        self.texture_loader.load_texture("explosion", "Expl")
        self.texture_loader.load_texture("computer", "CompKub")
        
        # Intro/Game Over
        self.texture_loader.load_texture("intro", f"{area}/Intro1")
        self.texture_loader.load_texture("gameover", "GameOver")
        self.texture_loader.load_texture("logo", "IntroD4D")
        
    def load_sounds(self):
        """Load all sound effects and music"""
        sound_path = self.base_path / "Sound"
        
        self.sound.load_sound("select", "Select")
        self.sound.load_sound("start", "Start")
        self.sound.load_sound("laser", "Laser")
        self.sound.load_sound("pain", "Pain")
        self.sound.load_sound("dead", "Dead")
        self.sound.load_sound("killcomp", "Killcomp")
        self.sound.load_sound("teleport", "Teleport")
        self.sound.load_sound("intro0", "Intro0")
        self.sound.load_sound("intro1", "Intro1")
        self.sound.load_sound("intro2", "Intro2")
        self.sound.load_sound("intro3", "Intro3")
        self.sound.load_sound("intro4", "Intro4")
        
        # Load music
        self.sound.load_music_list("Music")
        
    def init_geometry(self):
        """Initialize 3D geometry (trees, fire, smoke)"""
        self.trees1 = []
        self.trees2 = []
        self.smokes = []
        self.fires = []
        
        # Create trees (like original VB code)
        for i in range(TREE_MAX):
            x = random.randint(-95, 95)
            z = random.randint(-95, 95)
            self.trees1.append(Sprite3D(x, z, height=20, width=3))
            
            x = random.randint(-95, 95)
            z = random.randint(-95, 95)
            self.trees2.append(Sprite3D(x, z, height=12, width=5))
            
        # Create smoke/fire
        for i in range(FIRESMOKE):
            x = random.randint(-98, 98)
            z = random.randint(-98, 98)
            self.smokes.append(Sprite3D(x, z, height=3, width=1))
            
            x = random.randint(-98, 98)
            z = random.randint(-98, 98)
            self.fires.append(Sprite3D(x, z, height=3, width=1))
            
    def start_game(self, game_type: int):
        """Start a new game"""
        self.game_type = game_type
        self.player = Player()
        self.computer = Computer()
        self.play_time = 0
        self.time_ms = 0
        self.game_over = False
        self.in_menu = False
        
        # Reload textures for selected area
        self.texture_loader = TextureLoader(self.base_path / "Image")
        self.load_textures()
        
        # Init geometry
        self.init_geometry()
        
        # Update sky color
        if self.game_type == 1:
            glClearColor(0.5, 0.7, 1.0, 1.0)
        else:
            glClearColor(0.3, 0.1, 0.1, 1.0)
            
        # Play start sound
        self.sound.play_sound("start")
        
    def draw_ground(self):
        """Draw the ground plane"""
        self.texture_loader.bind("ground")
        
        size = POLE  # Ground size
        
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(-size, 0, -size)
        glTexCoord2f(20, 0); glVertex3f(size, 0, -size)
        glTexCoord2f(20, 20); glVertex3f(size, 0, size)
        glTexCoord2f(0, 20); glVertex3f(-size, 0, size)
        glEnd()
        
    def draw_sky(self):
        """Draw sky dome (simple version)"""
        self.texture_loader.bind("sky")
        
        glColor4f(1, 1, 1, 0.8)
        
        # Draw sky as a large sphere around player
        radius = 300
        
        glBegin(GL_QUADS)
        # Front
        glTexCoord2f(0, 0); glVertex3f(-radius, 0, -radius)
        glTexCoord2f(1, 0); glVertex3f(radius, 0, -radius)
        glTexCoord2f(1, 1); glVertex3f(radius, radius*2, -radius)
        glTexCoord2f(0, 1); glVertex3f(-radius, radius*2, -radius)
        glEnd()
        
    def draw_walls(self):
        """Draw arena walls"""
        glDisable(GL_TEXTURE_2D)
        
        wall_height = 60
        wall_size = POLE
        
        # Wall colors based on game type
        if self.game_type == 1:
            wall_color = (0.6, 0.4, 0.2, 1.0)  # Brown for Earth
        else:
            wall_color = (0.4, 0.2, 0.1, 1.0)  # Dark red for Hell
            
        glColor4f(*wall_color)
        
        # Back wall
        self.texture_loader.bind("wall1")
        glBegin(GL_QUADS)
        for i in range(10):
            x1 = -wall_size + i * 40
            x2 = -wall_size + (i+1) * 40
            glTexCoord2f(0, 0); glVertex3f(x1, 0, wall_size)
            glTexCoord2f(1, 0); glVertex3f(x2, 0, wall_size)
            glTexCoord2f(1, 1); glVertex3f(x2, wall_height, wall_size)
            glTexCoord2f(0, 1); glVertex3f(x1, wall_height, wall_size)
        glEnd()
        
        # Front wall
        glBegin(GL_QUADS)
        for i in range(10):
            x1 = -wall_size + i * 40
            x2 = -wall_size + (i+1) * 40
            glTexCoord2f(0, 0); glVertex3f(x2, 0, -wall_size)
            glTexCoord2f(1, 0); glVertex3f(x1, 0, -wall_size)
            glTexCoord2f(1, 1); glVertex3f(x1, wall_height, -wall_size)
            glTexCoord2f(0, 1); glVertex3f(x2, wall_height, -wall_size)
        glEnd()
        
        # Left wall
        self.texture_loader.bind("wall2")
        glBegin(GL_QUADS)
        for i in range(10):
            z1 = -wall_size + i * 40
            z2 = -wall_size + (i+1) * 40
            glTexCoord2f(0, 0); glVertex3f(-wall_size, 0, z1)
            glTexCoord2f(1, 0); glVertex3f(-wall_size, 0, z2)
            glTexCoord2f(1, 1); glVertex3f(-wall_size, wall_height, z2)
            glTexCoord2f(0, 1); glVertex3f(-wall_size, wall_height, z1)
        glEnd()
        
        # Right wall
        glBegin(GL_QUADS)
        for i in range(10):
            z1 = -wall_size + i * 40
            z2 = -wall_size + (i+1) * 40
            glTexCoord2f(0, 0); glVertex3f(wall_size, 0, z2)
            glTexCoord2f(1, 0); glVertex3f(wall_size, 0, z1)
            glTexCoord2f(1, 1); glVertex3f(wall_size, wall_height, z1)
            glTexCoord2f(0, 1); glVertex3f(wall_size, wall_height, z2)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        
    def draw_sprite(self, sprite: Sprite3D, texture_x: float = 0):
        """Draw a billboard sprite"""
        verts = sprite.get_vertices(self.player.x, self.player.z)
        
        glBegin(GL_QUADS)
        for v in verts:
            glTexCoord2f(v[3], v[4])
            glVertex3f(v[0], v[1], v[2])
        glEnd()
        
    def draw_trees(self):
        """Draw all trees"""
        # Tree type 1
        if self.game_type == 1:
            self.texture_loader.bind("tree1")
            for tree in self.trees1:
                self.draw_sprite(tree)
                
        # Tree type 2
        self.texture_loader.bind("tree2")
        for tree in self.trees2:
            self.draw_sprite(tree)
            
    def draw_fire_smoke(self):
        """Draw fire and smoke with animation"""
        # Smoke
        self.texture_loader.bind("smoke")
        for smoke in self.smokes:
            self.draw_sprite(smoke)
            
        # Fire (animated)
        self.texture_loader.bind("fire")
        for fire in self.fires:
            self.draw_sprite(fire)
            
    def draw_computer(self):
        """Draw the enemy cube"""
        glPushMatrix()
        
        glTranslatef(self.computer.x, self.computer.y, self.computer.z)
        glRotatef(self.computer.rotate_x, 1, 0, 0)
        glRotatef(self.computer.rotate_y, 0, 1, 0)
        glRotatef(self.computer.rotate_z, 0, 0, 1)
        
        size = 7
        
        self.texture_loader.bind("computer")
        
        # Draw all 6 faces of the cube
        glBegin(GL_QUADS)
        
        # Front face
        glTexCoord2f(0, 1); glVertex3f(-size, -size, -size)
        glTexCoord2f(1, 1); glVertex3f(size, -size, -size)
        glTexCoord2f(1, 0); glVertex3f(size, size, -size)
        glTexCoord2f(0, 0); glVertex3f(-size, size, -size)
        
        # Back face
        glTexCoord2f(0, 1); glVertex3f(size, -size, size)
        glTexCoord2f(1, 1); glVertex3f(-size, -size, size)
        glTexCoord2f(1, 0); glVertex3f(-size, size, size)
        glTexCoord2f(0, 0); glVertex3f(size, size, size)
        
        # Left face
        glTexCoord2f(0, 1); glVertex3f(-size, -size, size)
        glTexCoord2f(1, 1); glVertex3f(-size, -size, -size)
        glTexCoord2f(1, 0); glVertex3f(-size, size, -size)
        glTexCoord2f(0, 0); glVertex3f(-size, size, size)
        
        # Right face
        glTexCoord2f(0, 1); glVertex3f(size, -size, -size)
        glTexCoord2f(1, 1); glVertex3f(size, -size, size)
        glTexCoord2f(1, 0); glVertex3f(size, size, size)
        glTexCoord2f(0, 0); glVertex3f(size, size, -size)
        
        # Top face
        glTexCoord2f(0, 1); glVertex3f(-size, size, -size)
        glTexCoord2f(1, 1); glVertex3f(size, size, -size)
        glTexCoord2f(1, 0); glVertex3f(size, size, size)
        glTexCoord2f(0, 0); glVertex3f(-size, size, size)
        
        # Bottom face
        glTexCoord2f(0, 1); glVertex3f(-size, -size, size)
        glTexCoord2f(1, 1); glVertex3f(size, -size, size)
        glTexCoord2f(1, 0); glVertex3f(size, -size, -size)
        glTexCoord2f(0, 0); glVertex3f(-size, -size, -size)
        
        glEnd()
        glPopMatrix()
        
    def draw_laser(self):
        """Draw laser beam when shooting"""
        if not self.player.fire_now:
            return
            
        glDisable(GL_TEXTURE_2D)
        glColor4f(1.0, 0.0, 0.0, 1.0)
        
        glLineWidth(3.0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)  # From center
        glVertex3f(0, 0, -200)  # Forward
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        
    def draw_crosshair(self):
        """Draw crosshair on screen (2D overlay)"""
        # Switch to 2D mode
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_W, SCREEN_H, 0, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_TEXTURE_2D)
        
        # Draw crosshair
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        size = 15
        
        color = (0, 1, 0) if not self.player.fire_now else (1, 0, 0)
        glColor3f(*color)
        glLineWidth(2)
        
        glBegin(GL_LINES)
        # Horizontal
        glVertex2i(cx - size, cy)
        glVertex2i(cx - 5, cy)
        glVertex2i(cx + 5, cy)
        glVertex2i(cx + size, cy)
        # Vertical
        glVertex2i(cx, cy - size)
        glVertex2i(cx, cy - 5)
        glVertex2i(cx, cy + 5)
        glVertex2i(cx, cy + size)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)
        
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def draw_energy_bars(self):
        """Draw energy bars as 2D overlay"""
        # Switch to 2D
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_W, SCREEN_H, 0, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_TEXTURE_2D)
        
        bar_width = 150
        bar_height = 20
        
        # Player energy (left side)
        px, py = 30, 30
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_QUADS)
        glVertex2i(px, py)
        glVertex2i(px + bar_width, py)
        glVertex2i(px + bar_width, py + bar_height)
        glVertex2i(px, py + bar_height)
        glEnd()
        
        glColor3f(0, 1, 0)
        pw = int(bar_width * (self.player.energy / self.player.max_energy))
        glBegin(GL_QUADS)
        glVertex2i(px, py)
        glVertex2i(px + pw, py)
        glVertex2i(px + pw, py + bar_height)
        glVertex2i(px, py + bar_height)
        glEnd()
        
        # Computer energy (right side)
        cx = SCREEN_W - bar_width - 30
        cy = 30
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_QUADS)
        glVertex2i(cx, cy)
        glVertex2i(cx + bar_width, cy)
        glVertex2i(cx + bar_width, cy + bar_height)
        glVertex2i(cx, cy + bar_height)
        glEnd()
        
        glColor3f(1, 0, 0)
        cw = int(bar_width * (self.computer.energy / self.computer.max_energy))
        glBegin(GL_QUADS)
        glVertex2i(cx, cy)
        glVertex2i(cx + cw, cy)
        glVertex2i(cx + cw, cy + bar_height)
        glVertex2i(cx, cy + bar_height)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)
        
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def draw_hud(self):
        """Draw all HUD elements"""
        self.draw_crosshair()
        self.draw_energy_bars()
        
    def draw_menu(self):
        """Draw main menu"""
        # Switch to 2D
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_W, SCREEN_H, 0, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)
        
        # Background
        glColor3f(0, 0, 0)
        glBegin(GL_QUADS)
        glVertex2i(0, 0)
        glVertex2i(SCREEN_W, 0)
        glVertex2i(SCREEN_W, SCREEN_H)
        glVertex2i(0, SCREEN_H)
        glEnd()
        
        # Draw logo/intro image if available
        self.texture_loader.bind("logo")
        if self.texture_loader.get("logo"):
            glColor3f(1, 1, 1)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2i(100, 100)
            glTexCoord2f(1, 0); glVertex2i(SCREEN_W-100, 100)
            glTexCoord2f(1, 1); glVertex2i(SCREEN_W-100, SCREEN_H-200)
            glTexCoord2f(0, 1); glVertex2i(100, SCREEN_H-200)
            glEnd()
        
        # Text would be drawn here with pygame font
        # For now, we just have the visual elements
        
        glEnable(GL_DEPTH_TEST)
        
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def check_hit(self) -> bool:
        """Check if player shot hits the computer"""
        # Vector from player to computer
        dx = self.computer.x - self.player.x
        dz = self.computer.z - self.player.z
        
        distance = math.sqrt(dx*dx + dz*dz)
        
        if distance > 150:
            return False
            
        # Angle to computer
        angle_to_comp = math.atan2(dx, dz)
        
        # Difference from player angle
        angle_diff = angle_to_comp - self.player.angle
        
        # Normalize
        while angle_diff > PI:
            angle_diff -= 2 * PI
        while angle_diff < -PI:
            angle_diff += 2 * PI
            
        # Hit if within ~5 degrees
        if abs(angle_diff) < 0.1:
            return True
            
        return False
        
    def check_collision(self) -> bool:
        """Check player-computer collision"""
        dx = self.computer.x - self.player.x
        dz = self.computer.z - self.player.z
        dist = math.sqrt(dx*dx + dz*dz)
        
        if dist < 15:
            self.player.energy -= 2
            if self.player.energy <= 0:
                self.player.energy = 0
                self.game_over = True
            return True
        return False
        
    def handle_input(self):
        """Handle keyboard and mouse input"""
        keys = pygame.key.get_pressed()
        
        if self.in_menu:
            return
            
        if self.game_over:
            if keys[K_n]:
                # New game
                self.game_type = 1
                self.start_game(1)
            return
            
        # Forward/Backward
        if keys[K_UP] or keys[K_w]:
            self.player.x += self.player.step * math.sin(self.player.angle)
            self.player.z += self.player.step * math.cos(self.player.angle)
            
        if keys[K_DOWN] or keys[K_s]:
            self.player.x -= self.player.step * math.sin(self.player.angle)
            self.player.z -= self.player.step * math.cos(self.player.angle)
            
        # Rotation with mouse or keyboard
        if keys[K_LEFT] or keys[K_a]:
            self.player.angle -= self.player.rotate_speed
        if keys[K_RIGHT] or keys[K_d]:
            self.player.angle += self.player.rotate_speed
            
        # Strafe (from original)
        if keys[K_q]:
            self.player.x -= self.player.step * math.cos(self.player.angle)
            self.player.z += self.player.step * math.sin(self.player.angle)
        if keys[K_e]:
            self.player.x += self.player.step * math.cos(self.player.angle)
            self.player.z -= self.player.step * math.sin(self.player.angle)
            
        # Shooting
        if keys[K_SPACE] and self.player.fire_cooldown <= 0:
            self.player.fire_now = True
            self.player.fire_cooldown = 10
            self.sound.play_sound("laser")
            
            if self.check_hit():
                self.computer.energy -= 5
                if self.computer.energy <= 0:
                    # Kill the computer!
                    self.player.wins += 1
                    self.sound.play_sound("killcomp")
                    
                    # Switch area
                    self.game_type = 2 if self.game_type == 1 else 1
                    self.start_game(self.game_type)
        else:
            self.player.fire_now = False
            
        if self.player.fire_cooldown > 0:
            self.player.fire_cooldown -= 1
            
        # Wall boundaries
        limit = POLE - 5
        self.player.x = max(-limit, min(limit, self.player.x))
        self.player.z = max(-limit, min(limit, self.player.z))
        
        # Teleport (F12)
        if keys[K_F12]:
            self.game_type = 2 if self.game_type == 1 else 1
            self.sound.play_sound("teleport")
            self.start_game(self.game_type)
            
        # Music controls (F1-F7)
        music_keys = [K_F1, K_F2, K_F3, K_F4, K_F5, K_F6, K_F7]
        for i, key in enumerate(music_keys):
            if keys[key]:
                music_name = f"music{i+1}"
                if music_name in self.sound.music_files:
                    self.sound.play_music(music_name)
                    
    def update(self, dt: int):
        """Update game state"""
        if self.in_menu or self.game_over:
            return
            
        # Update play time
        self.time_ms += dt
        if self.time_ms >= 1000:
            self.time_ms -= 1000
            self.play_time += 1
            
        # Update computer
        self.computer.update()
        
        # Check collision
        self.check_collision()
        
        # Animation timer
        self.anim_timer += dt
        if self.anim_timer >= 100:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % 4
            
    def render(self):
        """Render the scene"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if self.in_menu:
            self.draw_menu()
            pygame.display.flip()
            return
            
        # Set up camera
        glLoadIdentity()
        
        # Camera position and rotation
        look_x = self.player.x + math.sin(self.player.angle) * 100
        look_z = self.player.z + math.cos(self.player.angle) * 100
        
        gluLookAt(
            self.player.x, self.player.y, self.player.z,
            look_x, self.player.y, look_z,
            0, 1, 0
        )
        
        # Draw scene
        self.draw_sky()
        self.draw_ground()
        self.draw_walls()
        self.draw_trees()
        self.draw_fire_smoke()
        self.draw_computer()
        self.draw_laser()
        
        # Draw HUD (2D overlay)
        self.draw_hud()
        
        pygame.display.flip()
        
    def run(self):
        """Main game loop"""
        while self.running:
            dt = self.clock.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        if self.game_over:
                            self.running = False
                        else:
                            self.game_over = True
                            
                    # Menu controls
                    if self.in_menu:
                        if event.key == K_1 or event.key == K_e:
                            self.start_game(1)  # Earth
                        elif event.key == K_2 or event.key == K_h:
                            self.start_game(2)  # Hell
                            
                    # Mouse grab toggle
                    if event.key == K_TAB:
                        self.mouse_grabbed = not self.mouse_grabbed
                        pygame.event.set_grab(self.mouse_grabbed)
                        pygame.mouse.set_visible(not self.mouse_grabbed)
                        
                elif event.type == MOUSEBUTTONDOWN:
                    if self.in_menu:
                        # Click to start
                        self.start_game(1)
                        
            # Handle continuous input
            self.handle_input()
            
            # Update game state
            self.update(dt)
            
            # Render
            self.render()
            
        pygame.quit()


# ============== MAIN ==============
def main():
    """Entry point"""
    print("=" * 50)
    print("DOOM 4D - Python Remastered")
    print("(c) 2004 Denis Astahov")
    print("=" * 50)
    print()
    print("Controls:")
    print("  W/↑ - Move forward")
    print("  S/↓ - Move backward")
    print("  A/← - Rotate left")
    print("  D/→ - Rotate right")
    print("  Q/E - Strafe left/right")
    print("  SPACE - Shoot")
    print("  F1-F7 - Change music")
    print("  F12 - Teleport to other area")
    print("  ESC - Exit")
    print()
    print("Starting game...")
    print()
    
    game = Doom4D()
    game.run()


if __name__ == "__main__":
    main()
