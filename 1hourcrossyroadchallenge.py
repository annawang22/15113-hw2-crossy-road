
"""
Enhanced Crossy Road Clone in Python (Pygame)
UPGRADED with visual improvements to match the classic game!

Features:
- Vibrant, colorful graphics with sky blue background
- Cute chicken character with hop animation
- 3D-style cars with windows and highlights
- Wooden logs with texture
- Animated flowing water
- Trees and environmental details on grass
- Smooth animations and polished UI

Controls:
- Arrow keys: move
- R: restart
- Esc: quit

Improvements over basic version:
- Character looks like a cute yellow chicken
- Hopping animation with parabolic arc
- Enhanced car designs with windows and shading
- Better log visuals with wood grain
- Animated water waves
- Trees scattered on grass lanes
- Brighter, more vibrant color palette
- Polished UI with better fonts and layout

Requires: pygame 2.x  (pip install pygame)

Run:
    python crossy_road_enhanced.py
"""

import random
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame


# ----------------------------- Config -----------------------------

WINDOW_W, WINDOW_H = 720, 960
FPS = 60

# Grid: each "tile" is a hop. Crossy Road feel comes from discrete hops.
TILE = 48
GRID_COLS = WINDOW_W // TILE  # 15 for 720/48
VISIBLE_ROWS = (WINDOW_H // TILE) + 2  # +2 for headroom

# Player movement cooldown (ms) to keep hop feel
HOP_COOLDOWN_MS = 110

# World generation: lane types and spacing
LANE_GRASS = "grass"
LANE_ROAD = "road"
LANE_RIVER = "river"

# How often to spawn new lanes ahead of player
AHEAD_ROWS = 28
BEHIND_ROWS = 12

# Speeds are in pixels/second; direction determined by sign
CAR_SPAWN_GAP_RANGE = (2.2, 4.5)  # seconds between car spawns per lane
LOG_SPAWN_GAP_RANGE = (2.0, 4.0)

# Lane "themes"
ROAD_CAR_SPEED_RANGE = (140, 260)
RIVER_LOG_SPEED_RANGE = (90, 180)

# Collision padding
PLAYER_HITBOX_INSET = 10  # shrink player rect a bit for forgiving collisions

# Colors - Brighter, more vibrant Crossy Road style
COL_BG = (135, 206, 235)  # Sky blue background
COL_GRASS = (102, 204, 102)  # Bright grass
COL_GRASS_DARK = (85, 180, 85)
COL_GRASS_LIGHT = (120, 220, 120)
COL_ROAD = (68, 68, 68)
COL_ROAD_SIDE = (88, 88, 88)  # Sidewalk edge
COL_ROAD_LINE = (240, 240, 100)
COL_RIVER = (64, 164, 223)
COL_WATER_DARK = (45, 140, 200)
COL_WATER_LIGHT = (100, 190, 240)
COL_PLAYER = (255, 220, 60)  # Bright yellow chicken-like
COL_PLAYER_BEAK = (255, 140, 0)
COL_PLAYER_EYE = (50, 50, 50)
COL_SHADOW = (0, 0, 0, 80)
COL_TEXT = (255, 255, 255)
COL_UI_BG = (30, 30, 30, 150)
COL_TREE = (101, 67, 33)  # Tree trunk
COL_TREE_LEAVES = (34, 139, 34)

# Entity colors
CAR_COLORS = [
    (232, 80, 84),
    (82, 180, 255),
    (255, 170, 55),
    (170, 110, 255),
    (90, 220, 140),
    (245, 245, 245),
]
LOG_COLORS = [
    (128, 86, 50),
    (148, 98, 56),
    (170, 112, 62),
]


# ----------------------------- Helpers -----------------------------

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def now_ms() -> int:
    return pygame.time.get_ticks()


def grid_to_px(col: int, row: int) -> Tuple[int, int]:
    # World coordinates: increasing row goes UP (negative y).
    return col * TILE, -row * TILE


def rect_from_grid(col: int, row: int, w_tiles: float = 1.0, h_tiles: float = 1.0) -> pygame.Rect:
    x, y = grid_to_px(col, row)
    return pygame.Rect(x, y, int(TILE * w_tiles), int(TILE * h_tiles))


# ----------------------------- Game Objects -----------------------------

@dataclass
class Obstacle:
    rect: pygame.Rect
    speed: float  # px/sec, +right, -left
    color: Tuple[int, int, int]
    kind: str      # 'car' or 'log'

    def update(self, dt: float):
        self.rect.x += int(self.speed * dt)

    def draw(self, surf: pygame.Surface, camera_y: int):
        r = self.rect.move(0, -camera_y)
        
        if self.kind == "car":
            # Draw shadow
            shadow = pygame.Surface((r.w + 4, r.h // 2), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 60), shadow.get_rect())
            surf.blit(shadow, (r.x - 2, r.y + r.h))
            
            # Main body with gradient effect
            pygame.draw.rect(surf, self.color, r, border_radius=8)
            
            # Darker bottom
            bottom = pygame.Rect(r.x, r.y + r.h // 2, r.w, r.h // 2)
            dark_color = tuple(max(0, c - 40) for c in self.color)
            pygame.draw.rect(surf, dark_color, bottom, border_radius=8)
            
            # Windows
            window_color = (100, 180, 220, 180)
            window_w = max(8, r.w // 5)
            window_h = r.h // 3
            window_y = r.y + r.h // 4
            
            # Front window
            pygame.draw.rect(surf, window_color, 
                           (r.x + r.w - window_w - 4, window_y, window_w, window_h), 
                           border_radius=3)
            # Back window
            pygame.draw.rect(surf, window_color, 
                           (r.x + 4, window_y, window_w, window_h), 
                           border_radius=3)
            
            # Highlight
            hl = pygame.Rect(r.x + 4, r.y + 4, max(0, r.w - 8), 4)
            pygame.draw.rect(surf, (255, 255, 255, 120), hl, border_radius=2)
            
        else:  # log
            # Log shadow
            shadow = pygame.Surface((r.w + 3, r.h // 2), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 50), shadow.get_rect())
            surf.blit(shadow, (r.x - 2, r.y + r.h))
            
            # Main log body
            pygame.draw.rect(surf, self.color, r, border_radius=6)
            
            # Wood texture lines
            dark_brown = tuple(max(0, c - 30) for c in self.color)
            for i in range(3):
                line_y = r.y + (i + 1) * r.h // 4
                pygame.draw.line(surf, dark_brown, 
                               (r.x + 4, line_y), (r.x + r.w - 4, line_y), 2)
            
            # Highlight on top
            hl_color = tuple(min(255, c + 30) for c in self.color)
            pygame.draw.rect(surf, hl_color, 
                           (r.x + 6, r.y + 3, r.w - 12, 4), border_radius=2)


@dataclass
class Lane:
    lane_type: str
    row: int  # world row index
    direction: int  # +1 right, -1 left (for moving objects)
    speed: float  # px/sec magnitude
    spawn_gap: float  # seconds
    last_spawn_t: float  # seconds accumulator
    objects: List[Obstacle]
    # For road/river visuals
    decoration_seed: int
    tree_positions: List[int] = None  # List of tile columns where trees are placed
    
    def __post_init__(self):
        if self.tree_positions is None:
            self.tree_positions = []
        # Generate tree positions for grass lanes
        if self.lane_type == LANE_GRASS:
            self._generate_tree_positions()
    
    def _generate_tree_positions(self):
        """Generate consistent tree positions based on decoration seed"""
        rng = random.Random(self.decoration_seed + 1000)
        self.tree_positions = []
        for col in range(GRID_COLS):
            if rng.random() < 0.2:  # 20% chance of tree
                self.tree_positions.append(col)
    
    def has_tree_at(self, col: int) -> bool:
        """Check if there's a tree at the given column"""
        return col in self.tree_positions

    def world_y(self) -> int:
        # World coordinates: increasing row goes UP (negative y).
        return -self.row * TILE

    def update(self, dt: float, t_total: float):
        # Move objects
        for obj in self.objects:
            obj.update(dt)

        # Cull offscreen objects (world coords)
        if self.lane_type in (LANE_ROAD, LANE_RIVER):
            self.objects = [o for o in self.objects if not self._is_far_offscreen(o)]

        # Spawn new objects
        if self.lane_type == LANE_ROAD:
            self._spawn_vehicle(dt, t_total)
        elif self.lane_type == LANE_RIVER:
            self._spawn_log(dt, t_total)

    def _is_far_offscreen(self, obj: Obstacle) -> bool:
        # A little generous: remove when fully past left/right plus margin
        margin = TILE * 4
        if obj.speed > 0:
            return obj.rect.left > WINDOW_W + margin
        else:
            return obj.rect.right < -margin

    def _spawn_vehicle(self, dt: float, t_total: float):
        # Use last_spawn_t as a countdown timer (seconds)
        self.last_spawn_t -= dt
        if self.last_spawn_t > 0:
            return

        # Reset timer with jitter
        self.last_spawn_t = random.uniform(*CAR_SPAWN_GAP_RANGE)

        # Spawn car at lane edge depending on direction
        car_len_tiles = random.choice([1.2, 1.5, 1.8, 2.2])
        car_w = int(TILE * car_len_tiles)
        car_h = int(TILE * 0.74)
        y = self.world_y() + (TILE - car_h) // 2
        if self.direction > 0:
            x = -car_w - random.randint(10, 80)
        else:
            x = WINDOW_W + random.randint(10, 80)

        rect = pygame.Rect(x, y, car_w, car_h)
        color = random.choice(CAR_COLORS)
        speed = self.speed * self.direction
        self.objects.append(Obstacle(rect=rect, speed=speed, color=color, kind="car"))

    def _spawn_log(self, dt: float, t_total: float):
        self.last_spawn_t -= dt
        if self.last_spawn_t > 0:
            return

        self.last_spawn_t = random.uniform(*LOG_SPAWN_GAP_RANGE)

        log_len_tiles = random.choice([1.6, 2.0, 2.4, 3.0])
        log_w = int(TILE * log_len_tiles)
        log_h = int(TILE * 0.70)
        y = self.world_y() + (TILE - log_h) // 2
        if self.direction > 0:
            x = -log_w - random.randint(10, 120)
        else:
            x = WINDOW_W + random.randint(10, 120)

        rect = pygame.Rect(x, y, log_w, log_h)
        color = random.choice(LOG_COLORS)
        speed = self.speed * self.direction
        self.objects.append(Obstacle(rect=rect, speed=speed, color=color, kind="log"))

    def draw(self, surf: pygame.Surface, camera_y: int):
        # Draw lane background
        y = self.world_y() - camera_y
        lane_rect = pygame.Rect(0, y, WINDOW_W, TILE)

        if self.lane_type == LANE_GRASS:
            # Base grass with slight variation
            pygame.draw.rect(surf, COL_GRASS, lane_rect)
            
            # Add texture with alternating patches
            rng = random.Random(self.decoration_seed)
            for i in range(0, WINDOW_W, TILE):
                if rng.random() < 0.3:
                    patch = pygame.Rect(i, y, TILE, TILE)
                    pygame.draw.rect(surf, COL_GRASS_DARK, patch)
                elif rng.random() < 0.15:
                    patch = pygame.Rect(i, y, TILE, TILE)
                    pygame.draw.rect(surf, COL_GRASS_LIGHT, patch)
            
            # Add trees occasionally
            for col in self.tree_positions:
                tree_x = col * TILE + TILE // 2
                tree_y = y + TILE // 2
                
                # Tree shadow
                shadow = pygame.Surface((16, 8), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow, (0, 0, 0, 60), shadow.get_rect())
                surf.blit(shadow, (tree_x - 8, tree_y + 8))
                
                # Trunk
                trunk_rect = pygame.Rect(tree_x - 3, tree_y - 6, 6, 12)
                pygame.draw.rect(surf, COL_TREE, trunk_rect, border_radius=2)
                
                # Leaves (rounded top)
                pygame.draw.circle(surf, COL_TREE_LEAVES, (tree_x, tree_y - 8), 10)
                # Add highlight
                pygame.draw.circle(surf, (50, 180, 50), (tree_x - 3, tree_y - 11), 4)
                    
        elif self.lane_type == LANE_ROAD:
            # Road with sidewalk edges
            pygame.draw.rect(surf, COL_ROAD_SIDE, lane_rect)
            road_inner = pygame.Rect(0, y + 4, WINDOW_W, TILE - 8)
            pygame.draw.rect(surf, COL_ROAD, road_inner)
            
            # Dashed center line
            dash_w = TILE // 2
            dash_h = 4
            dash_y = y + TILE // 2 - dash_h // 2
            for x in range(0, WINDOW_W, dash_w * 2):
                dash_rect = pygame.Rect(x + dash_w // 2, dash_y, dash_w - 4, dash_h)
                pygame.draw.rect(surf, COL_ROAD_LINE, dash_rect, border_radius=2)
                
        elif self.lane_type == LANE_RIVER:
            # Animated water base
            pygame.draw.rect(surf, COL_RIVER, lane_rect)
            
            # Animated wave effect using time-based offset
            wave_offset = (pygame.time.get_ticks() // 100) % (TILE * 2)
            
            # Draw flowing water waves
            for x in range(-TILE * 2, WINDOW_W + TILE * 2, TILE):
                wave_x = x + wave_offset
                # Dark wave
                pygame.draw.ellipse(surf, COL_WATER_DARK, 
                                  (wave_x, y + 8, TILE, 8))
                # Light shimmer
                pygame.draw.ellipse(surf, COL_WATER_LIGHT,
                                  (wave_x + TILE // 2, y + TILE - 14, TILE // 2, 6))
            
            # River banks
            pygame.draw.rect(surf, COL_WATER_DARK, (0, y, WINDOW_W, 3))
            pygame.draw.rect(surf, COL_WATER_DARK, (0, y + TILE - 3, WINDOW_W, 3))

        # Draw obstacles
        for obj in self.objects:
            obj.draw(surf, camera_y)


@dataclass
class Player:
    # x is the *world* x position of the tile the player occupies (top-left of the tile).
    # We keep x continuous so when you stand on a log you are carried perfectly with it
    # (i.e., you become "part of the log" unless you move).
    x: float
    row: int  # world row (increasing row goes UP; y = -row*TILE)
    alive: bool = True
    score_best: int = 0
    score: int = 0
    last_hop_ms: int = 0
    riding_dx: float = 0.0  # px/sec from log when on it
    hop_progress: float = 0.0  # 0.0 to 1.0 for animation
    hop_animating: bool = False

    def _tile_rect_world(self) -> pygame.Rect:
        # Tile in world coordinates (top-left).
        return pygame.Rect(int(self.x), -self.row * TILE, TILE, TILE)

    def rect_world(self) -> pygame.Rect:
        base = self._tile_rect_world()
        inset = 8
        return pygame.Rect(base.x + inset, base.y + inset, base.w - inset * 2, base.h - inset * 2)

    def hitbox_world(self) -> pygame.Rect:
        r = self.rect_world()
        return pygame.Rect(
            r.x + PLAYER_HITBOX_INSET,
            r.y + PLAYER_HITBOX_INSET,
            r.w - PLAYER_HITBOX_INSET * 2,
            r.h - PLAYER_HITBOX_INSET * 2,
        )

    def can_hop(self) -> bool:
        return (now_ms() - self.last_hop_ms) >= HOP_COOLDOWN_MS

    def _grid_col(self) -> int:
        # Nearest tile column to current x.
        return int(round(self.x / TILE))

    def hop(self, dc: int, dr: int):
        if not self.alive or not self.can_hop():
            return
        self.last_hop_ms = now_ms()
        self.hop_animating = True
        self.hop_progress = 0.0

        # Hops always land on the grid.
        col = self._grid_col()
        col = clamp(col + dc, 0, GRID_COLS - 1)
        self.x = float(col * TILE)
        self.row = max(0, self.row + dr)

    def update(self, dt: float):
        # When riding a log, move exactly with it: your position relative to the log stays constant
        # unless YOU hop.
        if not self.alive:
            return

        # Update hop animation
        if self.hop_animating:
            self.hop_progress += dt * 8.0  # Animation speed
            if self.hop_progress >= 1.0:
                self.hop_progress = 1.0
                self.hop_animating = False

        if abs(self.riding_dx) >= 1e-3:
            self.x += self.riding_dx * dt

        # Die only if fully carried off the screen horizontally.
        r = self.rect_world()
        if r.right < 0 or r.left > WINDOW_W:
            self.alive = False

    def draw(self, surf: pygame.Surface, camera_y: int):
        r = self.rect_world().move(0, -camera_y)
        
        # Calculate hop bounce
        hop_offset = 0
        if self.hop_animating:
            # Parabolic arc for hop
            t = self.hop_progress
            hop_offset = int(-18 * (4 * t * (1 - t)))  # Max height of 18px
        
        # Adjust position for hop
        r = r.move(0, hop_offset)

        # Shadow (stays on ground)
        shadow_y = r.y - hop_offset + r.h - 4
        shadow = pygame.Surface((r.w + 6, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, COL_SHADOW, shadow.get_rect())
        surf.blit(shadow, (r.x - 3, shadow_y))

        # Body - rounded chicken shape
        body_rect = pygame.Rect(r.x, r.y + 8, r.w, r.h - 8)
        pygame.draw.ellipse(surf, COL_PLAYER, body_rect)
        
        # Head - smaller circle on top
        head_size = r.w // 2 + 2
        head_x = r.centerx
        head_y = r.y + 12
        pygame.draw.circle(surf, COL_PLAYER, (head_x, head_y), head_size)
        
        # Beak
        beak_points = [
            (head_x + head_size - 2, head_y),
            (head_x + head_size + 6, head_y - 2),
            (head_x + head_size + 6, head_y + 2)
        ]
        pygame.draw.polygon(surf, COL_PLAYER_BEAK, beak_points)
        
        # Eyes
        eye_size = 3
        left_eye = (head_x - 5, head_y - 2)
        right_eye = (head_x + 5, head_y - 2)
        pygame.draw.circle(surf, COL_PLAYER_EYE, left_eye, eye_size)
        pygame.draw.circle(surf, COL_PLAYER_EYE, right_eye, eye_size)
        
        # Eye highlights
        pygame.draw.circle(surf, (255, 255, 255), (left_eye[0] - 1, left_eye[1] - 1), 1)
        pygame.draw.circle(surf, (255, 255, 255), (right_eye[0] - 1, right_eye[1] - 1), 1)
        
        # Wings (small ovals on sides)
        wing_left = pygame.Rect(r.x + 2, r.y + 14, 8, 12)
        wing_right = pygame.Rect(r.right - 10, r.y + 14, 8, 12)
        wing_color = tuple(max(0, c - 20) for c in COL_PLAYER)
        pygame.draw.ellipse(surf, wing_color, wing_left)
        pygame.draw.ellipse(surf, wing_color, wing_right)
        
        # Feet (only visible when not hopping high)
        if hop_offset > -5:
            feet_y = r.bottom - hop_offset - 2
            # Left foot
            pygame.draw.line(surf, COL_PLAYER_BEAK, 
                           (r.centerx - 6, feet_y), (r.centerx - 8, feet_y + 4), 2)
            pygame.draw.line(surf, COL_PLAYER_BEAK,
                           (r.centerx - 8, feet_y + 4), (r.centerx - 10, feet_y + 4), 2)
            # Right foot
            pygame.draw.line(surf, COL_PLAYER_BEAK,
                           (r.centerx + 6, feet_y), (r.centerx + 8, feet_y + 4), 2)
            pygame.draw.line(surf, COL_PLAYER_BEAK,
                           (r.centerx + 8, feet_y + 4), (r.centerx + 10, feet_y + 4), 2)


# ----------------------------- World -----------------------------

class World:
    def __init__(self):
        self.lanes: dict[int, Lane] = {}  # row -> Lane
        self.rng = random.Random(1337)
        self.max_generated_row = -1

    def reset(self):
        self.lanes.clear()
        self.rng = random.Random(random.randint(0, 10_000_000))
        self.max_generated_row = -1

        # Start area: a few grass lanes
        for r in range(0, 8):
            self._ensure_lane(r, force_type=LANE_GRASS)

    def lane_at(self, row: int) -> Lane:
        self._ensure_lane(row)
        return self.lanes[row]

    def update(self, dt: float, t_total: float, player_row: int):
        # Ensure lanes around player
        self._generate_around(player_row)

        # Update all lanes in a window
        for r in range(player_row - BEHIND_ROWS, player_row + AHEAD_ROWS + 1):
            if r < 0:
                continue
            lane = self.lanes.get(r)
            if lane:
                lane.update(dt, t_total)

    def draw(self, surf: pygame.Surface, camera_y: int, player_row: int):
        # Draw lanes around the player (works cleanly even with negative camera values).
        first_row = max(0, player_row - (BEHIND_ROWS + 8))
        last_row = player_row + (AHEAD_ROWS + 8)
        for r in range(first_row, last_row + 1):
            lane = self.lanes.get(r)
            if lane:
                lane.draw(surf, camera_y)

    def _generate_around(self, player_row: int):
        target_max = player_row + AHEAD_ROWS
        for r in range(self.max_generated_row + 1, target_max + 1):
            self._ensure_lane(r)
            self.max_generated_row = max(self.max_generated_row, r)

        # Optionally: discard far-behind lanes to keep memory bounded
        min_keep = max(0, player_row - (BEHIND_ROWS + 8))
        for r in list(self.lanes.keys()):
            if r < min_keep:
                del self.lanes[r]

    def _ensure_lane(self, row: int, force_type: Optional[str] = None):
        if row in self.lanes:
            return

        if force_type is not None:
            lane_type = force_type
        else:
            lane_type = self._choose_lane_type(row)

        direction = self.rng.choice([-1, 1])
        decoration_seed = self.rng.randint(0, 999999)

        if lane_type == LANE_GRASS:
            lane = Lane(
                lane_type=LANE_GRASS,
                row=row,
                direction=direction,
                speed=0.0,
                spawn_gap=999,
                last_spawn_t=999,
                objects=[],
                decoration_seed=decoration_seed,
            )
        elif lane_type == LANE_ROAD:
            speed = self.rng.uniform(*ROAD_CAR_SPEED_RANGE)
            lane = Lane(
                lane_type=LANE_ROAD,
                row=row,
                direction=direction,
                speed=speed,
                spawn_gap=self.rng.uniform(*CAR_SPAWN_GAP_RANGE),
                last_spawn_t=self.rng.uniform(0.0, 1.5),
                objects=[],
                decoration_seed=decoration_seed,
            )
        else:  # river
            speed = self.rng.uniform(*RIVER_LOG_SPEED_RANGE)
            lane = Lane(
                lane_type=LANE_RIVER,
                row=row,
                direction=direction,
                speed=speed,
                spawn_gap=self.rng.uniform(*LOG_SPAWN_GAP_RANGE),
                last_spawn_t=self.rng.uniform(0.0, 1.5),
                objects=[],
                decoration_seed=decoration_seed,
            )

        self.lanes[row] = lane

    def _choose_lane_type(self, row: int) -> str:
        # Keep early game safe-ish, then diversify.
        if row < 10:
            return LANE_GRASS if self.rng.random() < 0.75 else LANE_ROAD

        # Avoid too many consecutive hazardous lanes.
        prev1 = self.lanes.get(row - 1)
        prev2 = self.lanes.get(row - 2)

        def is_hazard(l: Optional[Lane]) -> bool:
            return l is not None and l.lane_type in (LANE_ROAD, LANE_RIVER)

        consecutive_hazard = 0
        if is_hazard(prev1):
            consecutive_hazard += 1
        if is_hazard(prev2) and is_hazard(prev1):
            consecutive_hazard += 1

        if consecutive_hazard >= 2:
            return LANE_GRASS

        # Weighted random
        roll = self.rng.random()
        if roll < 0.40:
            return LANE_GRASS
        elif roll < 0.72:
            return LANE_ROAD
        else:
            return LANE_RIVER


# ----------------------------- Game -----------------------------

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("🐔 Crossy Road - Python Edition 🐔")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("consolas", 22)
        self.font_big = pygame.font.SysFont("consolas", 48, bold=True)

        self.world = World()
        self.player = Player(x=(GRID_COLS // 2) * TILE, row=2)
        self.camera_y = 0
        self.t_total = 0.0  # seconds
        self.game_over = False

        self.reset()

    def reset(self):
        self.world.reset()
        self.player.x = float((GRID_COLS // 2) * TILE)
        self.player.row = 2
        self.player.alive = True
        self.player.score = 0
        self.player.riding_dx = 0.0
        self.player.hop_progress = 0.0
        self.player.hop_animating = False

        self.camera_y = (-self.player.row * TILE) - WINDOW_H + 10 * TILE
        self.t_total = 0.0
        self.game_over = False

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.t_total += dt

            self._handle_events()
            self._update(dt)
            self._draw()

    def _can_move_to(self, dc: int, dr: int) -> bool:
        """Check if the player can move to the target position (no tree blocking)"""
        # Calculate target position
        current_col = self.player._grid_col()
        target_col = clamp(current_col + dc, 0, GRID_COLS - 1)
        target_row = max(0, self.player.row + dr)
        
        # Get the lane at target row
        target_lane = self.world.lane_at(target_row)
        
        # Check if there's a tree blocking the move
        if target_lane.lane_type == LANE_GRASS:
            if target_lane.has_tree_at(target_col):
                return False
        
        return True

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._quit()

                if event.key == pygame.K_r:
                    self.reset()

                if not self.player.alive:
                    # Allow restart after death
                    continue

                if event.key == pygame.K_UP:
                    if self._can_move_to(0, 1):
                        self.player.hop(0, 1)
                elif event.key == pygame.K_DOWN:
                    if self._can_move_to(0, -1):
                        self.player.hop(0, -1)
                elif event.key == pygame.K_LEFT:
                    if self._can_move_to(-1, 0):
                        self.player.hop(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    if self._can_move_to(1, 0):
                        self.player.hop(1, 0)

    def _update(self, dt: float):
        if not self.player.alive:
            self.game_over = True
            return

        # World update around player
        self.world.update(dt, self.t_total, self.player.row)

        # Riding physics reset each frame; will be set if standing on log
        self.player.riding_dx = 0.0

        # Score = max row reached
        self.player.score = max(self.player.score, self.player.row - 2)
        self.player.score_best = max(self.player.score_best, self.player.score)

        # Resolve interactions at current lane
        lane = self.world.lane_at(self.player.row)

        # Apply water danger
        if lane.lane_type == LANE_RIVER:
            on_log = self._player_on_log(lane)
            if on_log is None:
                self.player.alive = False
            else:
                # Ride with the log
                self.player.riding_dx = on_log.speed

        # Apply road collision
        if lane.lane_type == LANE_ROAD:
            if self._player_hit_car(lane):
                self.player.alive = False

        # Apply riding movement drift
        self.player.update(dt)

        # If drift pushed player into a car (rare but possible), re-check collisions nearby
        if self.player.alive:
            lane2 = self.world.lane_at(self.player.row)
            if lane2.lane_type == LANE_ROAD and self._player_hit_car(lane2):
                self.player.alive = False

        # Camera follows player upward
        desired_camera = (-self.player.row * TILE) - WINDOW_H + 10 * TILE
        # Smooth camera
        self.camera_y += int((desired_camera - self.camera_y) * clamp(dt * 6.0, 0.0, 1.0))

    def _player_hit_car(self, lane: Lane) -> bool:
        hb = self.player.hitbox_world()
        for obj in lane.objects:
            if obj.kind == "car" and hb.colliderect(obj.rect.inflate(-6, -8)):
                return True
        return False

    def _player_on_log(self, lane: Lane) -> Optional[Obstacle]:
        # Stable detection: if a support point near the player's feet is over a log,
        # consider them safely on it.
        pr = self.player.rect_world()
        support_point = (pr.centerx, pr.bottom - 4)
        for obj in lane.objects:
            if obj.kind != "log":
                continue
            if obj.rect.inflate(10, 8).collidepoint(support_point):
                return obj
        return None

    def _draw(self):
        self.screen.fill(COL_BG)

        # Draw world
        self.world.draw(self.screen, self.camera_y, self.player.row)

        # Draw player
        self.player.draw(self.screen, self.camera_y)

        # UI overlay
        self._draw_ui()

        pygame.display.flip()

    def _draw_ui(self):
        # Top HUD with vibrant colors
        hud_height = 80
        hud = pygame.Surface((WINDOW_W - 32, hud_height), pygame.SRCALPHA)
        pygame.draw.rect(hud, COL_UI_BG, hud.get_rect(), border_radius=20)
        # Add a bright border
        pygame.draw.rect(hud, (255, 200, 60, 100), hud.get_rect(), width=3, border_radius=20)
        self.screen.blit(hud, (16, 16))

        # Score with larger, bolder text
        score_txt = self.font_big.render(f"{self.player.score}", True, (255, 230, 80))
        score_label = self.font.render("SCORE", True, (200, 200, 200))
        self.screen.blit(score_label, (40, 24))
        self.screen.blit(score_txt, (40, 45))
        
        # Best score
        best_txt = self.font.render(f"BEST: {self.player.score_best}", True, (180, 220, 255))
        self.screen.blit(best_txt, (200, 50))

        # Controls hint (smaller)
        small_font = pygame.font.SysFont("consolas", 16)
        controls_txt = small_font.render("← ↑ ↓ → Move  |  R Restart  |  ESC Quit", True, (200, 200, 200))
        self.screen.blit(controls_txt, ((WINDOW_W - controls_txt.get_width()) // 2, WINDOW_H - 30))

        if self.game_over:
            # Center game over card with Crossy Road style
            card_w, card_h = 450, 280
            x = (WINDOW_W - card_w) // 2
            y = (WINDOW_H - card_h) // 2
            
            card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            # Colorful gradient-like background
            pygame.draw.rect(card, (40, 40, 60, 220), card.get_rect(), border_radius=25)
            pygame.draw.rect(card, (100, 200, 255, 50), card.get_rect(), width=4, border_radius=25)

            title_font = pygame.font.SysFont("consolas", 56, bold=True)
            title = title_font.render("GAME OVER", True, (255, 100, 100))
            
            score_label2 = self.font.render("FINAL SCORE", True, (200, 200, 200))
            score_big = self.font_big.render(f"{self.player.score}", True, (255, 230, 80))
            best_label = self.font.render(f"Best: {self.player.score_best}", True, (180, 220, 255))
            
            restart_font = pygame.font.SysFont("consolas", 24)
            hint = restart_font.render("Press  R  to Restart", True, (150, 255, 150))

            # Position elements
            card.blit(title, ((card_w - title.get_width()) // 2, 30))
            card.blit(score_label2, ((card_w - score_label2.get_width()) // 2, 110))
            card.blit(score_big, ((card_w - score_big.get_width()) // 2, 135))
            card.blit(best_label, ((card_w - best_label.get_width()) // 2, 185))
            card.blit(hint, ((card_w - hint.get_width()) // 2, 225))

            self.screen.blit(card, (x, y))

    def _quit(self):
        pygame.quit()
        sys.exit(0)


def main():
    Game().run()


if __name__ == "__main__":
    main()
