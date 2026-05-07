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
POLE = 100          # Size of Area from Center to WALLs (was 200, but arena is -100 to 100)

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
        extensions = ['', '.bmp', '.BMP', '.jpg', '.JPG', '.jpeg', '.JPEG', '.png', '.PNG']
        
        for ext in extensions:
            test_path = Path(str(full_path) + ext) if ext else full_path
            if test_path.exists():
                full_path = test_path
                break
        else:
            # Silent fail for optional textures
            if name not in ['tree1', 'tree2', 'fire', 'smoke']:
                print(f"Texture not found: {relative_path}")
            return False
            
        try:
            # Load image with pygame
            surface = pygame.image.load(str(full_path))
            
            # Convert to RGBA if needed
            if surface.get_alpha():
                data = pygame.image.tostring(surface, "RGBA", True)
                format = GL_RGBA
            else:
                # For BMP files without alpha, use RGB
                data = pygame.image.tostring(surface, "RGB", True)
                format = GL_RGB
                
            width, height = surface.get_size()
            
            # Create OpenGL texture
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            
            # Fix inverted textures - flip vertically
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, 
                         format, GL_UNSIGNED_BYTE, data)
                         
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
        self.music_files: Dict[int, str] = {}
        self.current_music = None
        
    def load_sound(self, name: str, relative_path: str) -> bool:
        """Load a sound effect"""
        full_path = self.base_path / relative_path
        
        # Try with extensions
        for ext in ['', '.wav', '.WAV', '.mp3', '.MP3']:
            test_path = Path(str(full_path) + ext) if ext else full_path
            if test_path.exists():
                try:
                    self.sounds[name] = pygame.mixer.Sound(str(test_path))
                    print(f"Loaded sound: {name}")
                    return True
                except Exception as e:
                    print(f"Error loading sound {relative_path}: {e}")
        print(f"Sound not found: {relative_path}")
        return False
        
    def load_music_list(self, music_dir: str):
        """Load all music files from directory"""
        music_path = self.base_path / music_dir
        if music_path.exists():
            for f in sorted(music_path.glob("Music*.wav")):
                # Extract number from filename
                num = ''.join(filter(str.isdigit, f.stem))
                if num:
                    self.music_files[int(num)] = str(f)
                    print(f"Found music: {f.name}")
                    
    def play_sound(self, name: str):
        """Play a sound effect"""
        if name in self.sounds:
            self.sounds[name].play()
            
    def play_music(self, num: int):
        """Play background music by number"""
        if num in self.music_files:
            try:
                pygame.mixer.music.load(self.music_files[num])
                pygame.mixer.music.play(-1)
                self.current_music = num
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


# ============== PLAYER ==============
class Player:
    """Player/Camera entity"""
    
    def __init__(self):
        self.x = 0.0
        self.y = 10.0      # Camera height
        self.z = -50.0     # Starting position (looking at center)
        self.angle = 0.0   # Rotation angle (alfa) - 0 = looking forward (+Z)
        
        self.step = 1.5           # Movement speed
        self.rotate_speed = 0.04  # Rotation speed
        
        self.energy = 100
        self.max_energy = 100
        self.wins = 0
        
        # Shooting
        self.fire_now = False
        self.fire_cooldown = 0
        self.last_shoot = False  # For single shot detection
        

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
        self.step_count = COMPSTEP
        
        self.energy = 100
        self.max_energy = 100
        
        self.rotate_x = 0.0
        self.rotate_y = 0.0
        self.rotate_z = 0.0
        
    def spawn_target(self):
        """Set new random target position"""
        self.new_x = random.randint(-80, 80)
        self.new_z = random.randint(-80, 80)
        self.dx = (self.new_x - self.x) / COMPSTEP
        self.dz = (self.new_z - self.z) / COMPSTEP
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
        self.rotate_y = (self.rotate_y + 5) % 360  # Faster Y rotation
        self.rotate_z = (self.rotate_z + 1) % 360


# ============== MAIN GAME CLASS ==============
class Doom4D:
    """Main game class with OpenGL rendering"""
    
    def __init__(self):
        # Initialize pygame
        pygame.init()
        
        # Initialize mixer with proper settings
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
        
        # Game objects
        self.player = Player()
        self.computer = Computer()
        
        # Sprites
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
        
        # Pre-load menu textures
        self.load_menu_textures()
        self.load_sounds()
        
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
        # 90° FOV like original DirectX code
        gluPerspective(90, SCREEN_W / SCREEN_H, 1.0, 1000.0)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Set clear color
        glClearColor(0.0, 0.0, 0.0, 1.0)
        
    def load_menu_textures(self):
        """Load textures needed for menu"""
        self.texture_loader.load_texture("logo", "IntroD4D")
        self.texture_loader.load_texture("gameover", "GameOver")
        
    def load_textures(self):
        """Load all game textures for current area"""
        area = "Earth" if self.game_type == 1 else "Death"
        print(f"Loading textures for area: {area}")
        
        # Ground texture
        self.texture_loader.load_texture("ground", f"{area}/Ground")
        
        # Wall textures
        self.texture_loader.load_texture("wall1", f"{area}/Stena1")
        self.texture_loader.load_texture("wall2", f"{area}/Stena2")
        
        # Sky textures
        self.texture_loader.load_texture("sky", f"{area}/Nebo")
        
        # Tree textures - Tree1 only in Earth, Tree2 only in Death
        if self.game_type == 1:
            self.texture_loader.load_texture("tree1", "Earth/Tree1")
            # Tree2 not in Earth folder, use tree1 as fallback
        else:
            self.texture_loader.load_texture("tree2", "Death/Tree2")
            
        # Fire/Smoke - Fire only in Death, Smoke only in Earth
        if self.game_type == 1:
            self.texture_loader.load_texture("smoke", "Earth/Smoke")
        else:
            self.texture_loader.load_texture("fire", "Death/Faire")
            
        # Interface textures
        self.texture_loader.load_texture("craft", "CraftStain")
        self.texture_loader.load_texture("craft_fired", "CraftFired")
        self.texture_loader.load_texture("energy_cmp", "EnergyCMP")
        self.texture_loader.load_texture("energy_ply", "EnergyPLY")
        self.texture_loader.load_texture("computer", "CompKub")
        
        # Intro for current area
        self.texture_loader.load_texture("intro", f"{area}/Intro1")
        
    def load_sounds(self):
        """Load all sound effects and music"""
        print("Loading sounds...")
        
        self.sound.load_sound("select", "Sound/Select")
        self.sound.load_sound("start", "Sound/Start")
        self.sound.load_sound("laser", "Sound/Laser")
        self.sound.load_sound("pain", "Sound/Pain")
        self.sound.load_sound("dead", "Sound/Dead")
        self.sound.load_sound("killcomp", "Sound/Killcomp")
        self.sound.load_sound("teleport", "Sound/Teleport")
        
        # Load music
        self.sound.load_music_list("Music")
        
    def init_geometry(self):
        """Initialize 3D geometry (trees, fire, smoke)"""
        self.trees1 = []
        self.trees2 = []
        self.smokes = []
        self.fires = []
        
        random.seed()  # Randomize
        
        # Create trees
        for i in range(TREE_MAX):
            x = random.randint(-90, 90)
            z = random.randint(-90, 90)
            # Avoid center where computer spawns
            if abs(x) < 20 and abs(z) < 20:
                continue
            self.trees1.append(Sprite3D(x, z, height=20, width=4))
            
            x = random.randint(-90, 90)
            z = random.randint(-90, 90)
            if abs(x) < 20 and abs(z) < 20:
                continue
            self.trees2.append(Sprite3D(x, z, height=15, width=6))
            
        # Create smoke/fire depending on area
        for i in range(FIRESMOKE):
            x = random.randint(-95, 95)
            z = random.randint(-95, 95)
            if abs(x) < 25 and abs(z) < 25:
                continue
            self.smokes.append(Sprite3D(x, z, height=5, width=2))
            self.fires.append(Sprite3D(x, z, height=5, width=2))
            
    def start_game(self, game_type: int):
        """Start a new game"""
        self.game_type = game_type
        self.player = Player()
        self.computer = Computer()
        self.play_time = 0
        self.time_ms = 0
        self.game_over = False
        self.in_menu = False
        
        # Load textures for area
        self.texture_loader = TextureLoader(self.base_path / "Image")
        self.load_textures()
        
        # Init geometry
        self.init_geometry()
        
        # Update sky color
        if self.game_type == 1:
            glClearColor(0.5, 0.7, 1.0, 1.0)  # Blue sky for Earth
        else:
            glClearColor(0.4, 0.1, 0.1, 1.0)  # Dark red for Hell
            
        # Play start sound
        self.sound.play_sound("start")
        
        print(f"Game started! Area: {'Earth' if game_type == 1 else 'Hell'}")
        
    def draw_ground(self):
        """Draw the ground plane"""
        self.texture_loader.bind("ground")
        
        size = POLE
        
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(-size, 0, size)
        glTexCoord2f(10, 0); glVertex3f(size, 0, size)
        glTexCoord2f(10, 10); glVertex3f(size, 0, -size)
        glTexCoord2f(0, 10); glVertex3f(-size, 0, -size)
        glEnd()
        
    def draw_sky(self):
        """Draw sky dome"""
        self.texture_loader.bind("sky")
        
        glColor4f(1, 1, 1, 1)
        
        # Draw sky box around player
        dist = 250
        height = 150
        
        # Calculate rotated sky position based on camera
        glBegin(GL_QUADS)
        # Front sky
        glTexCoord2f(0, 1); glVertex3f(-dist, 0, -dist)
        glTexCoord2f(1, 1); glVertex3f(dist, 0, -dist)
        glTexCoord2f(1, 0); glVertex3f(dist, height, -dist)
        glTexCoord2f(0, 0); glVertex3f(-dist, height, -dist)
        
        # Back sky
        glTexCoord2f(0, 1); glVertex3f(dist, 0, dist)
        glTexCoord2f(1, 1); glVertex3f(-dist, 0, dist)
        glTexCoord2f(1, 0); glVertex3f(-dist, height, dist)
        glTexCoord2f(0, 0); glVertex3f(dist, height, dist)
        
        # Left sky
        glTexCoord2f(0, 1); glVertex3f(-dist, 0, dist)
        glTexCoord2f(1, 1); glVertex3f(-dist, 0, -dist)
        glTexCoord2f(1, 0); glVertex3f(-dist, height, -dist)
        glTexCoord2f(0, 0); glVertex3f(-dist, height, dist)
        
        # Right sky
        glTexCoord2f(0, 1); glVertex3f(dist, 0, -dist)
        glTexCoord2f(1, 1); glVertex3f(dist, 0, dist)
        glTexCoord2f(1, 0); glVertex3f(dist, height, dist)
        glTexCoord2f(0, 0); glVertex3f(dist, height, -dist)
        glEnd()
        
    def draw_walls(self):
        """Draw arena walls"""
        wall_height = 60
        wall_size = POLE
        
        glEnable(GL_TEXTURE_2D)
        
        # Back wall (positive Z)
        self.texture_loader.bind("wall1")
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        for i in range(10):
            x1 = -wall_size + i * 20
            x2 = -wall_size + (i+1) * 20
            glTexCoord2f(0, 1); glVertex3f(x1, 0, wall_size)
            glTexCoord2f(1, 1); glVertex3f(x2, 0, wall_size)
            glTexCoord2f(1, 0); glVertex3f(x2, wall_height, wall_size)
            glTexCoord2f(0, 0); glVertex3f(x1, wall_height, wall_size)
        glEnd()
        
        # Front wall (negative Z)
        glBegin(GL_QUADS)
        for i in range(10):
            x1 = -wall_size + i * 20
            x2 = -wall_size + (i+1) * 20
            glTexCoord2f(0, 1); glVertex3f(x2, 0, -wall_size)
            glTexCoord2f(1, 1); glVertex3f(x1, 0, -wall_size)
            glTexCoord2f(1, 0); glVertex3f(x1, wall_height, -wall_size)
            glTexCoord2f(0, 0); glVertex3f(x2, wall_height, -wall_size)
        glEnd()
        
        # Left wall (negative X)
        self.texture_loader.bind("wall2")
        glBegin(GL_QUADS)
        for i in range(10):
            z1 = -wall_size + i * 20
            z2 = -wall_size + (i+1) * 20
            glTexCoord2f(0, 1); glVertex3f(-wall_size, 0, z1)
            glTexCoord2f(1, 1); glVertex3f(-wall_size, 0, z2)
            glTexCoord2f(1, 0); glVertex3f(-wall_size, wall_height, z2)
            glTexCoord2f(0, 0); glVertex3f(-wall_size, wall_height, z1)
        glEnd()
        
        # Right wall (positive X)
        glBegin(GL_QUADS)
        for i in range(10):
            z1 = -wall_size + i * 20
            z2 = -wall_size + (i+1) * 20
            glTexCoord2f(0, 1); glVertex3f(wall_size, 0, z2)
            glTexCoord2f(1, 1); glVertex3f(wall_size, 0, z1)
            glTexCoord2f(1, 0); glVertex3f(wall_size, wall_height, z1)
            glTexCoord2f(0, 0); glVertex3f(wall_size, wall_height, z2)
        glEnd()
        
    def draw_sprite_billboard(self, sprite: Sprite3D):
        """Draw a billboard sprite facing camera"""
        # Calculate angle from sprite to camera for billboard effect
        dx = self.player.x - sprite.x
        dz = self.player.z - sprite.z
        angle = math.atan2(dx, dz)
        
        # Calculate perpendicular vectors for billboard
        sx = sprite.width * math.sin(angle)
        sz = sprite.width * math.cos(angle)
        
        glBegin(GL_QUADS)
        # Bottom-left
        glTexCoord2f(0, 1); glVertex3f(sprite.x - sx, 0, sprite.z - sz)
        # Bottom-right
        glTexCoord2f(1, 1); glVertex3f(sprite.x + sx, 0, sprite.z + sz)
        # Top-right
        glTexCoord2f(1, 0); glVertex3f(sprite.x + sx, sprite.height, sprite.z + sz)
        # Top-left
        glTexCoord2f(0, 0); glVertex3f(sprite.x - sx, sprite.height, sprite.z - sz)
        glEnd()
        
    def draw_trees(self):
        """Draw all trees"""
        glColor4f(1, 1, 1, 1)
        
        # Tree type 1 (only for Earth)
        if self.game_type == 1 and "tree1" in self.texture_loader.textures:
            self.texture_loader.bind("tree1")
            for tree in self.trees1:
                self.draw_sprite_billboard(tree)
                
        # Tree type 2 (only for Death/Hell)
        if self.game_type == 2 and "tree2" in self.texture_loader.textures:
            self.texture_loader.bind("tree2")
            for tree in self.trees2:
                self.draw_sprite_billboard(tree)
                
    def draw_fire_smoke(self):
        """Draw fire and smoke"""
        glColor4f(1, 1, 1, 0.8)
        
        # Smoke (Earth)
        if self.game_type == 1 and "smoke" in self.texture_loader.textures:
            self.texture_loader.bind("smoke")
            for smoke in self.smokes[:FIRESMOKE//2]:
                self.draw_sprite_billboard(smoke)
                
        # Fire (Hell/Death)
        if self.game_type == 2 and "fire" in self.texture_loader.textures:
            self.texture_loader.bind("fire")
            for fire in self.fires[:FIRESMOKE//2]:
                self.draw_sprite_billboard(fire)
                
    def draw_computer(self):
        """Draw the enemy cube"""
        glPushMatrix()
        
        glTranslatef(self.computer.x, self.computer.y, self.computer.z)
        glRotatef(self.computer.rotate_x, 1, 0, 0)
        glRotatef(self.computer.rotate_y, 0, 1, 0)
        glRotatef(self.computer.rotate_z, 0, 0, 1)
        
        size = 8
        
        self.texture_loader.bind("computer")
        glColor4f(1, 1, 1, 1)
        
        # Draw cube with texture on all faces
        glBegin(GL_QUADS)
        
        # Front face (negative Z)
        glTexCoord2f(0, 1); glVertex3f(-size, -size, -size)
        glTexCoord2f(1, 1); glVertex3f(size, -size, -size)
        glTexCoord2f(1, 0); glVertex3f(size, size, -size)
        glTexCoord2f(0, 0); glVertex3f(-size, size, -size)
        
        # Back face (positive Z)
        glTexCoord2f(1, 1); glVertex3f(size, -size, size)
        glTexCoord2f(0, 1); glVertex3f(-size, -size, size)
        glTexCoord2f(0, 0); glVertex3f(-size, size, size)
        glTexCoord2f(1, 0); glVertex3f(size, size, size)
        
        # Left face (negative X)
        glTexCoord2f(1, 1); glVertex3f(-size, -size, size)
        glTexCoord2f(0, 1); glVertex3f(-size, -size, -size)
        glTexCoord2f(0, 0); glVertex3f(-size, size, -size)
        glTexCoord2f(1, 0); glVertex3f(-size, size, size)
        
        # Right face (positive X)
        glTexCoord2f(0, 1); glVertex3f(size, -size, -size)
        glTexCoord2f(1, 1); glVertex3f(size, -size, size)
        glTexCoord2f(1, 0); glVertex3f(size, size, size)
        glTexCoord2f(0, 0); glVertex3f(size, size, -size)
        
        # Top face (positive Y)
        glTexCoord2f(0, 1); glVertex3f(-size, size, -size)
        glTexCoord2f(1, 1); glVertex3f(size, size, -size)
        glTexCoord2f(1, 0); glVertex3f(size, size, size)
        glTexCoord2f(0, 0); glVertex3f(-size, size, size)
        
        # Bottom face (negative Y)
        glTexCoord2f(0, 0); glVertex3f(-size, -size, size)
        glTexCoord2f(1, 0); glVertex3f(size, -size, size)
        glTexCoord2f(1, 1); glVertex3f(size, -size, -size)
        glTexCoord2f(0, 1); glVertex3f(-size, -size, -size)
        
        glEnd()
        glPopMatrix()
        
    def draw_laser(self):
        """Draw laser beam when shooting"""
        if not self.player.fire_now:
            return
            
        glDisable(GL_TEXTURE_2D)
        glColor4f(1.0, 0.2, 0.0, 1.0)
        glLineWidth(4.0)
        
        # Draw laser from camera forward
        glBegin(GL_LINES)
        # Start from player position, slightly in front
        start_x = self.player.x + math.sin(self.player.angle) * 2
        start_z = self.player.z + math.cos(self.player.angle) * 2
        end_x = self.player.x + math.sin(self.player.angle) * 150
        end_z = self.player.z + math.cos(self.player.angle) * 150
        
        glVertex3f(start_x, self.player.y, start_z)
        glVertex3f(end_x, self.player.y, end_z)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        
    def draw_crosshair(self):
        """Draw crosshair on screen"""
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
        
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        size = 20
        gap = 5
        
        color = (1, 0, 0) if self.player.fire_now else (0, 1, 0)
        glColor3f(*color)
        glLineWidth(2)
        
        glBegin(GL_LINES)
        # Horizontal
        glVertex2i(cx - size, cy)
        glVertex2i(cx - gap, cy)
        glVertex2i(cx + gap, cy)
        glVertex2i(cx + size, cy)
        # Vertical
        glVertex2i(cx, cy - size)
        glVertex2i(cx, cy - gap)
        glVertex2i(cx, cy + gap)
        glVertex2i(cx, cy + size)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)
        
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def draw_energy_bars(self):
        """Draw energy bars"""
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_W, SCREEN_H, 0, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_TEXTURE_2D)
        
        bar_width = 200
        bar_height = 25
        margin = 30
        
        # Player energy (bottom left)
        px, py = margin, SCREEN_H - bar_height - margin
        
        # Background
        glColor3f(0.2, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex2i(px, py)
        glVertex2i(px + bar_width, py)
        glVertex2i(px + bar_width, py + bar_height)
        glVertex2i(px, py + bar_height)
        glEnd()
        
        # Energy fill
        pw = int(bar_width * (self.player.energy / self.player.max_energy))
        glColor3f(0, 0.8, 0)
        glBegin(GL_QUADS)
        glVertex2i(px, py)
        glVertex2i(px + pw, py)
        glVertex2i(px + pw, py + bar_height)
        glVertex2i(px, py + bar_height)
        glEnd()
        
        # Border
        glColor3f(1, 1, 1)
        glLineWidth(2)
        glBegin(GL_LINE_LOOP)
        glVertex2i(px, py)
        glVertex2i(px + bar_width, py)
        glVertex2i(px + bar_width, py + bar_height)
        glVertex2i(px, py + bar_height)
        glEnd()
        
        # Computer energy (bottom right)
        cx = SCREEN_W - bar_width - margin
        cy = SCREEN_H - bar_height - margin
        
        glColor3f(0.2, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex2i(cx, cy)
        glVertex2i(cx + bar_width, cy)
        glVertex2i(cx + bar_width, cy + bar_height)
        glVertex2i(cx, cy + bar_height)
        glEnd()
        
        cw = int(bar_width * (self.computer.energy / self.computer.max_energy))
        glColor3f(0.8, 0, 0)
        glBegin(GL_QUADS)
        glVertex2i(cx, cy)
        glVertex2i(cx + cw, cy)
        glVertex2i(cx + cw, cy + bar_height)
        glVertex2i(cx, cy + bar_height)
        glEnd()
        
        glColor3f(1, 1, 1)
        glBegin(GL_LINE_LOOP)
        glVertex2i(cx, cy)
        glVertex2i(cx + bar_width, cy)
        glVertex2i(cx + bar_width, cy + bar_height)
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
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Switch to 2D
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
        glVertex2i(0, 0)
        glVertex2i(SCREEN_W, 0)
        glVertex2i(SCREEN_W, SCREEN_H)
        glVertex2i(0, SCREEN_H)
        glEnd()
        
        # Draw logo
        self.texture_loader.bind("logo")
        if self.texture_loader.get("logo"):
            glColor3f(1, 1, 1)
            glEnable(GL_TEXTURE_2D)
            # Center the logo
            lw, lh = 600, 400
            lx = (SCREEN_W - lw) // 2
            ly = (SCREEN_H - lh) // 2
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
        """Check if player shot hits the computer"""
        dx = self.computer.x - self.player.x
        dz = self.computer.z - self.player.z
        
        distance = math.sqrt(dx*dx + dz*dz)
        
        if distance > 120:
            return False
            
        # Angle to computer
        angle_to_comp = math.atan2(dx, dz)
        
        # Difference from player angle
        angle_diff = angle_to_comp - self.player.angle
        
        # Normalize to -PI to PI
        while angle_diff > PI:
            angle_diff -= 2 * PI
        while angle_diff < -PI:
            angle_diff += 2 * PI
            
        # Hit if within ~8 degrees (wider than before)
        hit_threshold = 0.15
        if abs(angle_diff) < hit_threshold:
            return True
            
        return False
        
    def check_collision(self) -> bool:
        """Check player-computer collision"""
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
        """Handle keyboard input - LIKE ORIGINAL VB6"""
        keys = pygame.key.get_pressed()
        
        if self.in_menu:
            return
            
        if self.game_over:
            if keys[K_n]:
                self.game_type = 1
                self.player.wins = 0
                self.start_game(1)
            return
            
        # === MOVEMENT - Like original VB6 ===
        # Up/Down = Forward/Backward
        if keys[K_UP]:
            # Move forward in look direction
            self.player.x += self.player.step * math.sin(self.player.angle)
            self.player.z += self.player.step * math.cos(self.player.angle)
            
        if keys[K_DOWN]:
            # Move backward
            self.player.x -= self.player.step * math.sin(self.player.angle)
            self.player.z -= self.player.step * math.cos(self.player.angle)
            
        # Left/Right = Rotate (like original delta angle)
        if keys[K_LEFT]:
            self.player.angle -= self.player.rotate_speed
            
        if keys[K_RIGHT]:
            self.player.angle += self.player.rotate_speed
            
        # Normalize angle
        while self.player.angle < 0:
            self.player.angle += 2 * PI
        while self.player.angle >= 2 * PI:
            self.player.angle -= 2 * PI
            
        # Shooting - SPACE key
        shoot_pressed = keys[K_SPACE]
        if shoot_pressed and not self.player.last_shoot:
            # Single shot
            self.player.fire_now = True
            self.sound.play_sound("laser")
            
            if self.check_hit():
                self.computer.energy -= 8
                if self.computer.energy <= 0:
                    self.player.wins += 1
                    self.sound.play_sound("killcomp")
                    # Switch area
                    self.game_type = 2 if self.game_type == 1 else 1
                    self.start_game(self.game_type)
        else:
            self.player.fire_now = False
            
        self.player.last_shoot = shoot_pressed
        
        # Wall boundaries
        limit = POLE - 8
        self.player.x = max(-limit, min(limit, self.player.x))
        self.player.z = max(-limit, min(limit, self.player.z))
        
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
        
    def render(self):
        """Render the scene"""
        if self.in_menu:
            self.draw_menu()
            pygame.display.flip()
            return
            
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Set up camera
        glLoadIdentity()
        
        # Camera looks in direction of player.angle
        # In original: angle 0 = looking at +Z (forward into arena)
        look_dist = 100
        look_x = self.player.x + math.sin(self.player.angle) * look_dist
        look_z = self.player.z + math.cos(self.player.angle) * look_dist
        
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
        
        # Draw HUD
        self.draw_hud()
        
        pygame.display.flip()
        
    def run(self):
        """Main game loop"""
        print("\n" + "="*50)
        print("DOOM 4D - Python Remastered")
        print("(c) 2004 Denis Astahov")
        print("="*50)
        print("\nControls:")
        print("  1 or E - Start Earth level")
        print("  2 or H - Start Hell level")
        print("  UP/DOWN - Move forward/backward")
        print("  LEFT/RIGHT - Rotate")
        print("  SPACE - Shoot")
        print("  F1-F7 - Play music")
        print("  F12 - Teleport to other level")
        print("  ESC - Exit/Menu")
        print("\nStarting...\n")
        
        while self.running:
            dt = self.clock.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        if self.game_over:
                            self.running = False
                        elif self.in_menu:
                            self.running = False
                        else:
                            self.game_over = True
                            
                    # Menu controls
                    if self.in_menu:
                        if event.key in [K_1, K_e, K_RETURN]:
                            self.sound.play_sound("select")
                            self.start_game(1)
                        elif event.key in [K_2, K_h]:
                            self.sound.play_sound("select")
                            self.start_game(2)
                            
                    # In-game controls (key down events)
                    if not self.in_menu and not self.game_over:
                        # Music
                        if event.key in [K_F1, K_F2, K_F3, K_F4, K_F5, K_F6, K_F7]:
                            num = event.key - K_F1 + 1
                            self.sound.play_music(num)
                            
                        # Teleport
                        if event.key == K_F12:
                            self.game_type = 2 if self.game_type == 1 else 1
                            self.sound.play_sound("teleport")
                            self.start_game(self.game_type)
                            
            # Handle continuous input
            self.handle_input()
            
            # Update
            self.update(dt)
            
            # Render
            self.render()
            
        pygame.quit()


if __name__ == "__main__":
    game = Doom4D()
    game.run()
