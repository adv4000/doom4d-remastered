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
from pathlib import Path
from typing import List, Dict

# ============== CONSTANTS (from original VB6) ==============
COMPSTEP = 100      # Number of Computer STEPS
TREE_MAX = 40       # Number of Trees
FIRESMOKE = 40      # Number of Fire/Smoke
PI = 3.14159265358979
RADIANS = PI / 180

# Screen settings
SCREEN_W = 1024
SCREEN_H = 768

# Window title
TITLE = "DOOM 4D - Remastered (c) 2004 Denis Astahov"


# ============== TEXTURE LOADER ==============
class TextureLoader:
    """Load and manage OpenGL textures"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.textures: Dict[str, int] = {}
        
    def load_texture(self, name: str, relative_path: str) -> bool:
        """Load a texture from file"""
        full_path = self.base_path / relative_path
        
        # Try different extensions
        for ext in ['', '.bmp', '.BMP', '.jpg', '.JPG', '.jpeg', '.JPEG', '.png', '.PNG']:
            test_path = Path(str(full_path) + ext) if ext else full_path
            if test_path.exists():
                full_path = test_path
                break
        else:
            return False
            
        try:
            surface = pygame.image.load(str(full_path))
            
            # Flip vertically for OpenGL (BMP stores top-to-bottom)
            surface = pygame.transform.flip(surface, False, True)
            
            # Convert to RGBA
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
            print(f"Loaded texture: {name} ({width}x{height})")
            return True
            
        except Exception as e:
            print(f"Error loading {relative_path}: {e}")
            return False
            
    def get(self, name: str) -> int:
        return self.textures.get(name, 0)
        
    def bind(self, name: str):
        if name in self.textures:
            glBindTexture(GL_TEXTURE_2D, self.textures[name])
        else:
            glBindTexture(GL_TEXTURE_2D, 0)


# ============== SOUND MANAGER ==============
class SoundManager:
    """Handles sound playback"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.music_sounds: Dict[int, pygame.mixer.Sound] = {}  # For music tracks
        self.current_music = None
        
    def load_sound(self, name: str, relative_path: str) -> bool:
        full_path = self.base_path / relative_path
        
        for ext in ['', '.wav', '.WAV', '.mp3', '.MP3']:
            test_path = Path(str(full_path) + ext) if ext else full_path
            if test_path.exists():
                try:
                    self.sounds[name] = pygame.mixer.Sound(str(test_path))
                    print(f"Loaded sound: {name}")
                    return True
                except Exception as e:
                    print(f"Error loading sound {relative_path}: {e}")
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
                        print(f"Loaded music track {num}: {f.name}")
                    except Exception as e:
                        print(f"Could not load music {f.name}: {e}")
                    
    def play_sound(self, name: str):
        if name in self.sounds:
            self.sounds[name].play()
            
    def play_music(self, num: int):
        if num in self.music_sounds:
            try:
                # Stop current music
                if self.current_music and self.current_music in self.music_sounds:
                    self.music_sounds[self.current_music].stop()
                # Play new track on loop
                self.music_sounds[num].play(-1)
                self.current_music = num
                print(f"Playing music track {num}")
            except Exception as e:
                print(f"Error playing music: {e}")


# ============== 3D SPRITE ==============
class Sprite3D:
    """3D Billboard sprite"""
    
    def __init__(self, x: float, z: float, height: float, width: float):
        self.x = x
        self.z = z
        self.height = height
        self.width = width


# ============== PLAYER ==============
class Player:
    """Player/Camera"""
    
    def __init__(self):
        self.x = 0.0
        self.y = 10.0
        self.z = -180.0     # Start far back
        self.angle = 0.0    # 0 = looking forward into arena (+Z direction)
        
        self.step = 2.0
        self.rotate_speed = 0.03
        
        self.energy = 100
        self.max_energy = 100
        self.wins = 0
        
        self.fire_now = False
        self.last_shoot = False


# ============== COMPUTER ==============
class Computer:
    """AI enemy cube"""
    
    def __init__(self):
        self.x = 0.0
        self.y = 10.0
        self.z = 0.0
        
        self.new_x = 0
        self.new_z = 0
        
        self.dx = 0.0
        self.dz = 0.0
        self.step_count = COMPSTEP
        
        self.energy = 100
        self.max_energy = 100
        
        self.rotate_x = 0.0
        self.rotate_y = 0.0
        self.rotate_z = 0.0
        
    def spawn_target(self):
        self.new_x = random.randint(-150, 150)
        self.new_z = random.randint(-150, 150)
        self.dx = (self.new_x - self.x) / COMPSTEP
        self.dz = (self.new_z - self.z) / COMPSTEP
        self.step_count = 0
        
    def update(self):
        if self.step_count >= COMPSTEP:
            self.spawn_target()
            
        self.x += self.dx
        self.z += self.dz
        self.step_count += 1
        
        # Wall boundaries
        self.x = max(-180, min(180, self.x))
        self.z = max(-180, min(180, self.z))
        
        self.rotate_x = (self.rotate_x + 1) % 360
        self.rotate_y = (self.rotate_y + 5) % 360
        self.rotate_z = (self.rotate_z + 1) % 360


# ============== MAIN GAME ==============
class Doom4D:
    """Main game class"""
    
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        self.screen = pygame.display.set_mode(
            (SCREEN_W, SCREEN_H), 
            DOUBLEBUF | OPENGL
        )
        pygame.display.set_caption(TITLE)
        
        self.running = True
        self.game_type = 1  # 1 = Earth, 2 = Hell
        self.in_menu = True
        self.game_over = False
        
        # Arena size (POLE from original = 200, so -200 to 200)
        self.arena_size = 200
        
        self.player = Player()
        self.computer = Computer()
        
        self.trees1: List[Sprite3D] = []
        self.trees2: List[Sprite3D] = []
        self.smokes: List[Sprite3D] = []
        self.fires: List[Sprite3D] = []
        
        self.clock = pygame.time.Clock()
        self.play_time = 0
        self.time_ms = 0
        
        self.init_opengl()
        
        self.base_path = Path(__file__).parent
        self.texture_loader = TextureLoader(self.base_path / "Image")
        self.sound = SoundManager(self.base_path)
        
        self.load_menu_textures()
        self.load_sounds()
        
    def init_opengl(self):
        """Initialize OpenGL"""
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
        
    def load_menu_textures(self):
        """Load menu textures"""
        self.texture_loader.load_texture("logo", "IntroD4D")
        
    def load_game_textures(self):
        """Load ALL game textures (both areas)"""
        print(f"\n=== Loading ALL textures ===")
        
        area = "Earth" if self.game_type == 1 else "Death"
        
        # Ground for current area
        self.texture_loader.load_texture("ground", f"{area}/Ground")
        
        # Walls for current area
        self.texture_loader.load_texture("wall1", f"{area}/Stena1")
        self.texture_loader.load_texture("wall2", f"{area}/Stena2")
        
        # Sky
        self.texture_loader.load_texture("sky", "Earth/Nebo")
        
        # Load BOTH tree textures (Tree1 from Earth, Tree2 from Death)
        self.texture_loader.load_texture("tree1", "Earth/Tree1")
        self.texture_loader.load_texture("tree2", "Death/Tree2")
            
        # Load BOTH fire and smoke textures
        self.texture_loader.load_texture("smoke", "Earth/Smoke")
        self.texture_loader.load_texture("fire", "Death/Faire")
            
        # Computer cube
        self.texture_loader.load_texture("computer", "CompKub")
        
        # Intro for current area
        self.texture_loader.load_texture("intro", f"{area}/Intro1")
        
    def load_sounds(self):
        """Load sounds"""
        print("\n=== Loading sounds ===")
        self.sound.load_sound("select", "Sound/Select")
        self.sound.load_sound("start", "Sound/Start")
        self.sound.load_sound("laser", "Sound/Laser")
        self.sound.load_sound("pain", "Sound/Pain")
        self.sound.load_sound("dead", "Sound/Dead")
        self.sound.load_sound("killcomp", "Sound/Killcomp")
        self.sound.load_sound("teleport", "Sound/Teleport")
        self.sound.load_music_list("Music")
        
    def init_geometry(self):
        """Initialize trees, fire, smoke"""
        self.trees1 = []
        self.trees2 = []
        self.smokes = []
        self.fires = []
        
        random.seed()
        
        # Trees - spread across arena
        for i in range(TREE_MAX):
            x = random.randint(-180, 180)
            z = random.randint(-180, 180)
            # Avoid center (where computer spawns)
            if abs(x) < 30 and abs(z) < 30:
                x += 50 if x >= 0 else -50
            self.trees1.append(Sprite3D(x, z, height=25, width=5))
            
            x = random.randint(-180, 180)
            z = random.randint(-180, 180)
            if abs(x) < 30 and abs(z) < 30:
                x += 50 if x >= 0 else -50
            self.trees2.append(Sprite3D(x, z, height=18, width=8))
            
        # Fire/Smoke
        for i in range(FIRESMOKE):
            x = random.randint(-190, 190)
            z = random.randint(-190, 190)
            if abs(x) < 40 and abs(z) < 40:
                x += 60 if x >= 0 else -60
            self.smokes.append(Sprite3D(x, z, height=6, width=3))
            self.fires.append(Sprite3D(x, z, height=6, width=3))
            
    def start_game(self, game_type: int):
        """Start new game"""
        self.game_type = game_type
        self.player = Player()
        self.computer = Computer()
        self.play_time = 0
        self.time_ms = 0
        self.game_over = False
        self.in_menu = False
        
        # Reload textures
        self.texture_loader = TextureLoader(self.base_path / "Image")
        self.load_game_textures()
        
        self.init_geometry()
        
        # Sky color
        if self.game_type == 1:
            glClearColor(0.4, 0.6, 0.9, 1.0)
        else:
            glClearColor(0.3, 0.1, 0.1, 1.0)
            
        self.sound.play_sound("start")
        print(f"\nGame started! Area: {'Earth' if game_type == 1 else 'Hell'}")
        print(f"Arena size: -{self.arena_size} to {self.arena_size}")
        
    def draw_ground(self):
        """Draw ground"""
        self.texture_loader.bind("ground")
        
        size = self.arena_size
        glColor4f(1, 1, 1, 1)
        
        # Tiled ground
        tiles = 4
        tile_size = size * 2 / tiles
        
        glBegin(GL_QUADS)
        for i in range(tiles):
            for j in range(tiles):
                x1 = -size + i * tile_size
                z1 = -size + j * tile_size
                x2 = x1 + tile_size
                z2 = z1 + tile_size
                
                glTexCoord2f(0, 0); glVertex3f(x1, 0, z1)
                glTexCoord2f(1, 0); glVertex3f(x2, 0, z1)
                glTexCoord2f(1, 1); glVertex3f(x2, 0, z2)
                glTexCoord2f(0, 1); glVertex3f(x1, 0, z2)
        glEnd()
        
    def draw_sky(self):
        """Draw sky dome"""
        self.texture_loader.bind("sky")
        
        dist = 500
        height = 250
        
        glColor4f(1, 1, 1, 1)
        
        # Sky box
        glBegin(GL_QUADS)
        # Front
        glTexCoord2f(0, 1); glVertex3f(-dist, 0, -dist)
        glTexCoord2f(1, 1); glVertex3f(dist, 0, -dist)
        glTexCoord2f(1, 0); glVertex3f(dist, height, -dist)
        glTexCoord2f(0, 0); glVertex3f(-dist, height, -dist)
        # Back
        glTexCoord2f(0, 1); glVertex3f(dist, 0, dist)
        glTexCoord2f(1, 1); glVertex3f(-dist, 0, dist)
        glTexCoord2f(1, 0); glVertex3f(-dist, height, dist)
        glTexCoord2f(0, 0); glVertex3f(dist, height, dist)
        # Left
        glTexCoord2f(0, 1); glVertex3f(-dist, 0, dist)
        glTexCoord2f(1, 1); glVertex3f(-dist, 0, -dist)
        glTexCoord2f(1, 0); glVertex3f(-dist, height, -dist)
        glTexCoord2f(0, 0); glVertex3f(-dist, height, dist)
        # Right
        glTexCoord2f(0, 1); glVertex3f(dist, 0, -dist)
        glTexCoord2f(1, 1); glVertex3f(dist, 0, dist)
        glTexCoord2f(1, 0); glVertex3f(dist, height, dist)
        glTexCoord2f(0, 0); glVertex3f(dist, height, -dist)
        # Top
        glTexCoord2f(0, 0); glVertex3f(-dist, height, -dist)
        glTexCoord2f(1, 0); glVertex3f(dist, height, -dist)
        glTexCoord2f(1, 1); glVertex3f(dist, height, dist)
        glTexCoord2f(0, 1); glVertex3f(-dist, height, dist)
        glEnd()
        
    def draw_walls(self):
        """Draw walls"""
        wall_height = 80
        wall_size = self.arena_size
        
        glColor4f(1, 1, 1, 1)
        
        # Back wall (+Z)
        self.texture_loader.bind("wall1")
        glBegin(GL_QUADS)
        for i in range(10):
            x1 = -wall_size + i * 40
            x2 = -wall_size + (i+1) * 40
            # Fix: swap Y coordinates to flip texture vertically
            glTexCoord2f(0, 1); glVertex3f(x1, 0, wall_size)
            glTexCoord2f(1, 1); glVertex3f(x2, 0, wall_size)
            glTexCoord2f(1, 0); glVertex3f(x2, wall_height, wall_size)
            glTexCoord2f(0, 0); glVertex3f(x1, wall_height, wall_size)
        glEnd()
        
        # Front wall (-Z)
        glBegin(GL_QUADS)
        for i in range(10):
            x1 = -wall_size + i * 40
            x2 = -wall_size + (i+1) * 40
            glTexCoord2f(0, 1); glVertex3f(x2, 0, -wall_size)
            glTexCoord2f(1, 1); glVertex3f(x1, 0, -wall_size)
            glTexCoord2f(1, 0); glVertex3f(x1, wall_height, -wall_size)
            glTexCoord2f(0, 0); glVertex3f(x2, wall_height, -wall_size)
        glEnd()
        
        # Left wall (-X)
        self.texture_loader.bind("wall2")
        glBegin(GL_QUADS)
        for i in range(10):
            z1 = -wall_size + i * 40
            z2 = -wall_size + (i+1) * 40
            glTexCoord2f(0, 1); glVertex3f(-wall_size, 0, z1)
            glTexCoord2f(1, 1); glVertex3f(-wall_size, 0, z2)
            glTexCoord2f(1, 0); glVertex3f(-wall_size, wall_height, z2)
            glTexCoord2f(0, 0); glVertex3f(-wall_size, wall_height, z1)
        glEnd()
        
        # Right wall (+X)
        glBegin(GL_QUADS)
        for i in range(10):
            z1 = -wall_size + i * 40
            z2 = -wall_size + (i+1) * 40
            glTexCoord2f(0, 1); glVertex3f(wall_size, 0, z2)
            glTexCoord2f(1, 1); glVertex3f(wall_size, 0, z1)
            glTexCoord2f(1, 0); glVertex3f(wall_size, wall_height, z1)
            glTexCoord2f(0, 0); glVertex3f(wall_size, wall_height, z2)
        glEnd()
        
    def draw_sprite_billboard(self, sprite: Sprite3D):
        """Draw billboard sprite"""
        dx = self.player.x - sprite.x
        dz = self.player.z - sprite.z
        angle = math.atan2(dx, dz)
        
        sx = sprite.width * math.sin(angle)
        sz = sprite.width * math.cos(angle)
        
        glBegin(GL_QUADS)
        # Fix: swap V coordinates to flip texture vertically
        glTexCoord2f(0, 1); glVertex3f(sprite.x - sx, 0, sprite.z - sz)
        glTexCoord2f(1, 1); glVertex3f(sprite.x + sx, 0, sprite.z + sz)
        glTexCoord2f(1, 0); glVertex3f(sprite.x + sx, sprite.height, sprite.z + sz)
        glTexCoord2f(0, 0); glVertex3f(sprite.x - sx, sprite.height, sprite.z - sz)
        glEnd()
        
    def draw_trees(self):
        """Draw trees"""
        glColor4f(1, 1, 1, 1)
        
        # Debug info
        t1_loaded = "tree1" in self.texture_loader.textures
        t2_loaded = "tree2" in self.texture_loader.textures
        print(f"Drawing trees - tree1:{t1_loaded}, tree2:{t2_loaded}, count:{len(self.trees1)}") if not hasattr(self, '_tree_debug') else None
        self._tree_debug = True
        
        # Type 1 trees (taller, narrower)
        if "tree1" in self.texture_loader.textures:
            self.texture_loader.bind("tree1")
            for tree in self.trees1:
                self.draw_sprite_billboard(tree)
        # Type 2 trees (shorter, wider)
        if "tree2" in self.texture_loader.textures:
            self.texture_loader.bind("tree2")
        for tree in self.trees2:
            self.draw_sprite_billboard(tree)
                    
    def draw_fire_smoke(self):
        """Draw fire and smoke"""
        glColor4f(1, 1, 1, 0.9)
        
        # Draw smoke (mainly for Earth, but available everywhere)
        if "smoke" in self.texture_loader.textures:
            self.texture_loader.bind("smoke")
            for smoke in self.smokes[:25]:
                self.draw_sprite_billboard(smoke)
        
        # Draw fire (mainly for Hell, but available everywhere)
        if "fire" in self.texture_loader.textures:
            self.texture_loader.bind("fire")
            for fire in self.fires[:25]:
                self.draw_sprite_billboard(fire)
                    
    def draw_computer(self):
        """Draw enemy cube"""
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
        """Draw laser"""
        if not self.player.fire_now:
            return
            
        glDisable(GL_TEXTURE_2D)
        glColor4f(1.0, 0.3, 0.0, 1.0)
        glLineWidth(4.0)
        
        start_x = self.player.x - math.sin(self.player.angle) * 5
        start_z = self.player.z + math.cos(self.player.angle) * 5
        end_x = self.player.x - math.sin(self.player.angle) * 200
        end_z = self.player.z + math.cos(self.player.angle) * 200
        
        glBegin(GL_LINES)
        glVertex3f(start_x, self.player.y, start_z)
        glVertex3f(end_x, self.player.y, end_z)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        
    def draw_crosshair(self):
        """Draw crosshair"""
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
        glVertex2i(cx - 25, cy)
        glVertex2i(cx - 8, cy)
        glVertex2i(cx + 8, cy)
        glVertex2i(cx + 25, cy)
        glVertex2i(cx, cy - 25)
        glVertex2i(cx, cy - 8)
        glVertex2i(cx, cy + 8)
        glVertex2i(cx, cy + 25)
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
        
        bar_w, bar_h = 250, 30
        margin = 40
        
        # Player energy (bottom left)
        px, py = margin, SCREEN_H - bar_h - margin
        
        glColor3f(0.2, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex2i(px, py)
        glVertex2i(px + bar_w, py)
        glVertex2i(px + bar_w, py + bar_h)
        glVertex2i(px, py + bar_h)
        glEnd()
        
        pw = int(bar_w * (self.player.energy / self.player.max_energy))
        glColor3f(0, 0.8, 0)
        glBegin(GL_QUADS)
        glVertex2i(px, py)
        glVertex2i(px + pw, py)
        glVertex2i(px + pw, py + bar_h)
        glVertex2i(px, py + bar_h)
        glEnd()
        
        glColor3f(1, 1, 1)
        glLineWidth(2)
        glBegin(GL_LINE_LOOP)
        glVertex2i(px, py)
        glVertex2i(px + bar_w, py)
        glVertex2i(px + bar_w, py + bar_h)
        glVertex2i(px, py + bar_h)
        glEnd()
        
        # Computer energy (bottom right)
        cx = SCREEN_W - bar_w - margin
        cy = SCREEN_H - bar_h - margin
        
        glColor3f(0.2, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex2i(cx, cy)
        glVertex2i(cx + bar_w, cy)
        glVertex2i(cx + bar_w, cy + bar_h)
        glVertex2i(cx, cy + bar_h)
        glEnd()
        
        cw = int(bar_w * (self.computer.energy / self.computer.max_energy))
        glColor3f(0.8, 0, 0)
        glBegin(GL_QUADS)
        glVertex2i(cx, cy)
        glVertex2i(cx + cw, cy)
        glVertex2i(cx + cw, cy + bar_h)
        glVertex2i(cx, cy + bar_h)
        glEnd()
        
        glColor3f(1, 1, 1)
        glBegin(GL_LINE_LOOP)
        glVertex2i(cx, cy)
        glVertex2i(cx + bar_w, cy)
        glVertex2i(cx + bar_w, cy + bar_h)
        glVertex2i(cx, cy + bar_h)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)
        
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def draw_hud(self):
        """Draw HUD"""
        self.draw_crosshair()
        self.draw_energy_bars()
        
    def draw_menu(self):
        """Draw menu"""
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
        glVertex2i(0, 0)
        glVertex2i(SCREEN_W, 0)
        glVertex2i(SCREEN_W, SCREEN_H)
        glVertex2i(0, SCREEN_H)
        glEnd()
        
        # Logo
        self.texture_loader.bind("logo")
        if self.texture_loader.get("logo"):
            glColor3f(1, 1, 1)
            glEnable(GL_TEXTURE_2D)
            lw, lh = 700, 450
            lx = (SCREEN_W - lw) // 2
            ly = (SCREEN_H - lh) // 2
            glBegin(GL_QUADS)
            glTexCoord2f(0, 1); glVertex2i(lx, ly)
            glTexCoord2f(1, 1); glVertex2i(lx + lw, ly)
            glTexCoord2f(1, 0); glVertex2i(lx + lw, ly + lh)
            glTexCoord2f(0, 0); glVertex2i(lx, ly + lh)
            glEnd()
        
        glEnable(GL_DEPTH_TEST)
        
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def check_hit(self) -> bool:
        """Check if shot hits computer"""
        dx = self.computer.x - self.player.x
        dz = self.computer.z - self.player.z
        
        dist = math.sqrt(dx*dx + dz*dz)
        if dist > 180:
            return False
            
        # Angle to computer
        angle_to = math.atan2(-dx, dz)  # Matched to new coordinate system
        diff = angle_to - self.player.angle
        
        while diff > PI: diff -= 2*PI
        while diff < -PI: diff += 2*PI
        
        return abs(diff) < 0.12
        
    def check_collision(self) -> bool:
        """Check collision"""
        dx = self.computer.x - self.player.x
        dz = self.computer.z - self.player.z
        dist = math.sqrt(dx*dx + dz*dz)
        
        if dist < 20:
            self.player.energy -= 1
            if self.player.energy <= 0:
                self.player.energy = 0
                self.game_over = True
                self.sound.play_sound("dead")
            return True
        return False
        
    def handle_input(self):
        """Handle input - FIXED controls"""
        keys = pygame.key.get_pressed()
        
        if self.in_menu or self.game_over:
            return
            
        # === Rotation ===
        # LEFT decreases angle (rotates left), RIGHT increases angle (rotates right)
        if keys[K_LEFT]:
            self.player.angle -= self.player.rotate_speed
        if keys[K_RIGHT]:
            self.player.angle += self.player.rotate_speed
            
        # Normalize
        while self.player.angle < 0: self.player.angle += 2*PI
        while self.player.angle >= 2*PI: self.player.angle -= 2*PI
            
        # Forward/Backward
        if keys[K_UP]:
            self.player.x -= self.player.step * math.sin(self.player.angle)  # Negative
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
                self.computer.energy -= 10
                if self.computer.energy <= 0:
                    self.player.wins += 1
                    self.sound.play_sound("killcomp")
                    self.game_type = 2 if self.game_type == 1 else 1
                    self.start_game(self.game_type)
        else:
            self.player.fire_now = False
        self.player.last_shoot = shoot
        
        # Boundaries
        limit = self.arena_size - 10
        self.player.x = max(-limit, min(limit, self.player.x))
        self.player.z = max(-limit, min(limit, self.player.z))
        
    def update(self, dt: int):
        """Update game"""
        if self.in_menu or self.game_over:
            return
            
        self.time_ms += dt
        if self.time_ms >= 1000:
            self.time_ms -= 1000
            self.play_time += 1
            
        self.computer.update()
        self.check_collision()
        
    def render(self):
        """Render"""
        if self.in_menu:
            self.draw_menu()
            pygame.display.flip()
            return
            
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glLoadIdentity()
        
        # Camera look direction - angle increases = rotates right
        look_x = self.player.x - math.sin(self.player.angle) * 100  # Negative sin
        look_z = self.player.z + math.cos(self.player.angle) * 100
        
        gluLookAt(
            self.player.x, self.player.y, self.player.z,
            look_x, self.player.y, look_z,
            0, 1, 0
        )
        
        self.draw_sky()
        self.draw_ground()
        self.draw_walls()
        self.draw_trees()
        self.draw_fire_smoke()
        self.draw_computer()
        self.draw_laser()
        self.draw_hud()
        
        pygame.display.flip()
        
    def run(self):
        """Main loop"""
        print("\n" + "="*50)
        print("DOOM 4D - Python Remastered")
        print("(c) 2004 Denis Astahov")
        print("="*50)
        print("\nControls:")
        print("  1/E - Start Earth")
        print("  2/H - Start Hell")
        print("  UP/DOWN - Move")
        print("  LEFT/RIGHT - Rotate")
        print("  SPACE - Shoot")
        print("  F1-F7 - Music")
        print("  F12 - Teleport")
        print("  ESC - Exit")
        
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
                            
            self.handle_input()
            self.update(dt)
            self.render()
            
        pygame.quit()


if __name__ == "__main__":
    game = Doom4D()
    game.run()
