import pygame
import sys
import time
import json
import requests
from collections import deque
from pathlib import Path

# ---------------------------
# LEVEL FILES
# ---------------------------
LEVELS = [
    Path("maps/level1.txt"),
    Path("maps/level2.txt"),
    Path("maps/level3.txt"),
    Path("maps/level4.txt"),
    Path("maps/level5.txt"),
]

# ---------------------------
# SETTINGS (2D OUTLINE STYLE)
# ---------------------------
TILE_SIZE = 32
FPS = 60

BG_COLOR    = (20, 20, 28)      # Background
FLOOR_COLOR = (35, 38, 55)      # Floor
WALL_COLOR  = (80, 90, 255)     # Wall fill (blue)
EXIT_COLOR  = (0, 255, 140)     # Exit
TEXT_COLOR  = (240, 240, 255)   # Text

# Best time file
BEST_FILE = Path("best_time.json")

# n8n webhook URL (for score saving)
WEBHOOK_URL = "https://feyzabalabann8n.app.n8n.cloud/webhook/maze-score"


def send_score_to_server(player_name: str, score: float):
    """
    Send total game score to n8n webhook.
    If there is an error, just log it to console and don't break the game.
    """
    try:
        payload = {
            "player_name": player_name,
            "score": score,
        }
        # Small timeout so the game doesn't freeze if internet is down
        requests.post(WEBHOOK_URL, json=payload, timeout=3)
        print("Score sent to server:", payload)
    except Exception as e:
        print("Could not send score:", e)


# ---------------------------
# LOAD / SAVE BEST TIMES
# ---------------------------
def load_best_times():
    if BEST_FILE.exists():
        try:
            return json.loads(BEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_best_times(data: dict):
    try:
        BEST_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


# ---------------------------
# MAP LOADING
# ---------------------------
def load_map(path: Path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(line.rstrip("\n"))

    width = max(len(r) for r in rows)
    height = len(rows)
    grid = [list(r.ljust(width)) for r in rows]

    start = None
    exit_pos = None

    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == "S":
                start = (x, y)
            elif ch == "E":
                exit_pos = (x, y)

    if start is None or exit_pos is None:
        raise ValueError("Map must contain 'S' and 'E'.")

    return grid, start, exit_pos, width, height


# ---------------------------
# CAN WE REACH THE EXIT?
# ---------------------------
def path_exists(grid, start, exit_pos):
    H, W = len(grid), len(grid[0])
    sy, sx = start[1], start[0]
    ey, ex = exit_pos[1], exit_pos[0]

    q = deque([(sy, sx)])
    seen = {(sy, sx)}

    while q:
        y, x = q.popleft()
        if (y, x) == (ey, ex):
            return True

        for dy, dx in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W:
                if grid[ny][nx] != "#" and (ny, nx) not in seen:
                    seen.add((ny, nx))
                    q.append((ny, nx))

    return False


# ---------------------------
# MOVEMENT CHECK
# ---------------------------
def can_move(grid, x, y):
    h = len(grid)
    w = len(grid[0])
    if not (0 <= y < h and 0 <= x < w):
        return False
    return grid[y][x] != "#"


# ---------------------------
# LOAD PLAYER SPRITES
# ---------------------------
def load_player_sprites():
    raw = {
        "pink": pygame.image.load("ghost/pink_ghost.png").convert_alpha(),
        "blue": pygame.image.load("ghost/blue_ghost.png").convert_alpha(),
    }
    return {
        k: pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))
        for k, img in raw.items()
    }


# ---------------------------
# CHARACTER SELECTION
# ---------------------------
def choose_skin(screen, clock, font, sprites):
    msg_font = pygame.font.SysFont("arial", 32)

    while True:
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return None
                if e.key == pygame.K_1:
                    return "pink"
                if e.key == pygame.K_2:
                    return "blue"

        screen.fill(BG_COLOR)

        title = msg_font.render("Choose your ghost, Feyza!", True, TEXT_COLOR)
        info = font.render("Press 1 for PINK, 2 for BLUE", True, TEXT_COLOR)

        screen.blit(title, (40, 40))
        screen.blit(info, (40, 80))

        p = sprites["pink"]
        pr = p.get_rect(center=(200, 230))
        screen.blit(p, pr)
        screen.blit(font.render("1 - Pink", True, TEXT_COLOR),
                    (pr.x, pr.bottom + 10))

        b = sprites["blue"]
        br = b.get_rect(center=(420, 230))
        screen.blit(b, br)
        screen.blit(font.render("2 - Blue", True, TEXT_COLOR),
                    (br.x, br.bottom + 10))

        pygame.display.flip()


# ---------------------------
# SMALL FLASH EFFECT
# ---------------------------
def flash_effect(screen):
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h))
    overlay.fill((255, 255, 255))
    overlay.set_alpha(120)

    for _ in range(3):
        screen.blit(overlay, (0, 0))
        pygame.display.flip()
        pygame.time.delay(80)


# ---------------------------
# RUN ONE LEVEL
# ---------------------------
def run_level(level_index, screen, clock, font, player_img, best_times):
    grid, start, exit_pos, width, height = load_map(LEVELS[level_index])

    if not path_exists(grid, start, exit_pos):
        raise ValueError(f"Level {level_index + 1} is not solvable.")

    screen = pygame.display.set_mode((width * TILE_SIZE, height * TILE_SIZE))
    pygame.display.set_caption(f"Maze Escape – Feyza (Level {level_index + 1})")

    player_x, player_y = start
    start_time = time.time()
    won = False
    win_time = None
    level_elapsed = 0  # time for this level

    level_key = f"level_{level_index + 1}"
    prev_best = best_times.get(level_key)

    msg_font = pygame.font.SysFont("arial", 26)
    new_record = False

    while True:
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "quit", 0
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return "quit", 0
                if e.key == pygame.K_r:
                    return "restart", 0

        if not won:
            keys = pygame.key.get_pressed()
            dx = dy = 0

            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
            elif keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1

            if dx or dy:
                nx, ny = player_x + dx, player_y + dy
                if can_move(grid, nx, ny):
                    player_x, player_y = nx, ny

            if (player_x, player_y) == exit_pos:
                won = True
                win_time = time.time()
                level_elapsed = int(win_time - start_time)

                # best time check
                if (prev_best is None) or (level_elapsed < prev_best):
                    best_times[level_key] = level_elapsed
                    save_best_times(best_times)
                    prev_best = level_elapsed
                    new_record = True

                # small flash effect
                flash_effect(screen)

        if won and win_time is not None and time.time() - win_time > 1.0:
            return "next", level_elapsed

        # --- Drawing ---
        screen.fill(BG_COLOR)

        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE,
                                   TILE_SIZE, TILE_SIZE)

                if ch == "#":
                    # 2D outline wall
                    pygame.draw.rect(screen, WALL_COLOR, rect)      # fill
                    pygame.draw.rect(screen, (0, 0, 0), rect, 3)   # black outline
                else:
                    pygame.draw.rect(screen, FLOOR_COLOR, rect)

                if (x, y) == exit_pos:
                    e_rect = rect.inflate(-6, -6)
                    pygame.draw.rect(screen, EXIT_COLOR, e_rect, border_radius=4)

        # Player
        screen.blit(player_img, (player_x * TILE_SIZE, player_y * TILE_SIZE))

        # HUD
        elapsed = int(time.time() - start_time)
        screen.blit(font.render(f"Time: {elapsed}s", True, TEXT_COLOR),
                    (10, 5))
        screen.blit(font.render(f"Level: {level_index + 1}", True, TEXT_COLOR),
                    (10, 30))

        # Best time info
        best_txt = "--" if prev_best is None else f"{prev_best}s"
        screen.blit(font.render(f"Best: {best_txt}", True, TEXT_COLOR),
                    (10, 55))

        # New record message
        if new_record:
            msg = msg_font.render("New Best Time! 🎉", True, EXIT_COLOR)
            mx = (width * TILE_SIZE - msg.get_width()) // 2
            screen.blit(msg, (mx, 10))

        pygame.display.flip()


# ---------------------------
# MAIN
# ---------------------------
def main():
    pygame.init()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 22)

    # Ask player name ONCE
    player_name = input("Enter your player name: ").strip()
    if not player_name:
        player_name = "Player"

    screen = pygame.display.set_mode((640, 480))

    sprites = load_player_sprites()
    best_times = load_best_times()

    chosen = choose_skin(screen, clock, font, sprites)
    if chosen is None:
        pygame.quit()
        sys.exit()

    player_img = sprites[chosen]

    current_level = 0
    total_time = 0  # sum of all finished level times in this run

    while True:
        if current_level >= len(LEVELS):
            # All levels finished
            screen.fill(BG_COLOR)
            msg = pygame.font.SysFont("arial", 28).render(
                "All levels finished! 🎉", True, TEXT_COLOR
            )
            screen.blit(msg, (50, 50))
            pygame.display.flip()
            pygame.time.wait(2000)

            # Send TOTAL time to n8n scoreboard
            send_score_to_server(player_name, total_time)
            break

        result, level_elapsed = run_level(
            current_level, screen, clock, font, player_img, best_times
        )

        if result == "next":
            total_time += level_elapsed
            current_level += 1
        elif result == "restart":
            # replay the same level, do not change total_time
            continue
        else:
            # quit
            break

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
