#!/usr/bin/env python3
"""
DOOM 4D - Python Port
Originally created by Denis Astahov (ADV-IT) in 2004
Visual Basic 6 + DirectX 7 -> Python + Pygame

Bachelor Degree Project - Score: 95/100
"""

import pygame
import math
import random
import os
import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Constants (from original VB6 code)
COMPSTEP = 100  # Number of Computer STEPS in one Direction Movement
TREE_MAX = 40   # Counter of Trees - My FOREST :)
FIRESMOKE = 40  # Counter of maximum Fire and Smoke Animations
PI = 3.14159265358979
RADIANS = PI / 180
POLE = 200      # Size of Area from Center to WALLs

# Screen settings
SCREEN_W = 1024
SCREEN_H = 768

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
MAGENTA = (255, 0, 255)
CYAN = (0, 255, 255)


@dataclass
class Sprite3D:
    """For Tree, Explosion, etc."""
    x: int
    z: int
    height: int
    width: int
    vertices: List[Tuple[float, float, float, float, float]] = None
    
    def __post_init__(self):
        if self.vertices is None:
            self.vertices = []


class SoundManager:
    """Handles sound playback"""
    def __init__(self):
        self.sounds = {}
        self.current_music = None
        
    def load_sound(self, name: str, path: str):
        """Load a sound effect"""
        try:
            self.sounds[name] = pygame.mixer.Sound(path)
        except:
            print(f"Could not load sound: {path}")
            
    def play_sound(self, name: str):
        """Play a sound effect"""
        if name in self.sounds:
            self.sounds[name].play()
            
    def play_music(self, path: str):
        """Play background music"""
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1)  # Loop
            self.current_music = path
        except:
            print(f"Could not load music: {path}")
            
    def stop_music(self):
        """Stop background music"""
        pygame.mixer.music.stop()


class Player:
    """Player/Camera entity"""
    def __init__(self):
        self.x = 0.0
        self.y = 6.0  # Camera height
        self.z = -12.0
        self.look_x = 0.0
        self.look_y = 6.0
        self.look_z = 70.0  # dist2focus
        self.angle = 0.0  # alfa - rotation angle
        self.step = 0.5
        self.delta = 0.8 * RADIANS  # rotation step
        self.energy = 100
        self.wins = 0
        self.fire_now = False


class Computer:
    """Computer-controlled enemy"""
    def __init__(self):
        self.x = 0.0
        self.y = 4.0
        self.z = 0.0
        self.new_x = 0
        self.new_z = 0
        self.old_x = 0
        self.old_z = 0
        self.dx = 0.0
        self.dz = 0.0
        self.step_count = COMPSTEP
        self.energy = 100
        self.rotate_x = 0
        self.rotate_y = 0
        self.rotate_z = 0


class Doom4D:
    """Main game class"""
    
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("DOOM 4D - Python Port")
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.quit_game = False
        self.game_type = 1  # 1 = Earth, 2 = Hell/Death
        
        # Game objects
        self.player = Player()
        self.computer = Computer()
        self.trees1: List[Sprite3D] = []
        self.trees2: List[Sprite3D] = []
        self.smokes: List[Sprite3D] = []
        self.fires: List[Sprite3D] = []
        
        # Textures (surfaces)
        self.textures = {}
        self.intro_img = None
        self.logo_img = None
        self.gameover_img = None
        self.expl_img = None
        self.craft_img = None
        self.craft_fired_img = None
        
        # Animation
        self.cel_x = 0
        self.cel_y = 0
        self.frame_x = 5
        self.frame_y = 4
        self.cel_max_x = 32
        self.cel_max_y = 64
        self.anim_wait = 0
        
        # Time
        self.play_time = 0
        self.time_counter = 0
        
        # Sound
        self.sound = SoundManager()
        
        # Menu state
        self.in_menu = True
        self.in_intro = False
        self.game_over = False
        self.intro_stage = 0
        
        # Video mode selection
        self.video_modes = [
            (640, 480), (800, 600), (1024, 768), (1280, 1024)
        ]
        self.current_mode = 2
        
        # Fog settings
        self.fog_enabled = False
        self.fog_color = (128, 128, 180)
        self.fog_mode = 2  # EXP
        
        # Key states
        self.keys_pressed = set()
        
    def init_geometry(self):
        """Initialize 3D geometry"""
        # Create trees
        self.trees1 = []
        self.trees2 = []
        
        for i in range(TREE_MAX):
            x = random.randint(-95, 95)
            z = random.randint(-95, 95)
            self.trees1.append(Sprite3D(x=x, z=z, height=20, width=3))
            
            x = random.randint(-95, 95)
            z = random.randint(-95, 95)
            self.trees2.append(Sprite3D(x=x, z=z, height=12, width=5))
            
        # Create smoke/fire
        self.smokes = []
        self.fires = []
        
        for i in range(FIRESMOKE):
            x = random.randint(-98, 98)
            z = random.randint(-98, 98)
            self.smokes.append(Sprite3D(x=x, z=z, height=3, width=1))
            
            x = random.randint(-98, 98)
            z = random.randint(-98, 98)
            self.fires.append(Sprite3D(x=x, z=z, height=3, width=1))
            
        # Reset computer
        self.computer = Computer()
        
    def load_textures(self):
        """Load all textures (simplified - using colored rects)"""
        # Create procedural textures
        self.textures['ground'] = self.create_ground_texture()
        self.textures['wall1'] = self.create_wall_texture(1)
        self.textures['wall2'] = self.create_wall_texture(2)
        self.textures['sky'] = self.create_sky_texture()
        self.textures['tree1'] = self.create_tree_texture(1)
        self.textures['tree2'] = self.create_tree_texture(2)
        self.textures['fire'] = self.create_fire_texture()
        self.textures['smoke'] = self.create_smoke_texture()
        
        # Load images if available
        base_path = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_path, '..', 'doom4d', 'Image')
        
        # Try to load intro/gameover images
        area = "Earth" if self.game_type == 1 else "Death"
        
        try:
            intro_path = os.path.join(img_path, area, 'Intro1.jpg')
            if os.path.exists(intro_path):
                self.intro_img = pygame.image.load(intro_path)
        except:
            pass
            
        try:
            gameover_path = os.path.join(img_path, 'GameOver.jpg')
            if os.path.exists(gameover_path):
                self.gameover_img = pygame.image.load(gameover_path)
        except:
            pass
            
        # Create craft interface
        self.craft_img = self.create_craft_texture(False)
        self.craft_fired_img = self.create_craft_texture(True)
        self.expl_img = self.create_explosion_texture()
        
    def create_ground_texture(self):
        """Create procedural ground texture"""
        surf = pygame.Surface((256, 256))
        base_color = (34, 139, 34) if self.game_type == 1 else (80, 40, 20)  # Green or Dark
        surf.fill(base_color)
        # Add noise
        for _ in range(1000):
            x = random.randint(0, 255)
            y = random.randint(0, 255)
            c = random.randint(-20, 20)
            color = tuple(max(0, min(255, base_color[i] + c)) for i in range(3))
            surf.set_at((x, y), color)
        return surf
        
    def create_wall_texture(self, wall_type):
        """Create procedural wall texture"""
        surf = pygame.Surface((64, 64))
        color = (139, 69, 19) if wall_type == 1 else (100, 50, 20)  # Brown tones
        surf.fill(color)
        # Add brick pattern
        for y in range(0, 64, 16):
            offset = 16 if (y // 16) % 2 else 0
            for x in range(0, 64, 32):
                rect = pygame.Rect(x + offset, y, 30, 14)
                darker = tuple(max(0, c - 30) for c in color)
                pygame.draw.rect(surf, darker, rect, 1)
        return surf
        
    def create_sky_texture(self):
        """Create procedural sky texture"""
        surf = pygame.Surface((512, 512))
        for y in range(512):
            # Gradient from dark blue to light
            ratio = y / 512
            r = int(135 * ratio)
            g = int(206 * ratio)
            b = int(235 * ratio)
            pygame.draw.line(surf, (r, g, b), (0, y), (512, y))
        return surf
        
    def create_tree_texture(self, tree_type):
        """Create procedural tree texture"""
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        if tree_type == 1:
            # Pine tree (triangle)
            pygame.draw.polygon(surf, (34, 139, 34), [(32, 0), (0, 64), (64, 64)])
            pygame.draw.rect(surf, (139, 69, 19), (28, 50, 8, 14))
        else:
            # Round tree
            pygame.draw.circle(surf, (0, 100, 0), (32, 32), 24)
            pygame.draw.circle(surf, (0, 80, 0), (32, 32), 20)
            pygame.draw.rect(surf, (139, 69, 19), (28, 48, 8, 16))
        return surf
        
    def create_fire_texture(self):
        """Create fire texture"""
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (255, 100, 0), [(32, 0), (0, 64), (64, 64)])
        pygame.draw.polygon(surf, (255, 200, 0), [(32, 10), (10, 64), (54, 64)])
        return surf
        
    def create_smoke_texture(self):
        """Create smoke texture"""
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.circle(surf, (128, 128, 128, 150), (32, 32), 24)
        pygame.draw.circle(surf, (100, 100, 100, 100), (32, 32), 18)
        return surf
        
    def create_craft_texture(self, fired):
        """Create craft/ship interface"""
        surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        # Draw crosshair
        color = (255, 255, 0) if fired else (0, 255, 0)
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        
        # Crosshair lines
        pygame.draw.line(surf, color, (cx - 30, cy), (cx - 10, cy), 2)
        pygame.draw.line(surf, color, (cx + 10, cy), (cx + 30, cy), 2)
        pygame.draw.line(surf, color, (cx, cy - 30), (cx, cy - 10), 2)
        pygame.draw.line(surf, color, (cx, cy + 10), (cx, cy + 30), 2)
        
        if fired:
            # Draw laser beam
            pygame.draw.line(surf, (255, 0, 0), (cx, cy), (cx, 0), 3)
            
        return surf
        
    def create_explosion_texture(self):
        """Create explosion flash texture"""
        surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        pygame.draw.circle(surf, (255, 200, 100, 180), (cx, cy), 200)
        pygame.draw.circle(surf, (255, 255, 200, 150), (cx, cy), 150)
        return surf
        
    def spawn_computer_target(self):
        """Set new random target for computer"""
        self.computer.new_x = random.randint(-90, 90)
        self.computer.new_z = random.randint(-90, 90)
        self.computer.dx = (self.computer.old_x - self.computer.new_x) / COMPSTEP
        self.computer.dz = (self.computer.old_z - self.computer.new_z) / COMPSTEP
        self.computer.old_x = self.computer.new_x
        self.computer.old_z = self.computer.new_z
        self.computer.step_count = 0
        
    def check_hit_target(self):
        """Check if player shot hits computer"""
        dist = math.sqrt((self.computer.x - self.player.x)**2 + 
                        (self.computer.z - self.player.z)**2)
        
        if dist <= self.player.look_z:
            # Calculate angle to target
            ax = self.player.look_x - self.player.x
            ay = self.player.look_y - self.player.y
            az = self.player.look_z
            ax = math.sin(self.player.angle) * self.player.look_z
            az = math.cos(self.player.angle) * self.player.look_z
            
            bx = self.computer.x - self.player.x
            bz = self.computer.z - self.player.z
            
            # Dot product for angle check
            dot = ax * bx + az * bz
            len_a = math.sqrt(ax**2 + az**2) + 0.001
            len_b = math.sqrt(bx**2 + bz**2) + 0.001
            
            cos_angle = dot / (len_a * len_b)
            
            # Hit threshold
            threshold = math.cos(4 / max(dist, 1))
            
            if cos_angle >= threshold:
                return True
        return False
        
    def check_collision(self):
        """Check player-computer collision"""
        dist = math.sqrt((self.computer.x - self.player.x)**2 + 
                        (self.computer.z - self.player.z)**2)
        if dist <= 4:
            self.player.energy -= 2
            if self.player.energy <= 0:
                self.game_over = True
            return True
        return False
        
    def update(self, dt):
        """Update game state"""
        if self.in_menu or self.game_over:
            return
            
        # Update play time
        self.time_counter += dt
        if self.time_counter >= 1000:
            self.time_counter = 0
            self.play_time += 1
            
        # Update animation
        self.anim_wait += dt
        if self.anim_wait > 40:
            self.anim_wait = 0
            self.cel_x += 1
            if self.cel_x >= self.frame_x:
                self.cel_x = 0
                self.cel_y += 1
            if self.cel_y >= self.frame_y:
                self.cel_x = 0
                self.cel_y = 0
                
        # Update computer rotation
        self.computer.rotate_x = (self.computer.rotate_x + 1) % 360
        self.computer.rotate_y = (self.computer.rotate_y + 4) % 360
        self.computer.rotate_z = (self.computer.rotate_z + 1) % 360
        
        # Move computer
        if self.computer.step_count >= COMPSTEP:
            self.spawn_computer_target()
            
        self.computer.x += self.computer.dx
        self.computer.z += self.computer.dz
        self.computer.step_count += 1
        
        # Check collision
        self.check_collision()
        
    def handle_input(self):
        """Handle keyboard input"""
        keys = pygame.key.get_pressed()
        
        if self.in_menu:
            return
            
        if self.game_over:
            if keys[pygame.K_n]:
                # New game
                self.player.energy = 100
                self.player.wins = 0
                self.computer.energy = 100
                self.game_over = False
                self.play_time = 0
                self.init_geometry()
            return
            
        # Movement
        if keys[pygame.K_UP]:
            self.player.x += self.player.step * math.sin(self.player.angle)
            self.player.z += self.player.step * math.cos(self.player.angle)
            
        if keys[pygame.K_DOWN]:
            self.player.x -= self.player.step * math.sin(self.player.angle)
            self.player.z -= self.player.step * math.cos(self.player.angle)
            
        if keys[pygame.K_RIGHT]:
            self.player.angle += self.player.delta
            if self.player.angle >= 2 * PI:
                self.player.angle -= 2 * PI
                
        if keys[pygame.K_LEFT]:
            self.player.angle -= self.player.delta
            if self.player.angle < 0:
                self.player.angle += 2 * PI
                
        # Shooting
        if keys[pygame.K_SPACE]:
            if not self.player.fire_now:
                self.player.fire_now = True
                if self.check_hit_target():
                    self.computer.energy -= 1
                    if self.computer.energy <= 0:
                        self.player.wins += 1
                        self.game_type = 2 if self.game_type == 1 else 1
                        self.load_textures()
                        self.computer.energy = 100
                        self.spawn_computer_target()
        else:
            self.player.fire_now = False
            
        # Wall collision
        if self.player.x > POLE - 2:
            self.player.x = POLE - 2
        if self.player.x < -POLE + 2:
            self.player.x = -POLE + 2
        if self.player.z > POLE - 2:
            self.player.z = POLE - 2
        if self.player.z < -POLE + 2:
            self.player.z = -POLE + 2
            
    def draw_ground(self):
        """Draw ground plane (simple 2D representation)"""
        # Draw ground gradient
        ground_y = SCREEN_H // 2
        pygame.draw.rect(self.screen, (34, 139, 34) if self.game_type == 1 else (80, 60, 40),
                        (0, ground_y, SCREEN_W, SCREEN_H - ground_y))
                        
    def draw_sky(self):
        """Draw sky"""
        sky = self.textures.get('sky')
        if sky:
            scaled = pygame.transform.scale(sky, (SCREEN_W, SCREEN_H // 2))
            self.screen.blit(scaled, (0, 0))
        else:
            pygame.draw.rect(self.screen, (135, 206, 235), (0, 0, SCREEN_W, SCREEN_H // 2))
            
    def draw_walls(self):
        """Draw walls (simplified as borders)"""
        wall_color = (139, 69, 19) if self.game_type == 1 else (100, 50, 30)
        
        # Draw walls as distant rectangles
        wall_height = 100
        horizon = SCREEN_H // 2
        
        # Front wall
        pygame.draw.rect(self.screen, wall_color, (0, horizon - wall_height, SCREEN_W, 5))
        # Back wall  
        pygame.draw.rect(self.screen, wall_color, (0, SCREEN_H - 50, SCREEN_W, 5))
        # Side walls
        pygame.draw.rect(self.screen, wall_color, (0, horizon - wall_height, 5, SCREEN_H // 2 + wall_height))
        pygame.draw.rect(self.screen, wall_color, (SCREEN_W - 5, horizon - wall_height, 5, SCREEN_H // 2 + wall_height))
        
    def draw_sprites(self, sprites: List[Sprite3D], texture):
        """Draw 3D sprites (billboard)"""
        for sprite in sprites:
            # Calculate screen position based on player position
            dx = sprite.x - self.player.x
            dz = sprite.z - self.player.z
            
            # Distance culling
            dist = math.sqrt(dx**2 + dz**2)
            if dist < 5 or dist > 150:
                continue
                
            # Angle to sprite
            angle_to_sprite = math.atan2(dx, dz)
            rel_angle = angle_to_sprite - self.player.angle
            
            # Normalize angle
            while rel_angle > PI:
                rel_angle -= 2 * PI
            while rel_angle < -PI:
                rel_angle += 2 * PI
                
            # Check if visible
            fov = PI / 2  # 90 degrees
            if abs(rel_angle) > fov:
                continue
                
            # Screen position
            screen_x = SCREEN_W // 2 + int(rel_angle / fov * SCREEN_W // 2)
            
            # Size based on distance
            size = max(10, int(2000 / dist))
            
            horizon = SCREEN_H // 2
            screen_y = horizon + int(size / 2)
            
            # Draw scaled sprite
            if texture:
                scaled = pygame.transform.scale(texture, (size, size * 2))
                self.screen.blit(scaled, (screen_x - size // 2, screen_y - size))
                
    def draw_computer(self):
        """Draw computer enemy (cube)"""
        # Calculate screen position
        dx = self.computer.x - self.player.x
        dz = self.computer.z - self.player.z
        
        dist = math.sqrt(dx**2 + dz**2)
        if dist < 5 or dist > 150:
            return
            
        angle_to = math.atan2(dx, dz)
        rel_angle = angle_to - self.player.angle
        
        while rel_angle > PI:
            rel_angle -= 2 * PI
        while rel_angle < -PI:
            rel_angle += 2 * PI
            
        fov = PI / 2
        if abs(rel_angle) > fov:
            return
            
        screen_x = SCREEN_W // 2 + int(rel_angle / fov * SCREEN_W // 2)
        size = max(20, int(3000 / dist))
        
        horizon = SCREEN_H // 2
        screen_y = horizon
        
        # Draw rotating cube (simplified as square)
        colors = [(255, 0, 0), (200, 0, 0), (150, 0, 0)]
        pygame.draw.rect(self.screen, colors[self.computer.rotate_y % 3],
                        (screen_x - size // 2, screen_y - size // 2, size, size))
        pygame.draw.rect(self.screen, (255, 255, 255),
                        (screen_x - size // 2, screen_y - size // 2, size, size), 2)
                        
    def draw_interface(self):
        """Draw HUD/craft interface"""
        # Draw crosshair
        if self.player.fire_now:
            self.screen.blit(self.craft_fired_img, (0, 0))
        else:
            self.screen.blit(self.craft_img, (0, 0))
            
        # Draw energy bars
        # Player energy (left)
        pbar_width = int(100 * (self.player.energy / 100))
        pygame.draw.rect(self.screen, (0, 255, 0), (30, 30, pbar_width, 20))
        pygame.draw.rect(self.screen, (255, 255, 255), (30, 30, 100, 20), 2)
        
        # Computer energy (right)
        cbar_width = int(100 * (self.computer.energy / 100))
        pygame.draw.rect(self.screen, (255, 0, 0), (SCREEN_W - 430, 30, cbar_width, 20))
        pygame.draw.rect(self.screen, (255, 255, 255), (SCREEN_W - 430, 30, 100, 20), 2)
        
        # Draw play time
        font = pygame.font.Font(None, 24)
        mins = self.play_time // 60
        secs = self.play_time % 60
        time_text = font.render(f"Time: {mins:02d}:{secs:02d}", True, WHITE)
        self.screen.blit(time_text, (SCREEN_W // 2 - 40, 10))
        
        # Draw wins
        wins_text = font.render(f"Kills: {self.player.wins}", True, YELLOW)
        self.screen.blit(wins_text, (SCREEN_W // 2 - 30, 30))
        
        # Draw area name
        area_name = "EARTH" if self.game_type == 1 else "HELL"
        area_text = font.render(f"Area: {area_name}", True, CYAN)
        self.screen.blit(area_text, (SCREEN_W // 2 - 40, 50))
        
    def draw_menu(self):
        """Draw main menu"""
        self.screen.fill(BLACK)
        
        # Draw title
        font_large = pygame.font.Font(None, 74)
        font_medium = pygame.font.Font(None, 36)
        
        title = font_large.render("DOOM 4D", True, RED)
        subtitle = font_medium.render("Python Port - (c) 2004 Denis Astahov", True, WHITE)
        
        self.screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 100))
        self.screen.blit(subtitle, (SCREEN_W // 2 - subtitle.get_width() // 2, 180))
        
        # Draw buttons
        button_y = 280
        button_w, button_h = 300, 60
        
        earth_rect = pygame.Rect(SCREEN_W // 2 - button_w // 2, button_y, button_w, button_h)
        pygame.draw.rect(self.screen, (0, 100, 0), earth_rect)
        pygame.draw.rect(self.screen, WHITE, earth_rect, 2)
        earth_text = font_medium.render("EARTH (Type 1)", True, WHITE)
        self.screen.blit(earth_text, (earth_rect.centerx - earth_text.get_width() // 2, 
                                       earth_rect.centery - earth_text.get_height() // 2))
        
        hell_rect = pygame.Rect(SCREEN_W // 2 - button_w // 2, button_y + 80, button_w, button_h)
        pygame.draw.rect(self.screen, (100, 0, 0), hell_rect)
        pygame.draw.rect(self.screen, WHITE, hell_rect, 2)
        hell_text = font_medium.render("HELL (Type 2)", True, WHITE)
        self.screen.blit(hell_text, (hell_rect.centerx - hell_text.get_width() // 2,
                                     hell_rect.centery - hell_text.get_height() // 2))
        
        # Video mode
        mode_text = font_medium.render(f"Resolution: {SCREEN_W}x{SCREEN_H}", True, YELLOW)
        self.screen.blit(mode_text, (SCREEN_W // 2 - mode_text.get_width() // 2, 500))
        
        # Instructions
        inst = font_medium.render("Press E for Earth, H for Hell, or click buttons", True, CYAN)
        self.screen.blit(inst, (SCREEN_W // 2 - inst.get_width() // 2, 600))
        
        return earth_rect, hell_rect
        
    def draw_game_over(self):
        """Draw game over screen"""
        # Darken screen
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        
        font_large = pygame.font.Font(None, 74)
        font_medium = pygame.font.Font(None, 36)
        
        title = font_large.render("GAME OVER", True, RED)
        self.screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 150))
        
        # Stats
        kills = font_medium.render(f"You killed the monster {self.player.wins} times!", True, WHITE)
        mins = self.play_time // 60
        time_played = font_medium.render(f"Play time: {mins} minutes", True, WHITE)
        
        self.screen.blit(kills, (SCREEN_W // 2 - kills.get_width() // 2, 300))
        self.screen.blit(time_played, (SCREEN_W // 2 - time_played.get_width() // 2, 340))
        
        # Instructions
        new_game = font_medium.render("Press N for New Game", True, MAGENTA)
        exit_text = font_medium.render("Press ESC to Exit", True, MAGENTA)
        
        self.screen.blit(new_game, (SCREEN_W // 2 - new_game.get_width() // 2, 500))
        self.screen.blit(exit_text, (SCREEN_W // 2 - exit_text.get_width() // 2, 540))
        
        credit = font_medium.render("Created by Denis Astahov (c) 2004", True, YELLOW)
        self.screen.blit(credit, (SCREEN_W // 2 - credit.get_width() // 2, 650))
        
    def draw(self):
        """Main draw function"""
        if self.in_menu:
            self.earth_rect, self.hell_rect = self.draw_menu()
            pygame.display.flip()
            return
            
        self.draw_sky()
        self.draw_ground()
        self.draw_walls()
        
        # Draw sprites
        self.draw_sprites(self.trees1, self.textures.get('tree1'))
        self.draw_sprites(self.trees2, self.textures.get('tree2'))
        self.draw_sprites(self.smokes, self.textures.get('smoke'))
        self.draw_sprites(self.fires, self.textures.get('fire'))
        
        # Draw computer
        self.draw_computer()
        
        # Draw interface
        self.draw_interface()
        
        # Draw game over if needed
        if self.game_over:
            self.draw_game_over()
            
        pygame.display.flip()
        
    def run(self):
        """Main game loop"""
        while self.running:
            dt = self.clock.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_over or self.in_menu:
                            self.running = False
                        else:
                            self.game_over = True
                            
                    if self.in_menu:
                        if event.key == pygame.K_e:
                            self.game_type = 1
                            self.start_game()
                        elif event.key == pygame.K_h:
                            self.game_type = 2
                            self.start_game()
                            
                    elif self.game_over:
                        if event.key == pygame.K_n:
                            self.player.energy = 100
                            self.player.wins = 0
                            self.computer.energy = 100
                            self.game_over = False
                            self.play_time = 0
                            self.init_geometry()
                            
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.in_menu:
                        pos = pygame.mouse.get_pos()
                        if hasattr(self, 'earth_rect') and self.earth_rect.collidepoint(pos):
                            self.game_type = 1
                            self.start_game()
                        elif hasattr(self, 'hell_rect') and self.hell_rect.collidepoint(pos):
                            self.game_type = 2
                            self.start_game()
                            
            if not self.in_menu:
                self.handle_input()
                self.update(dt)
                
            self.draw()
            
        pygame.quit()
        
    def start_game(self):
        """Start new game"""
        self.in_menu = False
        self.game_over = False
        self.player = Player()
        self.computer = Computer()
        self.play_time = 0
        self.load_textures()
        self.init_geometry()
        

def main():
    game = Doom4D()
    game.run()
    

if __name__ == "__main__":
    main()
