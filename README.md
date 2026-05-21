# DOOM 4D – Python Port REMASTERED

> Original Game by **Denis Astahov**, 2004  
> Bachelor Degree Final Project — Score: **95 / 100**  
> VB6 + DirectX 7 → Python 3.12+ port using **pygame + PyOpenGL**

## 🎮 About

DOOM 4D is a 3D First-Person Shooter where you battle a computer-controlled enemy across two arenas:
- **Earth** 🌍 - Green landscapes, peaceful trees
- **Death** 🔥 - Dark realm, fire and smoke

<img src="https://www.astahov.net/doom1.jpg"> <img src="https://www.astahov.net/doom2.jpg">
<br>

## How to run

```bash
# Clone the repo
git clone https://github.com/adv4000/doom4d-remastered.git
cd doom4d-remastered

# Install dependencies
pip install -r requirements.txt

# Run the game
python doom4d.py
```

## Controls

| Key | Action |
|-----|--------|
| ↑ ↓ | Move forward / back |
| ← → | Turn left / right |
| **Space** | Fire laser |
| **F12** | Teleport (switch Earth ↔ Death area) |
| **F1–F10** | Switch music track |
| **F11** | Stop music |
| **W** | White fog ON |
| **Q** | Black fog ON |
| **Z** | Fog OFF |
| **1 / 2 / 3** | Fog mode: Linear / Exp / Exp2 |
| **N** | New game (on Game Over screen) |
| **ESC** | Quit |


## 📁 Project Structure

```
doom4d-remastered/
├── doom4d.py          # Main game file
├── requirements.txt   # Python dependencies
├── README.md          # This file
├── Image/             # Textures and sprites
│   ├── Earth/         # Earth arena textures
│   └── Death/         # Hell arena textures
├── Sound/             # Sound effects
└── Music/             # Background music
```

## Original source

https://github.com/adv4000/doom4d
