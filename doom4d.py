#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          D O O M   4 D   —   P y t h o n   P o r t          ║
║                                                              ║
║  Original: VB6 + DirectX 7  by Denis Astahov  (c) 2004      ║
║  Score: 95/100  Bachelor Degree Final Project                ║
║  Python Port: pygame + PyOpenGL  (Python 3.14+)              ║
╚══════════════════════════════════════════════════════════════╝

Controls:
  Arrow Keys  ─ Move / Turn
  Space       ─ Shoot laser
  F12         ─ Teleport (switch Earth ↔ Death)
  F1–F10      ─ Switch music track
  F11         ─ Stop music
  N           ─ New game  (on Game Over screen)
  ESC         ─ Quit
"""

import sys
import os
import math
import random
import time

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame
from pygame.locals import DOUBLEBUF, OPENGL, KEYDOWN, KEYUP, QUIT

try:
    from OpenGL.GL import (
        glEnable, glDisable, glClear, glClearColor, glClearDepth,
        glDepthFunc, glBlendFunc, glViewport, glLoadIdentity,
        glAlphaFunc,
        glMatrixMode, glPushMatrix, glPopMatrix, glTranslatef,
        glRotatef, glScalef, glMultMatrixf, glOrtho,
        glBegin, glEnd, glVertex3f, glTexCoord2f, glColor4f,
        glGenTextures, glBindTexture, glTexImage2D,
        glTexParameteri, glTexParameterfv,
        glFogi, glFogf, glFogfv,
        glRasterPos2f, glDrawPixels,
        glShadeModel,
        GL_TEXTURE_2D, GL_RGBA, GL_UNSIGNED_BYTE,
        GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER,
        GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T,
        GL_LINEAR, GL_NEAREST, GL_REPEAT, GL_CLAMP_TO_EDGE,
        GL_DEPTH_TEST, GL_BLEND, GL_CULL_FACE,
        GL_LEQUAL, GL_LESS, GL_GREATER,
        GL_ALPHA_TEST,
        GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE,
        GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
        GL_MODELVIEW, GL_PROJECTION, GL_TEXTURE,
        GL_TRIANGLE_STRIP, GL_QUADS, GL_TRIANGLES,
        GL_FOG, GL_FOG_MODE, GL_FOG_DENSITY, GL_FOG_COLOR,
        GL_FOG_START, GL_FOG_END,
        GL_EXP, GL_EXP2, GL_LINEAR as GL_FOG_LINEAR,
        GL_LIGHTING, GL_SMOOTH,
    )
    from OpenGL.GLU import gluPerspective, gluLookAt
except ImportError:
    print("PyOpenGL missing. Run:  pip install PyOpenGL PyOpenGL_accelerate")
    sys.exit(1)

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("Pillow / numpy missing. Run:  pip install Pillow numpy")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
IMG  = lambda *p: os.path.join(BASE, "Image", *p)
SND  = lambda f:  os.path.join(BASE, "Sound", f)
MUS  = lambda f:  os.path.join(BASE, "Music",  f)

# ─────────────────────────────────────────────────────────────────────────────
# Constants  (mirror the VB6 source exactly)
# ─────────────────────────────────────────────────────────────────────────────
COMPSTEP  = 100
TREE_MAX  = 40
FIRESMOKE = 40
PI        = math.pi
DEG       = PI / 180
POLE      = 200          # half-arena size in world units
ZZZ       = POLE / 100  # = 2.0 – geometry zoom factor (from vb6: POLE/100)
FRAME_X   = 5           # animation sprite columns
FRAME_Y   = 4           # animation sprite rows

# Resolutions (mirroring VB6 FormMenu VideoMode ComboBox exactly)
RESOLUTIONS = [
    (1280, 1024, "1280 × 1024"),              # default (original VB6 max)
    (1920, 1080, "1920 × 1080  Full HD"),
    (2560, 1440, "2560 × 1440  2K"),
    (3840, 2160, "3840 × 2160  4K Ultra HD"),
]
_res_index = 0   # 1280×1024 default

SCREEN_W: int = RESOLUTIONS[_res_index][0]
SCREEN_H: int = RESOLUTIONS[_res_index][1]

FOV  = 90.0
NEAR = 1.0
FAR  = 2000.0


def set_resolution(index: int):
    """Apply the chosen resolution to the global SCREEN_W / SCREEN_H."""
    global SCREEN_W, SCREEN_H, _res_index
    _res_index = index % len(RESOLUTIONS)
    SCREEN_W   = RESOLUTIONS[_res_index][0]
    SCREEN_H   = RESOLUTIONS[_res_index][1]

# ─────────────────────────────────────────────────────────────────────────────
# Texture utilities
# ─────────────────────────────────────────────────────────────────────────────
_tex_cache: dict[str, int] = {}


def load_tex(path: str, black_key: bool = False) -> int:
    """Load an image into an OpenGL texture; optionally make black → transparent."""
    if path in _tex_cache:
        return _tex_cache[path]

    try:
        img = Image.open(path).convert("RGBA")
    except Exception:
        # 1×1 bright-magenta fallback so missing textures are obvious
        tex_id = int(glGenTextures(1))
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1, 1, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, b"\xff\x00\xff\xff")
        _tex_cache[path] = tex_id
        return tex_id

    arr = np.array(img, dtype=np.uint8)   # row 0 = image top → V=0 = image top (consistent)
    if black_key:
        mask = (arr[:, :, 0] < 12) & (arr[:, :, 1] < 12) & (arr[:, :, 2] < 12)
        arr[mask, 3] = 0

    tex_id = int(glGenTextures(1))
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                 img.width, img.height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, arr.tobytes())
    _tex_cache[path] = tex_id
    return tex_id


# ─────────────────────────────────────────────────────────────────────────────
# Sound utilities
# ─────────────────────────────────────────────────────────────────────────────
_snd_cache: dict[str, pygame.mixer.Sound] = {}


def extract_mp3_from_wav(wav_path: str) -> str:
    """
    Music files are WAVE containers holding raw MPEG Layer-3 data (fmt 0x0055).
    pygame.mixer cannot play this hybrid format directly — extract the MP3 payload
    once and cache it alongside the original file as a proper .mp3.
    Returns the path to the usable .mp3 file (or original path on failure).
    """
    import struct
    mp3_path = wav_path.rsplit(".", 1)[0] + ".mp3"
    if os.path.exists(mp3_path):
        return mp3_path
    try:
        with open(wav_path, "rb") as f:
            raw = f.read()
        # Verify RIFF/WAVE header and MP3 format code (0x0055)
        if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
            return wav_path
        fmt_code = struct.unpack_from("<H", raw, 20)[0]
        if fmt_code != 0x0055:          # not MP3-in-WAV — play as-is
            return wav_path
        # Walk chunks to find the 'data' chunk containing the raw MP3 frames
        pos = 12
        while pos < len(raw) - 8:
            chunk_id   = raw[pos:pos+4]
            chunk_size = struct.unpack_from("<I", raw, pos+4)[0]
            if chunk_id == b"data":
                with open(mp3_path, "wb") as f:
                    f.write(raw[pos+8 : pos+8+chunk_size])
                return mp3_path
            pos += 8 + chunk_size + (chunk_size % 2)   # word-aligned
    except Exception:
        pass
    return wav_path


def play_sound(filename: str):
    path = SND(filename)
    if not os.path.exists(path):
        return
    try:
        if path not in _snd_cache:
            _snd_cache[path] = pygame.mixer.Sound(path)
        _snd_cache[path].play()
    except Exception:
        pass


def play_music(filename: str):
    """Load and loop a music track. Handles MP3-in-WAV containers transparently."""
    path = MUS(filename)
    if not os.path.exists(path):
        return
    try:
        # Auto-extract MP3 payload if this is a WAVE/MP3 hybrid file
        playable = extract_mp3_from_wav(path) if path.lower().endswith(".wav") else path
        pygame.mixer.music.load(playable)
        pygame.mixer.music.play(-1)
    except Exception as e:
        print(f"[music] {filename}: {e}")


def stop_music():
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# OpenGL draw primitives
# ─────────────────────────────────────────────────────────────────────────────
def _quad_strip(verts):
    """Draw a GL_TRIANGLE_STRIP from 4 (u,v,x,y,z) tuples."""
    glBegin(GL_TRIANGLE_STRIP)
    for (u, v, x, y, z) in verts:
        glTexCoord2f(u, v)
        glVertex3f(x, y, z)
    glEnd()


def draw_hplane(x1, z1, x2, z2, y):
    """Horizontal quad: ground / sky / lower-floor."""
    _quad_strip([
        (0, 0, x1, y, z1),
        (1, 0, x2, y, z1),
        (0, 1, x1, y, z2),
        (1, 1, x2, y, z2),
    ])


def draw_vquad_z(x1, x2, z, y_top=30, y_bot=0):
    """Vertical quad parallel to X axis (front/back walls)."""
    _quad_strip([
        (0, 0, x1, y_top, z),
        (1, 0, x2, y_top, z),
        (0, 1, x1, y_bot, z),
        (1, 1, x2, y_bot, z),
    ])


def draw_vquad_x(x, z1, z2, y_top=30, y_bot=0):
    """Vertical quad parallel to Z axis (left/right walls)."""
    _quad_strip([
        (0, 0, x, y_top, z1),
        (1, 0, x, y_top, z2),
        (0, 1, x, y_bot, z1),
        (1, 1, x, y_bot, z2),
    ])


def draw_sprite_cross(x, z, height, width, u1=0.0, v1=0.0, u2=1.0, v2=1.0):
    """
    Two crossed billboard quads (as in the VB6 Create_SPRITE3D routine).
    Each plane rendered twice (front & back) since CULL_FACE is off.
    """
    # Plane 1: along X
    _quad_strip([(u1,v1,x-width,height,z),(u2,v1,x+width,height,z),
                 (u1,v2,x-width,0,z),    (u2,v2,x+width,0,z)])
    _quad_strip([(u1,v1,x+width,height,z),(u2,v1,x-width,height,z),
                 (u1,v2,x+width,0,z),    (u2,v2,x-width,0,z)])
    # Plane 2: along Z
    _quad_strip([(u1,v1,x,height,z-width),(u2,v1,x,height,z+width),
                 (u1,v2,x,0,    z-width), (u2,v2,x,0,    z+width)])
    _quad_strip([(u1,v1,x,height,z+width),(u2,v1,x,height,z-width),
                 (u1,v2,x,0,    z+width), (u2,v2,x,0,    z-width)])


def draw_cube(half=10):
    """Textured cube. Used for the enemy. Vertices mirror VB6 Init_ComputerOBJ."""
    s = half
    faces = [
        # front
        [(0,0,-s,-s,-s),(1,0,-s, s,-s),(0,1, s,-s,-s),(1,1, s, s,-s)],
        # right
        [(0,0, s,-s,-s),(1,0, s, s,-s),(0,1, s,-s, s),(1,1, s, s, s)],
        # back
        [(0,0, s,-s, s),(1,0, s, s, s),(0,1,-s,-s, s),(1,1,-s, s, s)],
        # left
        [(0,0,-s,-s, s),(1,0,-s, s, s),(0,1,-s,-s,-s),(1,1,-s, s,-s)],
        # top
        [(0,0,-s, s,-s),(1,0,-s, s, s),(0,1, s, s,-s),(1,1, s, s, s)],
        # bottom
        [(0,0,-s,-s, s),(1,0,-s,-s,-s),(0,1, s,-s, s),(1,1, s,-s,-s)],
    ]
    for face in faces:
        _quad_strip(face)


def draw_fullscreen_quad(tex_id, alpha=1.0):
    """Draw texture over the entire screen in 2-D orthographic mode."""
    global SCREEN_W, SCREEN_H
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, SCREEN_W, SCREEN_H, 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glColor4f(1, 1, 1, alpha)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex3f(0,        0,        0)   # top-left    → V=0 = image top
    glTexCoord2f(1, 0); glVertex3f(SCREEN_W, 0,        0)   # top-right
    glTexCoord2f(1, 1); glVertex3f(SCREEN_W, SCREEN_H, 0)   # bottom-right → V=1 = image bottom
    glTexCoord2f(0, 1); glVertex3f(0,        SCREEN_H, 0)   # bottom-left
    glEnd()

    glEnable(GL_DEPTH_TEST)
    glDisable(GL_BLEND)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_rect_2d(x1, y1, x2, y2, tex_id,
                 tx1=0.0, ty1=0.0, tx2=1.0, ty2=1.0, alpha=1.0):
    """Draw a 2-D textured rectangle (for HUD elements)."""
    global SCREEN_W, SCREEN_H
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, SCREEN_W, SCREEN_H, 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glColor4f(1, 1, 1, alpha)
    glBegin(GL_QUADS)
    glTexCoord2f(tx1, ty1); glVertex3f(x1, y1, 0)   # top-left    → ty1 = image top
    glTexCoord2f(tx2, ty1); glVertex3f(x2, y1, 0)   # top-right
    glTexCoord2f(tx2, ty2); glVertex3f(x2, y2, 0)   # bottom-right → ty2 = image bottom
    glTexCoord2f(tx1, ty2); glVertex3f(x1, y2, 0)   # bottom-left
    glEnd()

    glEnable(GL_DEPTH_TEST)
    glDisable(GL_BLEND)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


# ─────────────────────────────────────────────────────────────────────────────
# Game state  (all mutable fields, mirrors VB6 module-level Dims)
# ─────────────────────────────────────────────────────────────────────────────
class GS:
    game_type: int   = 1    # 1=Earth  2=Death
    area:      str   = "Earth"

    # Camera / player
    cam_x:  float = 0.0
    cam_y:  float = 6.0     # constant eye height
    cam_z:  float = -12.0
    see_x:  float = 0.0
    see_y:  float = 6.0
    see_z:  float = 70.0    # dist2focus = 70
    dist2focus: float = 70.0
    step:   float = 0.5001
    alfa:   float = 0.0
    delta:  float = 0.8 * DEG

    # Enemy / computer
    xm: float = 0.0        # enemy world X
    zm: float = 0.0        # enemy world Z
    comp_new_x: int = 0
    comp_new_z: int = 0
    comp_old_x: int = 0
    comp_old_z: int = 0
    cstep: int = COMPSTEP
    dx: float = 0.0
    dz: float = 0.0

    # Rotation accumulators (degrees, 0-360)
    rot_x: float = 0.0
    rot_y: float = 0.0
    rot_z: float = 0.0

    # Energies
    cmp_energy: int = 100
    ply_energy: int = 100
    player_win: int = 0

    # Flags
    quit_game:   bool = False
    start_yes:   bool = False
    vistrel_now: bool = False  # shot-in-progress guard

    # Time
    play_time: int = 0    # seconds
    _last_sec: int = 0    # ms at last second tick

    # Fog
    fog_on:    bool = False
    fog_mode:  int  = GL_EXP
    fog_color: tuple = (0.0, 0.0, 0.0, 1.0)

    # Animation frame
    cel_x: int = 0
    cel_y: int = 0
    _anim_tick: int = 0

    # Sprite lists  [(x, z, height, width), ...]
    trees1: list = []
    trees2: list = []
    smokes: list = []
    faires: list = []

    # Textures
    tex: dict = {}


gs = GS()


def gs_reset_player():
    """Reset player state for a new game."""
    gs.cam_x, gs.cam_y, gs.cam_z = 0.0, 6.0, -12.0
    gs.see_x, gs.see_y, gs.see_z = 0.0, 6.0, gs.cam_z + gs.dist2focus
    gs.alfa = 0.0
    gs.ply_energy = 100
    gs.cmp_energy = 100
    gs.play_time  = 0
    gs._last_sec  = pygame.time.get_ticks()
    gs.vistrel_now = False
    gs.quit_game   = False
    gs.start_yes   = False
    gs.xm = gs.zm  = 0.0
    gs.comp_old_x  = gs.comp_old_z = 0
    gs.cstep       = COMPSTEP
    gs.fog_on      = False


# ─────────────────────────────────────────────────────────────────────────────
# Texture loading
# ─────────────────────────────────────────────────────────────────────────────
def load_textures():
    _tex_cache.clear()
    area = gs.area
    t = gs.tex

    def L(key, *path, bk=False):
        t[key] = load_tex(IMG(*path), black_key=bk)

    L("ground",  area, "Ground.jpg")
    # Sky — Earth uses Nebo.jpg (lowercase), Death uses Nebo.JPG (uppercase)
    nebo_file = "Nebo.jpg" if os.path.exists(IMG(area, "Nebo.jpg")) else "Nebo.JPG"
    L("sky", area, nebo_file)
    L("wall1",   area, "Stena1.bmp", bk=True)
    L("wall2",   area, "Stena2.bmp", bk=True)

    nizz_file = "Nizz.JPG" if os.path.exists(IMG(area, "Nizz.JPG")) else "Nizz.jpg"
    L("nizz", area, nizz_file)

    if gs.game_type == 1:
        L("tree1", area, "Tree1.bmp", bk=True)
        L("tree2", area, "Tree1.bmp", bk=True)
        L("smoke", area, "Smoke.bmp", bk=True)
        L("faire", area, "Smoke.bmp", bk=True)
    else:
        L("tree1", area, "Tree2.bmp", bk=True)
        L("tree2", area, "Tree2.bmp", bk=True)
        # Death area has Faire.bmp only (no Smoke.bmp)
        faire_path = IMG(area, "Faire.bmp")
        L("smoke", area, "Faire.bmp", bk=True)
        L("faire", area, "Faire.bmp", bk=True)

    L("comp",       "CompKub.BMP", bk=True)
    L("expl",       "Expl.bmp",    bk=True)
    L("gameover",   "GameOver.jpg")
    L("craft",      "CraftStain.bmp", bk=True)
    L("craftfired", "CraftFired.bmp", bk=True)
    L("energy_ply", "EnergyPLY.bmp")
    L("energy_cmp", "EnergyCMP.bmp")
    L("logo",       "IntroD4D.bmp",   bk=True)

    intro_path = IMG(area, "Intro1.jpg")
    L("intro1", area, "Intro1.jpg")


# ─────────────────────────────────────────────────────────────────────────────
# Sprites
# ─────────────────────────────────────────────────────────────────────────────
def init_sprites():
    rr = lambda a, b: random.randint(a, b)
    gs.trees1 = [(rr(-95, 95), rr(-95, 95), 20, 3)  for _ in range(TREE_MAX)]
    gs.trees2 = [(rr(-95, 95), rr(-95, 95), 12, 5)  for _ in range(TREE_MAX)]
    gs.smokes = [(rr(-98, 98), rr(-98, 98),  3, 1)  for _ in range(FIRESMOKE)]
    gs.faires = [(rr(-98, 98), rr(-98, 98),  3, 1)  for _ in range(FIRESMOKE)]


# ─────────────────────────────────────────────────────────────────────────────
# Fog control
# ─────────────────────────────────────────────────────────────────────────────
def apply_fog():
    if gs.fog_on:
        glEnable(GL_FOG)
        glFogi(GL_FOG_MODE,    gs.fog_mode)
        glFogf(GL_FOG_DENSITY, 0.004)
        glFogfv(GL_FOG_COLOR,  gs.fog_color)
        glFogf(GL_FOG_START,   10.0)
        glFogf(GL_FOG_END,     800.0)
    else:
        glDisable(GL_FOG)


# ─────────────────────────────────────────────────────────────────────────────
# Animation frame advance  (mirror VB6: every 40 ms advance one frame)
# ─────────────────────────────────────────────────────────────────────────────
def advance_anim():
    now = pygame.time.get_ticks()
    if now >= gs._anim_tick + 40:
        gs._anim_tick = now
        gs.cel_x += 1
        if gs.cel_x >= FRAME_X:
            gs.cel_x = 0
            gs.cel_y += 1
        if gs.cel_y >= FRAME_Y:
            gs.cel_x = gs.cel_y = 0


def anim_uvs():
    """UV sub-rect for current animation frame."""
    u1 = gs.cel_x / FRAME_X
    v1 = gs.cel_y / FRAME_Y
    return u1, v1, u1 + 1/FRAME_X, v1 + 1/FRAME_Y


# ─────────────────────────────────────────────────────────────────────────────
# 3-D scene rendering
# ─────────────────────────────────────────────────────────────────────────────
def render_world():
    """Draw the textured arena (ground, walls, sky, trees, fire/smoke)."""
    t  = gs.tex
    sz = 20   # wall segment width in model space

    glEnable(GL_TEXTURE_2D)
    glColor4f(1, 1, 1, 1)

    glPushMatrix()
    glScalef(ZZZ, ZZZ, ZZZ)     # scale geometry ×2 (ZZZ = POLE/100 = 2)

    # Ground  ─100..100 model → ─200..200 world
    glBindTexture(GL_TEXTURE_2D, t["ground"])
    draw_hplane(-100, 100, 100, -100, 0)

    # Sky (Nebo)
    glBindTexture(GL_TEXTURE_2D, t["sky"])
    draw_hplane(250, 250, -250, -250, 50)

    # Walls — enable alpha-test so black (transparent) pixels are fully discarded.
    # This replicates DirectX COLORKEYENABLE behaviour: transparent wall pixels
    # write nothing to the colour buffer or depth buffer, allowing the NIZZ
    # floor drawn afterward to show through the gaps at the wall bases.
    glEnable(GL_ALPHA_TEST)
    glAlphaFunc(GL_GREATER, 0.0)          # discard pixels where alpha == 0

    # WALL1 – back   (z = +100 model)
    glBindTexture(GL_TEXTURE_2D, t["wall1"])
    for i in range(10):
        draw_vquad_z(-100 + i*sz, -80 + i*sz,  100)
    # WALL2 – front  (z = -100)
    for i in range(10):
        draw_vquad_z(-80 + i*sz,  -100 + i*sz, -100)

    # WALL3 – right  (x = +100)
    glBindTexture(GL_TEXTURE_2D, t["wall2"])
    for i in range(10):
        draw_vquad_x( 100, -80 + i*sz, -100 + i*sz)
    # WALL4 – left   (x = -100)
    for i in range(10):
        draw_vquad_x(-100, -100 + i*sz, -80 + i*sz)

    glDisable(GL_ALPHA_TEST)

    # Trees (alpha-blended crossed billboards)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glBindTexture(GL_TEXTURE_2D, t["tree1"])
    for (tx, tz, th, tw) in gs.trees1:
        draw_sprite_cross(tx, tz, th, tw)

    glBindTexture(GL_TEXTURE_2D, t["tree2"])
    for (tx, tz, th, tw) in gs.trees2:
        draw_sprite_cross(tx, tz, th, tw)

    # Animated fire / smoke
    advance_anim()
    u1, v1, u2, v2 = anim_uvs()

    glBindTexture(GL_TEXTURE_2D, t["smoke"])
    for (sx, sz_, sh, sw) in gs.smokes:
        draw_sprite_cross(sx, sz_, sh, sw, u1, v1, u2, v2)

    glBindTexture(GL_TEXTURE_2D, t["faire"])
    for (fx, fz, fh, fw) in gs.faires:
        draw_sprite_cross(fx, fz, fh, fw, u1, v1, u2, v2)

    glDisable(GL_BLEND)
    glPopMatrix()

    # ── Lower floor (Nizz) ────────────────────────────────────────────────────
    # Rotate the UV coords in texture-matrix space so the floor pattern
    # visibly spins from any viewing angle (geometry Y-rotation is imperceptible
    # on a symmetric horizontal plane viewed nearly edge-on from camera height).
    glMatrixMode(GL_TEXTURE)
    glLoadIdentity()
    glTranslatef(0.5, 0.5, 0.0)             # pivot around texture centre
    glRotatef(gs.rot_x * 3.0, 0.0, 0.0, 1.0)  # spin UV at 3× speed (clearly visible)
    glTranslatef(-0.5, -0.5, 0.0)
    glMatrixMode(GL_MODELVIEW)

    glPushMatrix()
    glScalef(ZZZ, ZZZ, ZZZ)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, t["nizz"])
    glColor4f(1, 1, 1, 1)
    draw_hplane(-500, 500, 500, -500, -10)
    glPopMatrix()

    # Reset texture matrix so nothing else is affected
    glMatrixMode(GL_TEXTURE)
    glLoadIdentity()
    glMatrixMode(GL_MODELVIEW)


def render_enemy():
    """Draw the rotating textured enemy cube (from VB6 Init_ComputerOBJ)."""
    # VB6 transform chain (D3D row-vector convention reversed for OpenGL):
    #   Scale(0.25) → RotX → RotZ → RotY → Translate(xm, y-2, zm)
    glPushMatrix()
    glTranslatef(gs.xm, gs.cam_y - 2, gs.zm)
    glRotatef(gs.rot_y, 0, 1, 0)
    glRotatef(gs.rot_z, 0, 0, 1)
    glRotatef(gs.rot_x, 1, 0, 0)
    glScalef(0.25, 0.25, 0.25)   # cube half-size = 10 → 2.5 world units
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, gs.tex["comp"])
    glColor4f(1, 1, 1, 1)
    draw_cube(10)
    glPopMatrix()


# ─────────────────────────────────────────────────────────────────────────────
# HUD  (2-D overlay rendered after 3-D scene)
# ─────────────────────────────────────────────────────────────────────────────
def render_hud(firing: bool, show_expl: bool):
    global SCREEN_W, SCREEN_H
    t = gs.tex

    # Full-screen craft overlay (crosshair / HUD border)
    craft_tex = t["craftfired"] if firing else t["craft"]
    draw_fullscreen_quad(craft_tex)

    # Explosion flash
    if show_expl:
        draw_fullscreen_quad(t["expl"], alpha=0.75)

    # Energy bars
    # CraftStain.bmp / CraftFired.bmp are 500×400 px.
    # VB6 formula: ScreenW / CraftDsc.lWidth * pixel_offset  (faithfully reproduced)
    CRAFT_W, CRAFT_H = 500, 400
    bar_h_top = int(SCREEN_H * 30  / CRAFT_H)
    bar_h_bot = int(SCREEN_H * 50  / CRAFT_H)
    ply_x1    = int(SCREEN_W * 30  / CRAFT_W)
    ply_x2    = int(SCREEN_W * (gs.ply_energy + 30) / CRAFT_W)
    draw_rect_2d(ply_x1, bar_h_top, ply_x2, bar_h_bot, t["energy_ply"],
                 tx2=gs.ply_energy / 100)

    # Computer bar – right side (x = 370/CraftW * ScreenW)
    cmp_x1 = int(SCREEN_W * 370 / CRAFT_W)
    cmp_x2 = int(SCREEN_W * (gs.cmp_energy + 370) / CRAFT_W)
    draw_rect_2d(cmp_x1, bar_h_top, cmp_x2, bar_h_bot, t["energy_cmp"],
                 tx2=gs.cmp_energy / 100)


# ─────────────────────────────────────────────────────────────────────────────
# Input / movement  (mirrors VB6 Make_Move + Read_Keys)
# ─────────────────────────────────────────────────────────────────────────────
def make_move(keys):
    """Update camera position & look-at from keyboard state."""
    s  = gs.step
    d  = gs.dist2focus
    a  = gs.alfa
    da = gs.delta
    cx, cy, cz = gs.cam_x, gs.cam_y, gs.cam_z

    if keys[pygame.K_UP]:
        cx += s * math.sin(a)
        cz += s * math.cos(a)
    if keys[pygame.K_DOWN]:
        cx -= s * math.sin(a)
        cz -= s * math.cos(a)
    if keys[pygame.K_RIGHT]:
        a  -= da          # DirectX left-hand vs OpenGL right-hand: sign flipped
        if abs(a) >= 2*PI:
            a  = 0.0
    if keys[pygame.K_LEFT]:
        a  += da
        if abs(a) >= 2*PI:
            a  = 0.0

    # Fog toggles  (mirror Z/W/Q, 1/2/3)
    if keys[pygame.K_z]:
        gs.fog_on = False
    if keys[pygame.K_w]:
        gs.fog_color = (1.0, 1.0, 1.0, 1.0)
        gs.fog_on    = True
    if keys[pygame.K_q]:
        gs.fog_color = (0.0, 0.0, 0.1, 1.0)
        gs.fog_on    = True
    if keys[pygame.K_1]:
        gs.fog_mode  = GL_FOG_LINEAR
    if keys[pygame.K_2]:
        gs.fog_mode  = GL_EXP
    if keys[pygame.K_3]:
        gs.fog_mode  = GL_EXP2

    # Wall collision (boundary = POLE - 2 = 198 world units)
    hit_wall = False
    if cx >  POLE - 2:
        cx =  POLE - 2;  hit_wall = True
    if cx < -(POLE - 2):
        cx = -(POLE - 2); hit_wall = True
    if cz >  POLE - 2:
        cz =  POLE - 2;  hit_wall = True
    if cz < -(POLE - 2):
        cz = -(POLE - 2); hit_wall = True
    if hit_wall:
        play_sound("Nothink.wav")

    # Write back
    gs.cam_x, gs.cam_y, gs.cam_z = cx, cy, cz
    gs.alfa = a
    gs.see_x = cx + d * math.sin(a)
    gs.see_y = cy
    gs.see_z = cz + d * math.cos(a)


# ─────────────────────────────────────────────────────────────────────────────
# Enemy AI  (mirrors VB6 Move_Computer + CheckDamage)
# ─────────────────────────────────────────────────────────────────────────────
def move_enemy():
    if gs.cstep >= COMPSTEP:
        # Pick a new random target in ±90 model space (= ±180 world via ZZZ)
        # Original uses -90..90 model-space range, no extra scaling here
        gs.comp_new_x = random.randint(-90, 90)
        gs.comp_new_z = random.randint(-90, 90)
        gs.dx = (gs.comp_old_x - gs.comp_new_x) / COMPSTEP
        gs.dz = (gs.comp_old_z - gs.comp_new_z) / COMPSTEP
        gs.comp_old_x = gs.comp_new_x
        gs.comp_old_z = gs.comp_new_z
        gs.cstep = 0

    gs.xm += gs.dx
    gs.zm += gs.dz
    gs.cstep += 1

    check_damage()


def check_damage():
    """If enemy touches player, reduce player energy."""
    dist = math.hypot(gs.xm - gs.cam_x, gs.zm - gs.cam_z)
    if dist <= 4:
        play_sound("Pain.wav")
        gs.ply_energy = max(0, gs.ply_energy - 2)
        if gs.ply_energy == 0:
            gs.quit_game = True


# ─────────────────────────────────────────────────────────────────────────────
# Shooting  (mirrors VB6 CheckHitTarget)
# ─────────────────────────────────────────────────────────────────────────────
def check_hit_target() -> bool:
    """Return True if shot landed on enemy."""
    dist = math.hypot(gs.xm - gs.cam_x, gs.zm - gs.cam_z)
    if dist > gs.dist2focus:
        return False

    # View vector A = camera look-at − camera eye
    Ax = gs.see_x - gs.cam_x
    Ay = gs.see_y - gs.cam_y
    Az = gs.see_z - gs.cam_z

    # Vector B = enemy − camera
    Bx = gs.xm - gs.cam_x
    By = 0.0
    Bz = gs.zm - gs.cam_z

    mag_A = math.sqrt(Ax*Ax + Ay*Ay + Az*Az)
    mag_B = math.sqrt(Bx*Bx + By*By + Bz*Bz)
    if mag_A < 1e-9 or mag_B < 1e-9:
        return False

    cos_alfa  = (Ax*Bx + Ay*By + Az*Bz) / (mag_A * mag_B)
    threshold = math.cos(4.0 / dist)   # VB6: Cos(4 / dist2target)
    return cos_alfa >= threshold


def change_area():
    gs.game_type = 2 if gs.game_type == 1 else 1
    gs.area      = "Earth" if gs.game_type == 1 else "Death"
    load_textures()
    init_sprites()


# ─────────────────────────────────────────────────────────────────────────────
# Timer tick  (mirrors VB6 TimerPlayTime_Timer + TimerIntro fog logic)
# ─────────────────────────────────────────────────────────────────────────────
def tick_play_time():
    now = pygame.time.get_ticks()
    if now - gs._last_sec >= 1000:
        gs._last_sec = now
        gs.play_time += 1
        t = gs.play_time

        # VB6 timer fog schedule (unchanged)
        if t in (60, 300):
            gs.fog_color = (1.0, 1.0, 1.0, 1.0)
            gs.fog_mode  = GL_EXP2
            gs.fog_on    = True
        elif t in (180, 400):
            gs.fog_color = (0.0, 0.0, 0.1, 1.0)
            gs.fog_mode  = GL_EXP2
            gs.fog_on    = True
        elif t in (120, 500):
            gs.fog_on    = False


# ─────────────────────────────────────────────────────────────────────────────
# Rotation increments  (1/4/1 per frame matching VB6)
# ─────────────────────────────────────────────────────────────────────────────
def tick_rotations():
    gs.rot_x = (gs.rot_x + 1) % 360
    gs.rot_y = (gs.rot_y + 4) % 360
    gs.rot_z = (gs.rot_z + 1) % 360


# ─────────────────────────────────────────────────────────────────────────────
# OpenGL one-time setup
# ─────────────────────────────────────────────────────────────────────────────
def setup_gl():
    global SCREEN_W, SCREEN_H
    glClearColor(0, 0, 0, 1)
    glClearDepth(1.0)
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glDisable(GL_LIGHTING)
    glDisable(GL_CULL_FACE)
    glShadeModel(GL_SMOOTH)  # Gouraud shading (mirrors VB6 D3DSHADE_GOURAUD)

    # Texture filtering (bilinear, mirrors VB6 D3DTFG_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    glViewport(0, 0, SCREEN_W, SCREEN_H)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV, SCREEN_W / SCREEN_H, NEAR, FAR)
    glMatrixMode(GL_MODELVIEW)


# ─────────────────────────────────────────────────────────────────────────────
# Menu screen  (pygame surface – no OpenGL needed here)
# ─────────────────────────────────────────────────────────────────────────────
def run_menu() -> int | None:
    """Show the menu. Returns game_type (1 or 2) or None to quit."""
    global SCREEN_W, SCREEN_H, _res_index

    # ── Scale factor — change S to 1 to restore original 800×600 size ────────
    S  = 2
    MW = 800 * S   # menu window width  (1600)
    MH = 600 * S   # menu window height (1200)
    CX = MW // 2   # centre X

    screen = pygame.display.set_mode((MW, MH))
    pygame.display.set_caption("Doom Fourth Dimension")

    font_title = pygame.font.SysFont("impact",   42 * S)
    font_res   = pygame.font.SysFont("consolas", 16 * S)
    font_small = pygame.font.SysFont("consolas", 17 * S)

    # ── Original VB6 menu assets extracted from FormMenu.frx ─────────────────
    menu_bg = None
    try:
        raw_bg  = pygame.image.load(IMG("menu_bg.png")).convert()
        menu_bg = pygame.transform.scale(raw_bg, (MW, MH))
    except Exception:
        pass

    BTN_W, BTN_H = 450 * S, 70 * S

    btn_earth_img = btn_death_img = None
    try:
        btn_earth_img = pygame.transform.scale(
            pygame.image.load(IMG("btn_earth.png")).convert(), (BTN_W, BTN_H))
        btn_death_img = pygame.transform.scale(
            pygame.image.load(IMG("btn_death.png")).convert(), (BTN_W, BTN_H))
    except Exception:
        pass

    overlay = pygame.Surface((MW, MH), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))

    btn_earth_rect = pygame.Rect(CX - BTN_W // 2, 235 * S, BTN_W, BTN_H)
    btn_death_rect = pygame.Rect(CX - BTN_W // 2, 318 * S, BTN_W, BTN_H)

    # ── Resolution dropdown ───────────────────────────────────────────────────
    RES_LABELS = [f"{w} × {h}" for (w, h, _) in RESOLUTIONS]
    dd_open    = False
    dd_sel     = _res_index

    DD_W, DD_H = 220 * S, 30 * S
    dd_x       = CX - DD_W // 2
    dd_y       = 415 * S
    dd_rect    = pygame.Rect(dd_x, dd_y, DD_W, DD_H)
    opt_rects  = [pygame.Rect(dd_x, dd_y + DD_H + i * DD_H, DD_W, DD_H)
                  for i in range(len(RESOLUTIONS))]

    play_sound("Start.wav")

    clock = pygame.time.Clock()
    while True:
        # ── Background ─────────────────────────────────────────────────────
        if menu_bg:
            screen.blit(menu_bg, (0, 0))
        else:
            screen.fill((10, 5, 20))
        screen.blit(overlay, (0, 0))

        # ── Title ──────────────────────────────────────────────────────────
        shadow = font_title.render("D O O M   F O U R T H   D I M E N S I O N", True, (60, 0, 0))
        title  = font_title.render("D O O M   F O U R T H   D I M E N S I O N", True, (220, 30, 30))
        tx = CX - title.get_width() // 2
        screen.blit(shadow, (tx + 2, 32 * S)); screen.blit(title, (tx, 30 * S))

        sub = font_small.render("— Select Battle Area —", True, (200, 200, 60))
        screen.blit(sub, (CX - sub.get_width() // 2, 88 * S))

        mouse = pygame.mouse.get_pos()

        # ── Earth button ───────────────────────────────────────────────────
        hover_e = btn_earth_rect.collidepoint(mouse) and not dd_open
        if btn_earth_img:
            img_e = btn_earth_img.copy()
            if hover_e:
                img_e.fill((40, 40, 0), special_flags=pygame.BLEND_RGB_ADD)
            screen.blit(img_e, btn_earth_rect)
            pygame.draw.rect(screen,
                             (120, 255, 120) if hover_e else (80, 160, 80),
                             btn_earth_rect, 2 * S)
        else:
            pygame.draw.rect(screen, (60,140,60) if hover_e else (30,80,30),
                             btn_earth_rect, border_radius=5 * S)
            pygame.draw.rect(screen, (100,220,100), btn_earth_rect, 2, border_radius=5 * S)
            lbl = font_res.render("EARTH  —  Green Zone", True, (200,255,200))
            screen.blit(lbl, (btn_earth_rect.centerx - lbl.get_width()//2,
                               btn_earth_rect.centery - lbl.get_height()//2))

        # ── Death button ───────────────────────────────────────────────────
        hover_d = btn_death_rect.collidepoint(mouse) and not dd_open
        if btn_death_img:
            img_d = btn_death_img.copy()
            if hover_d:
                img_d.fill((40, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
            screen.blit(img_d, btn_death_rect)
            pygame.draw.rect(screen,
                             (255, 100, 100) if hover_d else (160, 60, 60),
                             btn_death_rect, 2 * S)
        else:
            pygame.draw.rect(screen, (150,35,35) if hover_d else (80,20,20),
                             btn_death_rect, border_radius=5 * S)
            pygame.draw.rect(screen, (220,80,80), btn_death_rect, 2, border_radius=5 * S)
            lbl = font_res.render("DEATH  —  Hell Zone", True, (255,180,180))
            screen.blit(lbl, (btn_death_rect.centerx - lbl.get_width()//2,
                               btn_death_rect.centery - lbl.get_height()//2))

        # ── Resolution label ──────────────────────────────────────────────
        res_lbl = font_small.render("Screen Resolution:", True, (180, 180, 60))
        screen.blit(res_lbl, (CX - res_lbl.get_width() // 2, dd_y - 24 * S))

        # ── Dropdown box ───────────────────────────────────────────────────
        hover_dd = dd_rect.collidepoint(mouse)
        pygame.draw.rect(screen, (40, 40, 20) if hover_dd else (25, 25, 12), dd_rect)
        pygame.draw.rect(screen, (200, 200, 60), dd_rect, 2)

        sel_txt = font_res.render(RES_LABELS[dd_sel], True, (255, 255, 150))
        screen.blit(sel_txt, (dd_rect.x + 10 * S,
                               dd_rect.centery - sel_txt.get_height() // 2))

        arrow = "▲" if dd_open else "▼"
        arr_s = font_res.render(arrow, True, (200, 200, 60))
        screen.blit(arr_s, (dd_rect.right - arr_s.get_width() - 8 * S,
                             dd_rect.centery - arr_s.get_height() // 2))

        if dd_open:
            for i, opt_r in enumerate(opt_rects):
                is_hover  = opt_r.collidepoint(mouse)
                is_active = (i == dd_sel)
                bg_col = (80, 80, 10) if is_hover else ((50, 50, 5) if is_active else (20, 20, 8))
                pygame.draw.rect(screen, bg_col, opt_r)
                pygame.draw.rect(screen, (160, 160, 40), opt_r, 1)
                txt = font_res.render(RES_LABELS[i], True,
                                      (255, 255, 100) if is_active else (200, 200, 120))
                screen.blit(txt, (opt_r.x + 10 * S, opt_r.centery - txt.get_height() // 2))

        # ── Footer ─────────────────────────────────────────────────────────
        hint = font_small.render(
            "Arrow Keys = Move/Turn    SPACE = Shoot    F12 = Teleport    ESC = Quit",
            True, (210, 210, 210))
        screen.blit(hint, (CX - hint.get_width() // 2, 555 * S))

        credit = font_small.render(
            "Original by Denis Astahov  ©2004   |   Remastered Python Port 2026",
            True, (210, 200, 140))
        screen.blit(credit, (CX - credit.get_width() // 2, 576 * S))

        pygame.display.flip()
        clock.tick(60)

        # ── Events ─────────────────────────────────────────────────────────
        for ev in pygame.event.get():
            if ev.type == QUIT:
                return None
            if ev.type == KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return None
                if ev.key == pygame.K_UP:
                    dd_sel = (dd_sel - 1) % len(RESOLUTIONS)
                    set_resolution(dd_sel)
                if ev.key == pygame.K_DOWN:
                    dd_sel = (dd_sel + 1) % len(RESOLUTIONS)
                    set_resolution(dd_sel)

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if dd_open:
                    picked = False
                    for i, opt_r in enumerate(opt_rects):
                        if opt_r.collidepoint(ev.pos):
                            dd_sel = i
                            set_resolution(i)
                            dd_open = False
                            picked  = True
                            break
                    if not picked:
                        dd_open = False
                elif dd_rect.collidepoint(ev.pos):
                    dd_open = True
                elif btn_earth_rect.collidepoint(ev.pos):
                    play_sound("Select.wav")
                    return 1
                elif btn_death_rect.collidepoint(ev.pos):
                    play_sound("Select.wav")
                    return 2


# ─────────────────────────────────────────────────────────────────────────────
# Intro sequence  (mirrors VB6 DemonstLoop – 4-quadrant reveal + logo)
# ─────────────────────────────────────────────────────────────────────────────
def run_intro():
    """Animated intro: reveals intro image in 4 quadrants, then shows logo."""
    global SCREEN_W, SCREEN_H
    play_music("Music1.wav")
    play_sound("Intro0.wav")

    # Load intro images as pygame surfaces (we're still in GL context)
    try:
        intro_surf = pygame.image.load(IMG(gs.area, "Intro1.jpg")).convert()
        intro_surf = pygame.transform.scale(intro_surf, (SCREEN_W, SCREEN_H))
    except Exception:
        intro_surf = None

    try:
        logo_surf  = pygame.image.load(IMG("IntroD4D.bmp")).convert_alpha()
    except Exception:
        logo_surf  = None

    # Upload intro as OpenGL texture
    if intro_surf:
        intro_data = pygame.image.tostring(intro_surf, "RGBA", False)
        intro_tex  = int(glGenTextures(1))
        glBindTexture(GL_TEXTURE_2D, intro_tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                     SCREEN_W, SCREEN_H, 0, GL_RGBA, GL_UNSIGNED_BYTE, intro_data)
    else:
        intro_tex = None

    if logo_surf:
        # Make black pixels transparent
        arr = pygame.surfarray.pixels3d(logo_surf)
        dark = (arr[:,:,0] < 12) & (arr[:,:,1] < 12) & (arr[:,:,2] < 12)
        alpha = pygame.surfarray.pixels_alpha(logo_surf)
        alpha[dark] = 0
        del arr, alpha

        logo_surf = pygame.transform.scale(logo_surf,
                        (int(SCREEN_W * 0.65), int(SCREEN_H * 0.65)))
        logo_data = pygame.image.tostring(logo_surf, "RGBA", False)
        logo_tex  = int(glGenTextures(1))
        glBindTexture(GL_TEXTURE_2D, logo_tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                     logo_surf.get_width(), logo_surf.get_height(),
                     0, GL_RGBA, GL_UNSIGNED_BYTE, logo_data)
    else:
        logo_tex = None

    pic_shown  = 0
    logo_zoom  = 0.0   # grows from 0→80 px padding  (mirrors VB6 x/Y)
    stage_tick = pygame.time.get_ticks()
    sound_map  = {1: "Intro1.wav", 2: "Intro2.wav",
                  3: "Intro3.wav", 4: "Intro4.wav", 6: "Intro0.wav"}

    clock = pygame.time.Clock()
    while True:
        # Stage advance every 3 seconds (VB6 TimerIntro Interval=3000)
        if pygame.time.get_ticks() - stage_tick >= 3000:
            stage_tick = pygame.time.get_ticks()
            pic_shown += 1
            if pic_shown in sound_map:
                play_sound(sound_map[pic_shown])

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Reveal intro image quadrant by quadrant
        if intro_tex and pic_shown >= 1:
            hw = SCREEN_W // 2
            hh = SCREEN_H // 2
            if pic_shown >= 6:
                # Full image + animated logo overlay
                logo_zoom = min(logo_zoom + 0.3, 80)
                lz = int(logo_zoom)
                draw_fullscreen_quad(intro_tex)
                if logo_tex:
                    lw = logo_surf.get_width()
                    lh = logo_surf.get_height()
                    draw_rect_2d(lz, lz, SCREEN_W - lz, SCREEN_H - lz, logo_tex)
            else:
                # Progressive quadrant reveal
                if pic_shown >= 1:
                    draw_rect_2d(0,  0,  hw, hh, intro_tex, 0,   0,   0.5, 0.5)   # top-left
                if pic_shown >= 2:
                    draw_rect_2d(hw, 0,  SCREEN_W, hh, intro_tex, 0.5, 0,   1.0, 0.5)   # top-right
                if pic_shown >= 3:
                    draw_rect_2d(0,  hh, hw, SCREEN_H, intro_tex, 0,   0.5, 0.5, 1.0)   # bottom-left
                if pic_shown >= 4:
                    draw_rect_2d(hw, hh, SCREEN_W, SCREEN_H, intro_tex, 0.5, 0.5, 1.0, 1.0)   # bottom-right

        pygame.display.flip()
        clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == QUIT:
                return False
            if ev.type == KEYDOWN:
                return True   # any key → start game


# ─────────────────────────────────────────────────────────────────────────────
# Game Over screen  (mirrors VB6 EndGameLoop)
# ─────────────────────────────────────────────────────────────────────────────
def run_gameover() -> bool:
    """Show game-over screen. Returns True=new game, False=quit."""
    global SCREEN_W, SCREEN_H
    stop_music()
    play_sound("Death_end.wav")

    font_big   = pygame.font.SysFont("impact",  38)
    font_med   = pygame.font.SysFont("impact",  26)
    font_small = pygame.font.SysFont("consolas", 20)

    gameover_tex = gs.tex["gameover"]
    expand = 0
    clock  = pygame.time.Clock()

    while True:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Phase 1: expanding game-over image (mirrors VB6 loop z=0..ScreenH/2)
        if expand <= SCREEN_H // 2:
            cx, cy = SCREEN_W//2, SCREEN_H//2
            draw_rect_2d(cx - expand, cy - expand,
                         cx + expand, cy + expand, gameover_tex)
            expand += 3
        else:
            # Phase 2: full image + text overlay
            draw_fullscreen_quad(gameover_tex)

            # Text rendered via pygame surface → GL texture (each frame cheap)
            lines = [
                (font_big,   (255, 255,   0), f"The  G A M E  is  O V E R"),
                (font_med,   (255,   0,   0), f"You Kill Monster  →  {gs.player_win} Times !!!"),
                (font_med,   (255,   0,   0), f"Your Play Time  →  {gs.play_time // 60} Minutes"),
                (font_small, (128,  70, 255), "Come Back Soon !!!"),
                (font_small, (255, 255, 255), "Created by Denis Astahov  ©2004     Remastered Python Port 2026"),
                (font_med,   (255,   0, 255), "Press N  to New Game!      ESC  to Exit..."),
            ]
            y_off = 30
            for (fnt, col, txt) in lines:
                surf = fnt.render(txt, True, col)
                data = pygame.image.tostring(surf, "RGBA", False)
                tmp  = int(glGenTextures(1))
                glBindTexture(GL_TEXTURE_2D, tmp)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                             surf.get_width(), surf.get_height(),
                             0, GL_RGBA, GL_UNSIGNED_BYTE, data)
                x1 = SCREEN_W//2 - surf.get_width()//2
                draw_rect_2d(x1, y_off,
                             x1 + surf.get_width(), y_off + surf.get_height(), tmp)
                y_off += surf.get_height() + 8
                # (tiny texture leak acceptable – game-over screen is brief)

        pygame.display.flip()
        clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == QUIT:
                return False
            if ev.type == KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return False
                if ev.key == pygame.K_n:
                    return True


# ─────────────────────────────────────────────────────────────────────────────
# Primary game loop  (mirrors VB6 PrimaryLoop)
# ─────────────────────────────────────────────────────────────────────────────
def run_game():
    """Main 3-D game loop. Returns True=new game requested, False=quit."""
    gs_reset_player()
    init_sprites()
    play_sound("Lets_go.wav")

    show_expl   = False
    expl_frames = 0
    clock = pygame.time.Clock()

    while not gs.quit_game:
        # ── events ────────────────────────────────────────────────────────
        for ev in pygame.event.get():
            if ev.type == QUIT:
                gs.quit_game = True

            if ev.type == KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    gs.quit_game = True

                if ev.key == pygame.K_n:
                    gs.start_yes = True

                if ev.key == pygame.K_F12:
                    play_sound("Teleport.wav")
                    change_area()

                # Music tracks
                for i in range(1, 11):
                    if ev.key == getattr(pygame, f"K_F{i}", None):
                        play_sound("Switch.wav")
                        play_music(f"Music{i}.wav")

                if ev.key == pygame.K_F11:
                    stop_music()

            if ev.type == KEYUP:
                if ev.key == pygame.K_SPACE:
                    gs.vistrel_now = False

        keys = pygame.key.get_pressed()

        # ── logic ─────────────────────────────────────────────────────────
        make_move(keys)
        move_enemy()
        tick_rotations()
        tick_play_time()
        apply_fog()

        # Shoot
        firing = bool(keys[pygame.K_SPACE])
        if firing and not gs.vistrel_now:
            gs.vistrel_now = True
            play_sound("Laser.wav")
            if check_hit_target():
                show_expl   = True
                expl_frames = 4
                play_sound("Killcomp.wav")
                gs.cmp_energy = max(0, gs.cmp_energy - 1)
                if gs.cmp_energy == 0:
                    play_sound("Dead.wav")
                    gs.player_win += 1
                    change_area()
                    gs.cmp_energy = 100
                    gs.xm = gs.zm = 0.0
                    gs.cstep = COMPSTEP

        if expl_frames > 0:
            expl_frames -= 1
        else:
            show_expl = False

        # ── render 3-D scene ──────────────────────────────────────────────
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(gs.cam_x, gs.cam_y, gs.cam_z,
                  gs.see_x, gs.see_y, gs.see_z,
                  0, 1, 0)

        render_world()
        render_enemy()

        # ── HUD ───────────────────────────────────────────────────────────
        render_hud(firing, show_expl)

        pygame.display.flip()
        clock.tick(60)

    return gs.start_yes


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    global SCREEN_W, SCREEN_H   # allow the actual-size update below to write module globals

    # ── Windows DPI fix ───────────────────────────────────────────────────────
    # Must be called BEFORE pygame.init() so Windows gives us physical pixels.
    # Without this, DPI scaling (125 %, 150 %, 200 %…) makes the OS report
    # logical pixels; glViewport then covers only the bottom-left of the real
    # framebuffer and the rest of the screen stays black.
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor V1
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
    pygame.display.set_caption("DOOM 4D  by Denis Astahov")

    # ── Menu (plain pygame, no GL) ─────────────────────────────────────────
    game_type = run_menu()
    if game_type is None:
        pygame.quit()
        sys.exit(0)

    gs.game_type = game_type
    gs.area      = "Earth" if game_type == 1 else "Death"

    # ── Switch to OpenGL window ────────────────────────────────────────────
    # Default resolution (index 0 = 1280×1024) → windowed at exact size.
    # Any other resolution → fullscreen.
    #   Pass size (0, 0) for fullscreen so SDL2 adopts the current desktop
    #   resolution without any mode-switching or DPI rescaling.
    fullscreen    = (_res_index != 0)
    display_flags = DOUBLEBUF | OPENGL | (pygame.FULLSCREEN if fullscreen else 0)

    if fullscreen:
        pygame.display.set_mode((0, 0), display_flags)   # native desktop resolution
    else:
        pygame.display.set_mode((SCREEN_W, SCREEN_H), display_flags)

    pygame.display.set_caption("DOOM 4D  by Denis Astahov")

    # Read the physical framebuffer dimensions that SDL2/OpenGL actually allocated.
    # On DPI-scaled systems this differs from the requested logical size.
    actual = pygame.display.get_surface().get_size()
    SCREEN_W, SCREEN_H = actual
    setup_gl()     # uses the real SCREEN_W / SCREEN_H
    load_textures()

    # ── Intro ──────────────────────────────────────────────────────────────
    if not run_intro():
        pygame.quit()
        sys.exit(0)

    stop_music()

    # ── Game loop (can restart on N key) ──────────────────────────────────
    while True:
        new_game = run_game()
        if not new_game:
            want_new = run_gameover()
            if not want_new:
                break
            # New game: reset and restart
            gs.player_win = 0
        else:
            # Player pressed N during play – just restart immediately
            gs.player_win = 0

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
