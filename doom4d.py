#!/usr/bin/env python3
"""
DOOM 4D - Python Remastered with PyOpenGL
Originally created by Denis Astahov (ADV-IT) in 2004
Visual Basic 6 + DirectX 7 -> Python + Pygame + PyOpenGL

Bachelor Degree Project - Score: 95/100
Repository: https://github.com/adv4000/doom4d-remastered
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

import math
import random
from pathlib import Path
from typing import List, Dict, Tuple

# ==================== CONSTANTS (from original VB6) ====================
COMPSTEP = 100       # Number of Computer's STEPS in one Direction Movement
TREE_MAX = 40        # Counter of Trees -1 My FOREST :)
FIRESMOKE = 40       # Counter of maximum Fire and Smoke Animations -1

PI = 3.14159265358979
Radians = PI / 180.0
POLE = 200           # Size of Area from Center to WALLs

SCREEN_W = 1920
SCREEN_H = 1080
TITLE = "DOOM 4D - Remastered (c) 2004 Denis Astahov"


# ==================== TEXTURE LOADER ====================
class TextureLoader:
    """Load and manage OpenGL textures"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.textures: Dict[str, int] = {}
        
    def make_transparent(self, surface: pygame.Surface) -> pygame.Surface:
        """Convert black pixels to transparent (color key from VB6)"""
        # Fast method: use pygame's colorkey
        surface = surface.convert()
        surface.set_colorkey((0, 0, 0))  # Black = transparent
        
        # Create surface with alpha
        new_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        new_surface.blit(surface, (0, 0))
        
        return new_surface
        
    def load_texture(self, name: str, relative_path: str, with_transparency: bool = False) -> bool:
        """Load texture from file"""
        full_path = self.base_path / relative_path
        
        # Try different extensions
        for ext in ['', '.bmp', '.BMP', '.jpg', '.JPG', '.jpeg', '.JPEG', '.png', '.PNG']:
            test_path = Path(str(full_path) + ext) if ext else full_path
            if test_path.exists():
                full_path = test_path
                break
        else:
            print(f"Texture not found: {relative_path}")
            return False
            
        try:
            print(f"Loading {name} from {full_path.name}...")
            surface = pygame.image.load(str(full_path))
            
            # Apply transparency only for sprites/walls (not for floor, sky, computer)
            if with_transparency:
                surface = self.make_transparent(surface)
            
            # Flip for OpenGL coordinate system
            surface = pygame.transform.flip(surface, False, True)
            data = pygame.image.tostring(surface, "RGBA", True)
            width, height = surface.get_size()
            
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            
            # Tell OpenGL to handle alpha properly
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_PRIORITY, 1.0)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            
            self.textures[name] = texture_id
            print(f"Loaded: {name} ({width}x{height})")
            return True
        except Exception as e:
            print(f"Error loading {relative_path}: {e}")
            return False
            
    def get(self, name: str) -> int:
        """Get texture ID"""
        return self.textures.get(name, 0)
        
    def bind(self, name: str):
        """Bind texture for rendering"""
        if name in self.textures:
            glBindTexture(GL_TEXTURE_2D, self.textures[name])
        else:
            glBindTexture(GL_TEXTURE_2D, 0)


# ==================== SOUND MANAGER ====================
class SoundManager:
    """Handle sound and music playback"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.music_sounds: Dict[int, pygame.mixer.Sound] = {}
        self.current_music = None
        
    def load_sound(self, name: str, relative_path: str) -> bool:
        """Load sound effect"""
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
        """Load all music tracks"""
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
        """Play sound effect"""
        if name in self.sounds:
            self.sounds[name].play()
            
    def play_music(self, num: int):
        """Play music track on loop"""
        if num in self.music_sounds:
            try:
                if self.current_music and self.current_music in self.music_sounds:
                    self.music_sounds[self.current_music].stop()
                self.music_sounds[num].play(-1)
                self.current_music = num
                print(f"Playing music track {num}")
            except Exception as e:
                print(f"Error playing music: {e}")


# ==================== SPRITE 3D ====================
class Sprite3D:
    """Cross-shaped 3D sprite (4 faces in + pattern)"""
    
    def __init__(self, x: float, z: float, height: float, width: float):
        self.x = x
        self.z = z
        self.height = height
        self.width = width


# ==================== PLAYER ====================
class Player:
    """Player/Camera controller"""
    
    def __init__(self):
        # Camera position (VecCamLok in VB6)
        self.x = 0.0
        self.y = 6.0      # Constant height
        self.z = -12.0    # Start position
        
        # View parameters
        self.angle = 0.0  # alfa in VB6 (angle in radians)
        
        # Movement parameters
        self.step = 0.5001
        self.rotate_speed = 0.8 * Radians  # delta in VB6
        
        # Game stats
        self.energy = 100
        self.max_energy = 100
        self.wins = 0
        
        # Shooting
        self.fire_now = False
        self.last_shoot = False


# ==================== COMPUTER ====================
class Computer:
    """Computer enemy cube"""
    
    def __init__(self):
        self.x = 0.0
        self.y = 4.0
        self.z = 0.0
        
        self.target_x = 0.0
        self.target_z = 0.0
        self.dx = 0.0
        self.dz = 0.0
        self.step_count = COMPSTEP
        
        self.energy = 100
        self.max_energy = 100
        
        # Rotation angles
        self.rotate_x = 0.0
        self.rotate_y = 0.0
        self.rotate_z = 0.0
        
    def spawn_target(self):
        """Set new random target position"""
        self.target_x = random.randint(-85, 85)
        self.target_z = random.randint(-85, 85)
        self.dx = (self.target_x - self.x) / COMPSTEP
        self.dz = (self.target_z - self.z) / COMPSTEP
        self.step_count = 0
        
    def update(self):
        """Update computer position"""
        if self.step_count >= COMPSTEP:
            self.spawn_target()
            
        self.x += self.dx
        self.z += self.dz
        self.step_count += 1
        
        # Keep in bounds
        self.x = max(-90, min(90, self.x))
        self.z = max(-90, min(90, self.z))
        
        # Update rotation
        self.rotate_x = (self.rotate_x + 1) % 360
        self.rotate_y = (self.rotate_y + 4) % 360
        self.rotate_z = (self.rotate_z + 1) % 360


# ==================== MAIN GAME ====================
class Doom4D:
    """Main game class"""
    
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), DOUBLEBUF | OPENGL | FULLSCREEN)
        pygame.display.set_caption(TITLE)
        
        self.running = True
        self.game_type = 1  # 1=Earth, 2=Hell
        self.in_menu = True
        self.game_over = False
        
        # Intro animation state
        self.intro_stage = 0
        self.intro_timer = 0
        self.intro_zoom = 0.0  # Start at 0 (full screen), increase to 80 (shrink)
        self.intro_running = True
        
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
        
        # Zoom factor (from original: zzz = POLE / 100)
        self.zoom = POLE / 100  # = 2.0
        
        # Rotating floor (NIZZ) angle
        self.nizz_angle = 0.0
        
        # Fire/Smoke animation
        self.cel_x = 0
        self.cel_y = 0
        self.frame_x = 5  # 5 frames horizontally
        self.frame_y = 4  # 4 frames vertically
        self.cel_width = 32
        self.cel_height = 64
        self.anim_timer = 0
        self.anim_delay = 40  # 40ms between frames
        
        # Fog control
        self.fog_enabled = False
        self.fog_color = (1.0, 1.0, 1.0, 1.0)  # White
        
        # Initialize OpenGL
        self.init_opengl()
        
        # Load resources
        self.base_path = Path(__file__).parent
        self.texture_loader = TextureLoader(self.base_path / "Image")
        self.sound = SoundManager(self.base_path)
        
        self.load_all_textures()
        self.load_sounds()
        
        # Start intro music (from original VB6: PlayMusic in DemonstLoop)
        self.sound.play_music(1)
        
        # Play intro sound at start
        self.sound.play_sound("intro0")
        
    def init_opengl(self):
        """Initialize OpenGL settings"""
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Note: No alpha test - use blending only for transparency
        
        # Perspective projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(90, SCREEN_W / SCREEN_H, 1.0, 2000.0)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Background color
        glClearColor(0.0, 0.0, 0.2, 1.0)
        
    def load_all_textures(self):
        """Load all textures from both Earth and Death areas"""
        print("\n=== Loading ALL textures ===")
        
        # Ground (no transparency)
        self.texture_loader.load_texture("ground_earth", "Earth/Ground", False)
        self.texture_loader.load_texture("ground_death", "Death/Ground", False)
        
        # Wall textures (WITH transparency for black areas)
        self.texture_loader.load_texture("wall1_earth", "Earth/Stena1", True)
        self.texture_loader.load_texture("wall2_earth", "Earth/Stena2", True)
        self.texture_loader.load_texture("wall1_death", "Death/Stena1", True)
        self.texture_loader.load_texture("wall2_death", "Death/Stena2", True)
        
        # Sky (different for each area, no transparency)
        self.texture_loader.load_texture("sky_earth", "Earth/Nebo", False)
        self.texture_loader.load_texture("sky_death", "Death/Nebo", False)
        
        # Trees (WITH transparency)
        self.texture_loader.load_texture("tree1", "Earth/Tree1", True)
        self.texture_loader.load_texture("tree2", "Death/Tree2", True)
        
        # Fire and Smoke (WITH transparency, animated sprites)
        self.texture_loader.load_texture("smoke", "Earth/Smoke", True)
        self.texture_loader.load_texture("fire", "Death/Faire", True)
        
        # NIZZ floor (no transparency)
        self.texture_loader.load_texture("nizz_earth", "Earth/Nizz", False)
        self.texture_loader.load_texture("nizz_death", "Death/Nizz", False)
        
        # Computer cube (no transparency)
        self.texture_loader.load_texture("computer", "CompKub", False)
        
        # Energy bars (no transparency, use colorkey for black)
        self.texture_loader.load_texture("energy_player", "EnergyPLY", False)
        self.texture_loader.load_texture("energy_computer", "EnergyCMP", False)
        
        # Intro/Logo (logo WITH transparency for black color)
        self.texture_loader.load_texture("intro_earth", "Earth/Intro1", False)
        self.texture_loader.load_texture("intro_death", "Death/Intro1", False)
        self.texture_loader.load_texture("logo", "IntroD4D", True)  # Black = transparent
        
        print(f"\nTotal textures loaded: {len(self.texture_loader.textures)}")
        
    def load_sounds(self):
        """Load all sound effects"""
        print("\n=== Loading sounds ===")
        self.sound.load_sound("select", "Sound/Select")
        self.sound.load_sound("start", "Sound/Start")
        self.sound.load_sound("laser", "Sound/Laser")
        self.sound.load_sound("pain", "Sound/Pain")
        self.sound.load_sound("dead", "Sound/Dead")
        self.sound.load_sound("killcomp", "Sound/Killcomp")
        self.sound.load_sound("teleport", "Sound/Teleport")
        
        # Intro sounds
        for i in range(5):
            self.sound.load_sound(f"intro{i}", f"Sound/Intro{i}")
            
        # Music
        self.sound.load_music_list("Music")
        
    def init_geometry(self):
        """Initialize trees and fire/smoke at random positions (from original VB6)"""
        self.trees1 = []
        self.trees2 = []
        self.smokes = []
        self.fires = []
        
        random.seed()
        
        # Create trees (TREE_MAX = 40)
        for i in range(TREE_MAX):
            # Tree1: height=20, width=3
            x = random.randint(-95, 95)
            z = random.randint(-95, 95)
            self.trees1.append(Sprite3D(x, z, height=20, width=3))
            
            # Tree2: height=12, width=5
            x = random.randint(-95, 95)
            z = random.randint(-95, 95)
            self.trees2.append(Sprite3D(x, z, height=12, width=5))
            
        # Create smoke and fire (FIRESMOKE = 40)
        for i in range(FIRESMOKE):
            # Smoke: height=3, width=1
            x = random.randint(-98, 98)
            z = random.randint(-98, 98)
            self.smokes.append(Sprite3D(x, z, height=3, width=1))
            
            # Fire: height=3, width=1
            x = random.randint(-98, 98)
            z = random.randint(-98, 98)
            self.fires.append(Sprite3D(x, z, height=3, width=1))
            
        print(f"Created {len(self.trees1)} trees1, {len(self.trees2)} trees2")
        print(f"Created {len(self.smokes)} smoke, {len(self.fires)} fire")
        
    def start_game(self, game_type: int):
        """Start a new game"""
        self.game_type = game_type
        self.player = Player()
        self.computer = Computer()
        self.play_time = 0
        self.time_ms = 0
        self.game_over = False
        self.in_menu = False
        self.intro_running = False
        
        # Set background color based on area
        if self.game_type == 1:
            glClearColor(0.0, 0.0, 0.4, 1.0)  # Blue for Earth
        else:
            glClearColor(0.2, 0.0, 0.0, 1.0)  # Red for Hell
            
        self.init_geometry()
        self.sound.play_sound("start")
        print(f"\nGame started! Area: {'Earth' if game_type == 1 else 'Hell'}")
        
    def draw_ground(self):
        """Draw ground plane (-100 to 100)"""
        texture_name = "ground_earth" if self.game_type == 1 else "ground_death"
        self.texture_loader.bind(texture_name)
        glColor4f(1, 1, 1, 1)
        
        # Apply zoom
        z = self.zoom
        
        glBegin(GL_TRIANGLE_STRIP)
        glTexCoord2f(0, 0); glVertex3f(-100 * z, 0, 100 * z)
        glTexCoord2f(1, 0); glVertex3f(100 * z, 0, 100 * z)
        glTexCoord2f(0, 1); glVertex3f(-100 * z, 0, -100 * z)
        glTexCoord2f(1, 1); glVertex3f(100 * z, 0, -100 * z)
        glEnd()
        
    def draw_nizz(self):
        """Draw rotating floor underneath (NIZZ from original)"""
        texture_name = "nizz_earth" if self.game_type == 1 else "nizz_death"
        self.texture_loader.bind(texture_name)
        glColor4f(1, 1, 1, 1)
        
        glPushMatrix()
        
        # Position at Y = -10, scaled by zoom
        z = self.zoom
        glTranslatef(0, -10 * z, 0)
        glRotatef(self.nizz_angle, 0, 1, 0)
        
        glBegin(GL_TRIANGLE_STRIP)
        glTexCoord2f(0, 0); glVertex3f(-500 * z, 0, 500 * z)
        glTexCoord2f(1, 0); glVertex3f(500 * z, 0, 500 * z)
        glTexCoord2f(0, 1); glVertex3f(-500 * z, 0, -500 * z)
        glTexCoord2f(1, 1); glVertex3f(500 * z, 0, -500 * z)
        glEnd()
        
        glPopMatrix()
        
    def draw_sky(self):
        """Draw sky (NEBO from original) at Y=50"""
        texture_name = "sky_earth" if self.game_type == 1 else "sky_death"
        self.texture_loader.bind(texture_name)
        glColor4f(1, 1, 1, 1)
        
        z = self.zoom
        
        glBegin(GL_TRIANGLE_STRIP)
        glTexCoord2f(0, 0); glVertex3f(250 * z, 50 * z, 250 * z)
        glTexCoord2f(1, 0); glVertex3f(-250 * z, 50 * z, 250 * z)
        glTexCoord2f(0, 1); glVertex3f(250 * z, 50 * z, -250 * z)
        glTexCoord2f(1, 1); glVertex3f(-250 * z, 50 * z, -250 * z)
        glEnd()
        
    def draw_walls(self):
        """Draw arena walls (from original VB6)"""
        z = self.zoom
        size = 20  # Size of one wall segment
        wall_height = 30
        
        wall1 = "wall1_earth" if self.game_type == 1 else "wall1_death"
        wall2 = "wall2_earth" if self.game_type == 1 else "wall2_death"
        
        # Back wall (+Z)
        self.texture_loader.bind(wall1)
        glBegin(GL_TRIANGLE_STRIP)
        for i in range(10):
            x1 = (-100 + i * size) * z
            x2 = (-80 + i * size) * z
            glTexCoord2f(0, 0); glVertex3f(x1, wall_height * z, 100 * z)
            glTexCoord2f(1, 0); glVertex3f(x2, wall_height * z, 100 * z)
            glTexCoord2f(0, 1); glVertex3f(x1, 0, 100 * z)
            glTexCoord2f(1, 1); glVertex3f(x2, 0, 100 * z)
        glEnd()
        
        # Front wall (-Z)
        glBegin(GL_TRIANGLE_STRIP)
        for i in range(10):
            x1 = (-80 + i * size) * z
            x2 = (-100 + i * size) * z
            glTexCoord2f(0, 0); glVertex3f(x1, wall_height * z, -100 * z)
            glTexCoord2f(1, 0); glVertex3f(x2, wall_height * z, -100 * z)
            glTexCoord2f(0, 1); glVertex3f(x1, 0, -100 * z)
            glTexCoord2f(1, 1); glVertex3f(x2, 0, -100 * z)
        glEnd()
        
        # Right wall (+X)
        self.texture_loader.bind(wall2)
        glBegin(GL_TRIANGLE_STRIP)
        for i in range(10):
            z1 = (-80 + i * size) * z
            z2 = (-100 + i * size) * z
            glTexCoord2f(0, 0); glVertex3f(100 * z, wall_height * z, z1)
            glTexCoord2f(1, 0); glVertex3f(100 * z, wall_height * z, z2)
            glTexCoord2f(0, 1); glVertex3f(100 * z, 0, z1)
            glTexCoord2f(1, 1); glVertex3f(100 * z, 0, z2)
        glEnd()
        
        # Left wall (-X)
        glBegin(GL_TRIANGLE_STRIP)
        for i in range(10):
            z1 = (-100 + i * size) * z
            z2 = (-80 + i * size) * z
            glTexCoord2f(0, 0); glVertex3f(-100 * z, wall_height * z, z1)
            glTexCoord2f(1, 0); glVertex3f(-100 * z, wall_height * z, z2)
            glTexCoord2f(0, 1); glVertex3f(-100 * z, 0, z1)
            glTexCoord2f(1, 1); glVertex3f(-100 * z, 0, z2)
        glEnd()
        
    def draw_sprite_3d(self, sprite: Sprite3D):
        """Draw cross-shaped 3D sprite (4 faces in + pattern, from original VB6)"""
        x = sprite.x * self.zoom
        z = sprite.z * self.zoom
        h = sprite.height * self.zoom
        w = sprite.width * self.zoom
        
        # Face 1 (parallel to X axis, facing +Z)
        glBegin(GL_TRIANGLE_STRIP)
        glTexCoord2f(0, 0); glVertex3f(x - w, h, z)
        glTexCoord2f(1, 0); glVertex3f(x + w, h, z)
        glTexCoord2f(0, 1); glVertex3f(x - w, 0, z)
        glTexCoord2f(1, 1); glVertex3f(x + w, 0, z)
        glEnd()
        
        # Face 2 (parallel to X axis, facing -Z)
        glBegin(GL_TRIANGLE_STRIP)
        glTexCoord2f(1, 0); glVertex3f(x + w, h, z)
        glTexCoord2f(0, 0); glVertex3f(x - w, h, z)
        glTexCoord2f(1, 1); glVertex3f(x + w, 0, z)
        glTexCoord2f(0, 1); glVertex3f(x - w, 0, z)
        glEnd()
        
        # Face 3 (parallel to Z axis, facing +X)
        glBegin(GL_TRIANGLE_STRIP)
        glTexCoord2f(0, 0); glVertex3f(x, h, z - w)
        glTexCoord2f(1, 0); glVertex3f(x, h, z + w)
        glTexCoord2f(0, 1); glVertex3f(x, 0, z - w)
        glTexCoord2f(1, 1); glVertex3f(x, 0, z + w)
        glEnd()
        
        # Face 4 (parallel to Z axis, facing -X)
        glBegin(GL_TRIANGLE_STRIP)
        glTexCoord2f(1, 0); glVertex3f(x, h, z + w)
        glTexCoord2f(0, 0); glVertex3f(x, h, z - w)
        glTexCoord2f(1, 1); glVertex3f(x, 0, z + w)
        glTexCoord2f(0, 1); glVertex3f(x, 0, z - w)
        glEnd()
        
    def draw_sprite_3d_animated(self, sprite: Sprite3D, u_off: float, v_off: float, u_size: float, v_size: float):
        """Draw animated cross-shaped 3D sprite with UV offset"""
        x = sprite.x * self.zoom
        z = sprite.z * self.zoom
        h = sprite.height * self.zoom
        w = sprite.width * self.zoom
        
        # UV coordinates for current animation frame
        u0 = u_off
        u1 = u_off + u_size
        v0 = v_off
        v1 = v_off + v_size
        
        # Face 1 (parallel to X axis, facing +Z)
        glBegin(GL_TRIANGLE_STRIP)
        glTexCoord2f(u0, v0); glVertex3f(x - w, h, z)
        glTexCoord2f(u1, v0); glVertex3f(x + w, h, z)
        glTexCoord2f(u0, v1); glVertex3f(x - w, 0, z)
        glTexCoord2f(u1, v1); glVertex3f(x + w, 0, z)
        glEnd()
        
        # Face 2 (parallel to X axis, facing -Z)
        glBegin(GL_TRIANGLE_STRIP)
        glTexCoord2f(u1, v0); glVertex3f(x + w, h, z)
        glTexCoord2f(u0, v0); glVertex3f(x - w, h, z)
        glTexCoord2f(u1, v1); glVertex3f(x + w, 0, z)
        glTexCoord2f(u0, v1); glVertex3f(x - w, 0, z)
        glEnd()
        
        # Face 3 (parallel to Z axis, facing +X)
        glBegin(GL_TRIANGLE_STRIP)
        glTexCoord2f(u0, v0); glVertex3f(x, h, z - w)
        glTexCoord2f(u1, v0); glVertex3f(x, h, z + w)
        glTexCoord2f(u0, v1); glVertex3f(x, 0, z - w)
        glTexCoord2f(u1, v1); glVertex3f(x, 0, z + w)
        glEnd()
        
        # Face 4 (parallel to Z axis, facing -X)
        glBegin(GL_TRIANGLE_STRIP)
        glTexCoord2f(u1, v0); glVertex3f(x, h, z + w)
        glTexCoord2f(u0, v0); glVertex3f(x, h, z - w)
        glTexCoord2f(u1, v1); glVertex3f(x, 0, z + w)
        glTexCoord2f(u0, v1); glVertex3f(x, 0, z - w)
        glEnd()
        
    def draw_trees(self):
        """Draw trees - Earth uses Tree1 (fir trees), Death uses Tree2 (dead trees)"""
        glColor4f(1, 1, 1, 1)
        
        # Earth: only Tree1 (fir trees)
        if self.game_type == 1 and "tree1" in self.texture_loader.textures:
            self.texture_loader.bind("tree1")
            # Draw both tree types with Tree1 texture
            for tree in self.trees1:
                self.draw_sprite_3d(tree)
            for tree in self.trees2:
                self.draw_sprite_3d(tree)
                
        # Hell: only Tree2 (dead trees)
        if self.game_type == 2 and "tree2" in self.texture_loader.textures:
            self.texture_loader.bind("tree2")
            # Draw both tree types with Tree2 texture
            for tree in self.trees1:
                self.draw_sprite_3d(tree)
            for tree in self.trees2:
                self.draw_sprite_3d(tree)
                    
    def draw_fire_smoke(self):
        """Draw fire and smoke sprites with animation"""
        # Calculate UV coordinates for current animation frame
        u_offset = self.cel_x / self.frame_x
        v_offset = self.cel_y / self.frame_y
        u_size = 1.0 / self.frame_x
        v_size = 1.0 / self.frame_y
        
        # Smoke for Earth area
        if self.game_type == 1 and "smoke" in self.texture_loader.textures:
            glColor4f(1, 1, 1, 0.8)
            self.texture_loader.bind("smoke")
            for smoke in self.smokes:
                self.draw_sprite_3d_animated(smoke, u_offset, v_offset, u_size, v_size)
                
        # Fire for Hell area
        if self.game_type == 2 and "fire" in self.texture_loader.textures:
            glColor4f(1, 1, 1, 0.9)
            self.texture_loader.bind("fire")
            for fire in self.fires:
                self.draw_sprite_3d_animated(fire, u_offset, v_offset, u_size, v_size)
                
    def draw_computer(self):
        """Draw computer cube (from original VB6)"""
        glPushMatrix()
        
        # Position and scale (scale = 0.25 * zoom from original)
        s = 10 * 0.25 * self.zoom
        x = self.computer.x * self.zoom
        z = self.computer.z * self.zoom
        
        glTranslatef(x, self.computer.y * self.zoom, z)
        glRotatef(self.computer.rotate_x, 1, 0, 0)
        glRotatef(self.computer.rotate_y, 0, 1, 0)
        glRotatef(self.computer.rotate_z, 0, 0, 1)
        
        self.texture_loader.bind("computer")
        glColor4f(1, 1, 1, 1)
        
        # Draw cube faces
        glBegin(GL_QUADS)
        
        # Front (+Z)
        glTexCoord2f(0, 1); glVertex3f(-s, -s, -s)
        glTexCoord2f(1, 1); glVertex3f(s, -s, -s)
        glTexCoord2f(1, 0); glVertex3f(s, s, -s)
        glTexCoord2f(0, 0); glVertex3f(-s, s, -s)
        
        # Back (-Z)
        glTexCoord2f(1, 1); glVertex3f(s, -s, s)
        glTexCoord2f(0, 1); glVertex3f(-s, -s, s)
        glTexCoord2f(0, 0); glVertex3f(-s, s, s)
        glTexCoord2f(1, 0); glVertex3f(s, s, s)
        
        # Left (-X)
        glTexCoord2f(1, 1); glVertex3f(-s, -s, s)
        glTexCoord2f(0, 1); glVertex3f(-s, -s, -s)
        glTexCoord2f(0, 0); glVertex3f(-s, s, -s)
        glTexCoord2f(1, 0); glVertex3f(-s, s, s)
        
        # Right (+X)
        glTexCoord2f(0, 1); glVertex3f(s, -s, -s)
        glTexCoord2f(1, 1); glVertex3f(s, -s, s)
        glTexCoord2f(1, 0); glVertex3f(s, s, s)
        glTexCoord2f(0, 0); glVertex3f(s, s, -s)
        
        # Top (+Y)
        glTexCoord2f(0, 1); glVertex3f(-s, s, -s)
        glTexCoord2f(1, 1); glVertex3f(s, s, -s)
        glTexCoord2f(1, 0); glVertex3f(s, s, s)
        glTexCoord2f(0, 0); glVertex3f(-s, s, s)
        
        # Bottom (-Y)
        glTexCoord2f(0, 0); glVertex3f(-s, -s, s)
        glTexCoord2f(1, 0); glVertex3f(s, -s, s)
        glTexCoord2f(1, 1); glVertex3f(s, -s, -s)
        glTexCoord2f(0, 1); glVertex3f(-s, -s, -s)
        
        glEnd()
        
        glPopMatrix()
        
    def draw_laser(self):
        """Draw laser beam when shooting"""
        if not self.player.fire_now:
            return
            
        glDisable(GL_TEXTURE_2D)
        glColor4f(1.0, 0.3, 0.0, 1.0)
        glLineWidth(4.0)
        
        z = self.zoom
        dist = 150 * z
        
        # Start from player position
        start_x = self.player.x * z
        start_z = self.player.z * z
        
        # End at look direction
        end_x = start_x + dist * math.sin(self.player.angle)
        end_z = start_z + dist * math.cos(self.player.angle)
        
        glBegin(GL_LINES)
        glVertex3f(start_x, self.player.y * z, start_z)
        glVertex3f(end_x, self.player.y * z, end_z)
        glEnd()
        
        glEnable(GL_TEXTURE_2D)
        
    def draw_crosshair(self):
        """Draw targeting crosshair"""
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
        """Draw player and computer energy bars using texture images"""
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_W, SCREEN_H, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)
        
        bar_w = 200
        bar_h = 40
        margin = 30
        
        # Player energy (bottom left)
        px = margin
        py = SCREEN_H - bar_h - margin
        pw = int(bar_w * self.player.energy / 100.0)
        
        # Draw energy bar background
        glDisable(GL_TEXTURE_2D)
        glColor4f(0.3, 0.3, 0.3, 1.0)
        glBegin(GL_QUADS)
        glVertex2i(px, py)
        glVertex2i(px + bar_w, py)
        glVertex2i(px + bar_w, py + bar_h)
        glVertex2i(px, py + bar_h)
        glEnd()
        
        # Draw player energy with texture
        if "energy_player" in self.texture_loader.textures:
            glEnable(GL_TEXTURE_2D)
            self.texture_loader.bind("energy_player")
            glColor4f(1, 1, 1, 1)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2i(px, py)
            glTexCoord2f(1, 0); glVertex2i(px + pw, py)
            glTexCoord2f(1, 1); glVertex2i(px + pw, py + bar_h)
            glTexCoord2f(0, 1); glVertex2i(px, py + bar_h)
            glEnd()
        else:
            # Fallback - green bar
            glColor4f(0, 0.8, 0, 1.0)
            glBegin(GL_QUADS)
            glVertex2i(px, py)
            glVertex2i(px + pw, py)
            glVertex2i(px + pw, py + bar_h)
            glVertex2i(px, py + bar_h)
            glEnd()
        
        # Computer energy (bottom right)
        cx = SCREEN_W - bar_w - margin
        cy = SCREEN_H - bar_h - margin
        cw = int(bar_w * self.computer.energy / 100.0)
        
        # Draw energy bar background
        glDisable(GL_TEXTURE_2D)
        glColor4f(0.3, 0.3, 0.3, 1.0)
        glBegin(GL_QUADS)
        glVertex2i(cx, cy)
        glVertex2i(cx + bar_w, cy)
        glVertex2i(cx + bar_w, cy + bar_h)
        glVertex2i(cx, cy + bar_h)
        glEnd()
        
        # Draw computer energy with texture
        if "energy_computer" in self.texture_loader.textures:
            glEnable(GL_TEXTURE_2D)
            self.texture_loader.bind("energy_computer")
            glColor4f(1, 1, 1, 1)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2i(cx, cy)
            glTexCoord2f(1, 0); glVertex2i(cx + cw, cy)
            glTexCoord2f(1, 1); glVertex2i(cx + cw, cy + bar_h)
            glTexCoord2f(0, 1); glVertex2i(cx, cy + bar_h)
            glEnd()
        else:
            # Fallback - red bar
            glColor4f(0.8, 0, 0, 1.0)
            glBegin(GL_QUADS)
            glVertex2i(cx, cy)
            glVertex2i(cx + cw, cy)
            glVertex2i(cx + cw, cy + bar_h)
            glVertex2i(cx, cy + bar_h)
            glEnd()
        
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def draw_intro(self):
        """Draw intro animation - 4 quadrants + logo zoom (from original VB6)"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_W, SCREEN_H, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)
        
        # Black background
        glColor3f(0, 0, 0)
        glBegin(GL_QUADS)
        glVertex2i(0, 0); glVertex2i(SCREEN_W, 0)
        glVertex2i(SCREEN_W, SCREEN_H); glVertex2i(0, SCREEN_H)
        glEnd()
        
        # Progressive reveal of intro picture (4 quadrants)
        texture_name = "intro_earth" if self.game_type == 1 else "intro_death"
        
        if self.intro_stage >= 1:
            self.texture_loader.bind(texture_name)
            if self.texture_loader.get(texture_name):
                glColor3f(1, 1, 1)
                
                # Stage 1: Top-left quadrant (0,0 to midX,midY)
                if self.intro_stage >= 1:
                    glBegin(GL_QUADS)
                    glTexCoord2f(0, 0); glVertex2i(0, 0)
                    glTexCoord2f(0.5, 0); glVertex2i(SCREEN_W//2, 0)
                    glTexCoord2f(0.5, 0.5); glVertex2i(SCREEN_W//2, SCREEN_H//2)
                    glTexCoord2f(0, 0.5); glVertex2i(0, SCREEN_H//2)
                    glEnd()
                
                # Stage 2: Top-right quadrant (midX,0 to W,midY)
                if self.intro_stage >= 2:
                    glBegin(GL_QUADS)
                    glTexCoord2f(0.5, 0); glVertex2i(SCREEN_W//2, 0)
                    glTexCoord2f(1, 0); glVertex2i(SCREEN_W, 0)
                    glTexCoord2f(1, 0.5); glVertex2i(SCREEN_W, SCREEN_H//2)
                    glTexCoord2f(0.5, 0.5); glVertex2i(SCREEN_W//2, SCREEN_H//2)
                    glEnd()
                
                # Stage 3: Bottom-left quadrant (0,midY to midX,H)
                if self.intro_stage >= 3:
                    glBegin(GL_QUADS)
                    glTexCoord2f(0, 0.5); glVertex2i(0, SCREEN_H//2)
                    glTexCoord2f(0.5, 0.5); glVertex2i(SCREEN_W//2, SCREEN_H//2)
                    glTexCoord2f(0.5, 1); glVertex2i(SCREEN_W//2, SCREEN_H)
                    glTexCoord2f(0, 1); glVertex2i(0, SCREEN_H)
                    glEnd()
                
                # Stage 4: Bottom-right quadrant (midX,midY to W,H)
                if self.intro_stage >= 4:
                    glBegin(GL_QUADS)
                    glTexCoord2f(0.5, 0.5); glVertex2i(SCREEN_W//2, SCREEN_H//2)
                    glTexCoord2f(1, 0.5); glVertex2i(SCREEN_W, SCREEN_H//2)
                    glTexCoord2f(1, 1); glVertex2i(SCREEN_W, SCREEN_H)
                    glTexCoord2f(0.5, 1); glVertex2i(SCREEN_W//2, SCREEN_H)
                    glEnd()
        
        # Stage 5: Full intro picture (before zoom)
        if self.intro_stage >= 5:
            # Full intro picture
            self.texture_loader.bind(texture_name)
            if self.texture_loader.get(texture_name):
                glColor3f(1, 1, 1)
                glBegin(GL_QUADS)
                glTexCoord2f(0, 0); glVertex2i(0, 0)
                glTexCoord2f(1, 0); glVertex2i(SCREEN_W, 0)
                glTexCoord2f(1, 1); glVertex2i(SCREEN_W, SCREEN_H)
                glTexCoord2f(0, 1); glVertex2i(0, SCREEN_H)
                glEnd()
        
        # Stage 6+: Logo overlay - zoom OUT from full screen to small
        # From original: DDRect(x, Y, ScreenW - x, ScreenH - Y)
        # x,Y start at 0 and increase to 80
        # This makes logo SHRINK from full screen to center
        if self.intro_stage >= 6:
            if "logo" in self.texture_loader.textures:
                self.texture_loader.bind("logo")
                glColor4f(1, 1, 1, 1)
                
                margin = int(self.intro_zoom)
                # Logo starts full screen (margin=0) and shrinks (margin increases)
                # Left=margin, Top=margin, Right=ScreenW-margin, Bottom=ScreenH-margin
                glBegin(GL_QUADS)
                glTexCoord2f(0, 0); glVertex2i(margin, margin)
                glTexCoord2f(1, 0); glVertex2i(SCREEN_W - margin, margin)
                glTexCoord2f(1, 1); glVertex2i(SCREEN_W - margin, SCREEN_H - margin)
                glTexCoord2f(0, 1); glVertex2i(margin, SCREEN_H - margin)
                glEnd()
        
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def draw_menu(self):
        """Draw main menu with logo"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_W, 0, SCREEN_H, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)
        
        # Black background
        glColor3f(1, 1, 1)
        glBegin(GL_QUADS)
        glVertex2i(0, 0); glVertex2i(SCREEN_W, 0)
        glVertex2i(SCREEN_W, SCREEN_H); glVertex2i(0, SCREEN_H)
        glEnd()
        
        # Logo centered
        if "logo" in self.texture_loader.textures:
            self.texture_loader.bind("logo")
            glColor4f(1, 1, 1, 1)
            glEnable(GL_TEXTURE_2D)
            
            lw, lh = 600, 400
            lx = (SCREEN_W - lw) // 2
            ly = (SCREEN_H - lh) // 2
            
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2i(lx, ly + lh)
            glTexCoord2f(1, 0); glVertex2i(lx + lw, ly + lh)
            glTexCoord2f(1, 1); glVertex2i(lx + lw, ly)
            glTexCoord2f(0, 1); glVertex2i(lx, ly)
            glEnd()
        
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
    def check_hit(self) -> bool:
        """Check if laser hits computer (from original VB6)"""
        dx = self.computer.x - self.player.x
        dz = self.computer.z - self.player.z
        dist = math.sqrt(dx*dx + dz*dz)
        
        if dist > 80:  # Max range
            return False
            
        # Calculate angle between player look direction and target
        # Using cosine formula from original
        angle_to = math.atan2(dx, dz)
        diff = angle_to - self.player.angle
        
        # Normalize angle difference
        while diff > PI: diff -= 2*PI
        while diff < -PI: diff += 2*PI
        
        # Check if within firing cone
        return abs(diff) < 0.15  # ~8.6 degrees
        
    def check_collision(self) -> bool:
        """Check collision between player and computer (from original VB6)"""
        dx = self.computer.x - self.player.x
        dz = self.computer.z - self.player.z
        dist = math.sqrt(dx*dx + dz*dz)
        
        if dist <= 4:  # Collision distance from original
            self.player.energy -= 2  # -2 energy per collision
            if self.player.energy <= 0:
                self.player.energy = 0
                self.game_over = True
                self.sound.play_sound("dead")
            return True
        return False
        
    def handle_input(self):
        """Handle keyboard input (from original VB6)"""
        keys = pygame.key.get_pressed()
        
        if self.in_menu or self.game_over:
            return
            
        # Rotation - swapped for OpenGL coordinate system
        if keys[K_RIGHT]:
            self.player.angle -= self.player.rotate_speed
        if keys[K_LEFT]:
            self.player.angle += self.player.rotate_speed
            
        # Normalize angle
        while self.player.angle >= 2*PI: self.player.angle -= 2*PI
        while self.player.angle < 0: self.player.angle += 2*PI
            
        # Movement (from original: step*cos(alfa) for Z, step*sin(alfa) for X)
        if keys[K_UP]:
            self.player.x += self.player.step * math.sin(self.player.angle)
            self.player.z += self.player.step * math.cos(self.player.angle)
        if keys[K_DOWN]:
            self.player.x -= self.player.step * math.sin(self.player.angle)
            self.player.z -= self.player.step * math.cos(self.player.angle)
            
        # Shooting
        shoot = keys[K_SPACE]
        if shoot and not self.player.last_shoot:
            self.player.fire_now = True
            self.sound.play_sound("laser")
            if self.check_hit():
                self.computer.energy -= 1  # -1 energy per hit from original
                if self.computer.energy <= 0:
                    self.player.wins += 1
                    self.sound.play_sound("killcomp")
                    # Switch area and restart
                    self.game_type = 2 if self.game_type == 1 else 1
                    self.start_game(self.game_type)
        else:
            self.player.fire_now = False
        self.player.last_shoot = shoot
        
        # Boundary check (POLE=200, divided by zoom=2, so ±100)
        limit = (POLE / self.zoom) - 5
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
            
        # Update fire/smoke animation
        self.anim_timer += dt
        if self.anim_timer >= self.anim_delay:
            self.anim_timer = 0
            self.cel_x += 1
            if self.cel_x >= self.frame_x:
                self.cel_x = 0
                self.cel_y += 1
                if self.cel_y >= self.frame_y:
                    self.cel_y = 0
            
        # Update NIZZ rotation
        self.nizz_angle += 1.0
        
        # Update computer
        self.computer.update()
        
        # Check collision
        self.check_collision()
        
        # Fog control at specific times (from original VB6)
        if self.play_time == 60 or self.play_time == 300:
            # White fog ON
            self.fog_enabled = True
            self.fog_color = (1.0, 1.0, 1.0, 1.0)
            glFogi(GL_FOG_MODE, GL_LINEAR)
            glFogfv(GL_FOG_COLOR, self.fog_color)
            glFogf(GL_FOG_START, 50.0)
            glFogf(GL_FOG_END, 500.0)
            glEnable(GL_FOG)
            
        if self.play_time == 180 or self.play_time == 400:
            # Black fog ON
            self.fog_enabled = True
            self.fog_color = (0.0, 0.0, 0.1, 1.0)
            glFogfv(GL_FOG_COLOR, self.fog_color)
            glEnable(GL_FOG)
            
        if self.play_time == 120 or self.play_time == 500:
            # Fog OFF
            self.fog_enabled = False
            glDisable(GL_FOG)
        
    def update_intro(self, dt: int):
        """Update intro animation - 3000ms per quadrant (from original VB6)"""
        if not self.intro_running:
            return
            
        self.intro_timer += dt
        
        # 3000ms per quadrant (TimerIntro.Interval = 3000 in VB6)
        if self.intro_timer > 3000:
            self.intro_timer = 0
            self.intro_stage += 1
            
            # Play intro sounds (from original)
            if self.intro_stage == 1:
                self.sound.play_sound("intro1")
            elif self.intro_stage == 2:
                self.sound.play_sound("intro2")
            elif self.intro_stage == 3:
                self.sound.play_sound("intro3")
            elif self.intro_stage == 4:
                self.sound.play_sound("intro4")
            elif self.intro_stage == 6:
                self.sound.play_sound("intro0")
        
        # Zoom animation (PicShowed = 6 in original, runs EVERY FRAME)
        if self.intro_stage >= 6:
            # Zoom OUT: x increases from 0 to 80 (logo shrinks from full screen)
            self.intro_zoom = min(80.0, self.intro_zoom + 0.5 * (dt / 16.67))
            if self.intro_zoom >= 80.0:
                self.intro_running = False
        
    def render(self):
        """Render the scene"""
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
        
        # Camera setup matching original DirectX7 (left-handed coordinates)
        # Look from player position toward angle direction
        z = self.zoom
        dist2focus = 70  # From original VB6
        
        cam_x = self.player.x * z
        cam_y = self.player.y * z
        cam_z = self.player.z * z
        
        look_x = cam_x + dist2focus * z * math.sin(self.player.angle)
        look_y = cam_y
        look_z = cam_z + dist2focus * z * math.cos(self.player.angle)
        
        gluLookAt(
            cam_x, cam_y, cam_z,
            look_x, look_y, look_z,
            0, 1, 0
        )
        
        # Draw world
        self.draw_nizz()
        self.draw_sky()
        self.draw_ground()
        self.draw_walls()
        self.draw_trees()
        self.draw_fire_smoke()
        self.draw_computer()
        self.draw_laser()
        
        # Draw HUD
        self.draw_crosshair()
        self.draw_energy_bars()
        
        pygame.display.flip()
        
    def run(self):
        """Main game loop"""
        print("\n" + "="*50)
        print("DOOM 4D - Python Remastered")
        print("(c) 2004 Denis Astahov")
        print("="*50)
        print("\nControls:")
        print("  1/E - Earth | 2/H - Hell")
        print("  UP/DOWN - Move | LEFT/RIGHT - Rotate")
        print("  SPACE - Shoot | F1-F7 - Music")
        print("  F12 - Teleport | Q - Black Fog | W - White Fog | Z - Fog Off")
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
                            
                    if self.intro_running:
                        # Skip intro on any key
                        if event.key in [K_RETURN, K_SPACE, K_1, K_e]:
                            self.intro_running = False
                        continue
                        
                    if self.in_menu:
                        # Menu controls
                        if event.key in [K_1, K_e, K_RETURN]:
                            self.sound.play_sound("select")
                            self.start_game(1)
                        elif event.key in [K_2, K_h]:
                            self.sound.play_sound("select")
                            self.start_game(2)
                            
                    if not self.in_menu and not self.game_over:
                        # In-game controls
                        if event.key in [K_F1, K_F2, K_F3, K_F4, K_F5, K_F6, K_F7]:
                            self.sound.play_music(event.key - K_F1 + 1)
                            
                        if event.key == K_F12:
                            # Teleport (switch area)
                            self.game_type = 2 if self.game_type == 1 else 1
                            self.sound.play_sound("teleport")
                            self.start_game(self.game_type)
                            
                        # Fog controls
                        if event.key == K_z:
                            glDisable(GL_FOG)
                            self.fog_enabled = False
                        if event.key == K_w:
                            glFogi(GL_FOG_MODE, GL_LINEAR)
                            glFogfv(GL_FOG_COLOR, (1.0, 1.0, 1.0, 1.0))
                            glFogf(GL_FOG_START, 50.0)
                            glFogf(GL_FOG_END, 500.0)
                            glEnable(GL_FOG)
                        if event.key == K_q:
                            glFogi(GL_FOG_MODE, GL_LINEAR)
                            glFogfv(GL_FOG_COLOR, (0.0, 0.0, 0.1, 1.0))
                            glFogf(GL_FOG_START, 50.0)
                            glFogf(GL_FOG_END, 500.0)
                            glEnable(GL_FOG)
                            
                    if self.game_over:
                        # Game over controls
                        if event.key == K_n:
                            # New game
                            self.player.wins = 0
                            self.start_game(1)
                            
            # Update and render
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
