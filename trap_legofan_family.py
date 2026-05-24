"""
Trap LEGO FAN1's Family  v5 – realistic map, smooth walking, always-visible rope
pip install pygame pypresence websockets
"""
import pygame, sys, time, math, random, json, os, pathlib, subprocess, tempfile, urllib.request, urllib.error

APP_DIR = pathlib.Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
VERSION_FILE = APP_DIR / "version.json"

def load_version_metadata():
    meta = {
        "version": "1.1.0",
        "update_manifest_url": "",
    }
    try:
        if VERSION_FILE.exists():
            loaded = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                meta.update({k: v for k, v in loaded.items() if k in meta})
    except Exception as e:
        print(f"[VERSION] Load failed: {e}")
    return meta

VERSION_META = load_version_metadata()

# ── Discord RPC ───────────────────────────────────────────────────────────────
DISCORD_APP_ID = "1490446446208483471"
rpc = None; rpc_connected = False
try:
    from pypresence import Presence
    rpc = Presence(DISCORD_APP_ID); rpc.connect()
    rpc_connected = True; print("[RPC] Connected.")
except Exception as e:
    print(f"[RPC] Skipping: {e}")

# ── Constants ─────────────────────────────────────────────────────────────────
TILE          = 48
COLS          = 26
ROWS          = 20
WIN_W         = COLS * TILE
WIN_H         = ROWS * TILE + 64
FPS           = 60
FLEE_RADIUS   = 5.0
FLEE_SPEED    = 0.13
ROAM_SPEED    = 0.022
PLAYER_SPEED  = 0.17
SPRINT_SPEED  = 0.26
STAMINA_MAX   = 180
STAMINA_DRAIN = 1
STAMINA_REGEN = 0.55
TOTAL_MEMBERS = 8
PER_CATCH     = 11
LERP_SPEED    = 0.35   # slightly faster visual smoothing
SAVE_VERSION  = 1
APP_VERSION    = str(VERSION_META.get("version", "1.1.0"))
UPDATE_MANIFEST_URL = str(VERSION_META.get("update_manifest_url", ""))

# ── Colours ───────────────────────────────────────────────────────────────────
C_BG       = (12, 10, 16)
C_WALL     = (50, 45, 65)
C_WALL_T   = (70, 65, 90)
C_WALL_S   = (35, 30, 48)
C_FLOOR_A  = (28, 24, 38)
C_FLOOR_B  = (32, 28, 44)
C_CARPET   = (38, 28, 42)
C_CARPET2  = (44, 32, 48)
C_WOOD     = (42, 32, 22)
C_WOOD2    = (48, 36, 24)
C_KITCHEN  = (45, 40, 25)
C_KITCHEN2 = (50, 45, 30)
C_TILE     = (35, 35, 45)
C_TILE2    = (40, 40, 50)
C_HUD_BG   = (8,  6,  12)
C_BAR_BG   = (35, 30, 50)
C_BAR_FG   = (60, 200,100)
C_BAR_DONE = (255,210, 0)
C_WHITE    = (255,255,255)
C_YELLOW   = (255,210, 40)
C_RED      = (255, 70, 70)
C_STAM_HI  = (80, 220,120)
C_STAM_LO  = (220, 80, 80)
C_CAGE     = (180,160, 80)
C_CAGE2    = (120,100, 40)
C_ROPE     = (200,160, 60)

# ── Family members ────────────────────────────────────────────────────────────
FAMILY = [
    {"id":"mum",         "name":"Mum",                   "col":(215,170,120),"body":(236,198,170),"hair":(95,70,40),  "shirt":(156,112,92), "pants":(64,64,78),  "gender":"f","speed_mult":1.05},
    {"id":"dad",         "name":"Dad",                   "col":(120,145,170),"body":(205,170,130),"hair":(50,35,25),  "shirt":(82,104,122), "pants":(52,58,72),  "gender":"m","speed_mult":1.10},
    {"id":"carina",      "name":"Carina",                "col":(190,125,165),"body":(238,202,176),"hair":(70,42,25),  "shirt":(172,108,138), "pants":(72,58,84),  "gender":"f","speed_mult":1.20},
    {"id":"mumsbrother", "name":"Mum's Brother",         "col":(120,165,130),"body":(198,160,120),"hair":(58,38,20),  "shirt":(94,118,92),   "pants":(58,66,72),  "gender":"m","speed_mult":0.95},
    {"id":"dadsaunt",    "name":"Dad's Grandma's Sister","col":(165,150,190),"body":(222,190,160),"hair":(110,90,70), "shirt":(146,130,168), "pants":(78,76,88),  "gender":"f","speed_mult":0.75},
    {"id":"dadsuncle",   "name":"Her Husband",           "col":(185,155,95), "body":(196,164,126),"hair":(45,36,28),  "shirt":(128,112,78),  "pants":(64,58,52),  "gender":"m","speed_mult":0.80},
    {"id":"exwife",      "name":"Mum's Bro's Ex-Wife",   "col":(170,110,110),"body":(232,188,158),"hair":(90,56,44),  "shirt":(158,96,96),   "pants":(76,62,66),  "gender":"f","speed_mult":1.15},
    {"id":"niece",       "name":"Mum's Bro's Daughter",  "col":(110,175,170),"body":(244,210,186),"hair":(120,80,40), "shirt":(102,154,152), "pants":(66,76,82),  "gender":"f","speed_mult":1.25},
]

# ── Player character presets ──────────────────────────────────────────────────
PLAYER_CHARS = [
    {"label":"Guy 1",   "gender":"m","body":(228,190,160),"hair":(58,40,24), "shirt":(74,110,152),"pants":(50,56,72)},
    {"label":"Guy 2",   "gender":"m","body":(204,166,128),"hair":(132,86,42), "shirt":(162,88,72),"pants":(62,66,82)},
    {"label":"Guy 3",   "gender":"m","body":(170,124,92), "hair":(28,22,16), "shirt":(72,132,96), "pants":(48,54,56)},
    {"label":"Woman 1", "gender":"f","body":(238,202,176),"hair":(88,60,34),  "shirt":(168,102,152),"pants":(72,58,92)},
    {"label":"Woman 2", "gender":"f","body":(214,174,140),"hair":(48,32,22),  "shirt":(84,146,166), "pants":(62,52,76)},
    {"label":"Woman 3", "gender":"f","body":(242,208,186),"hair":(172,136,78), "shirt":(188,124,72), "pants":(60,64,92)},
]

# ── Map (more realistic house layout) ─────────────────────────────────────────
RAW_MAP = [
    "11111111111111111111111111",
    "10000000001111110000000001",
    "10000000001000010000000001",
    "10000111111000010000011101",
    "10000100000000010000010001",
    "10000100011111111111010001",
    "10000000000000010001010001",
    "10000100010000010001010001",
    "10000100010000010001011101",
    "10000100010000010000000001",
    "10000100011111111111111101",
    "10000100000000010000000001",
    "10000111111100010001111001",
    "10000000000100010001001001",
    "10111110000100011111001001",
    "10000010000100010000000001",
    "10000010000111110011111001",
    "10000010000000000000001001",
    "10000000000000000000000001",
    "11111111111111111111111111",
]
LEVEL = [[int(c) for c in row] for row in RAW_MAP]
FLOOR_CELLS = [(c,r) for r in range(ROWS) for c in range(COLS) if LEVEL[r][c]==0]
SPAWN_ZONES = [
    (1, 1, 8, 4),
    (9, 1, 16, 4),
    (17, 1, 24, 4),
    (1, 5, 8, 9),
    (9, 5, 16, 9),
    (17, 5, 24, 9),
    (1, 10, 8, 16),
    (9, 10, 16, 16),
    (17, 10, 24, 16),
    (1, 17, 24, 18),
]

def floor_shade(c, r):
    """Room‑aware floor colours."""
    # kitchen (top‑right area)
    if c>=16 and r<10:      return (C_KITCHEN, C_KITCHEN2)
    # living room / lounge
    if 8<=c<16 and 1<r<10:  return (C_WOOD, C_WOOD2)
    # bedroom / office
    if c<9 and 4<r<17:      return (C_CARPET, C_CARPET2)
    # hallway / tile
    return (C_TILE, C_TILE2)

def rand_floor_far(ox, oy, min_dist=8):
    cands = [(c,r) for c,r in FLOOR_CELLS if math.hypot(c-ox,r-oy)>=min_dist]
    return random.choice(cands or FLOOR_CELLS)

def rand_floor_in_zone(zone, used=None):
    x1, y1, x2, y2 = zone
    used = used or set()
    cands = [
        (c, r)
        for c in range(x1, x2 + 1)
        for r in range(y1, y2 + 1)
        if 0 <= c < COLS and 0 <= r < ROWS and LEVEL[r][c] == 0 and (c, r) not in used
    ]
    if cands:
        return random.choice(cands)
    cands = [(c, r) for c, r in FLOOR_CELLS if (c, r) not in used]
    return random.choice(cands or FLOOR_CELLS)

def lerp(a, b, t):
    return a + (b - a) * t

def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))

def safe_rgb(col, fallback=(255, 255, 255)):
    try:
        if isinstance(col, pygame.Color):
            return (clamp(col.r), clamp(col.g), clamp(col.b))
        seq = tuple(col)
        if len(seq) >= 3:
            return (clamp(seq[0]), clamp(seq[1]), clamp(seq[2]))
    except Exception:
        pass
    return fallback

def safe_rgba(col, alpha=255, fallback=(255, 255, 255)):
    r, g, b = safe_rgb(col, fallback)
    return (r, g, b, clamp(alpha))

SAVE_ROOT = pathlib.Path(os.environ.get("LOCALAPPDATA") or pathlib.Path.home()) / "TrapLEGOFANFamily"
SAVE_FILE = SAVE_ROOT / "save.json"
APP_PATH = pathlib.Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve()

def default_save_data():
    return {
        "version": SAVE_VERSION,
        "player_name": "",
        "last_character": None,
        "runs_played": 0,
        "best_caught": 0,
        "best_progress": 0,
        "currency": 0,
        "upgrades": {},
        "current_run": None,
        "last_saved": None,
    }

def load_save_data():
    data = default_save_data()
    try:
        if SAVE_FILE.exists():
            loaded = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update({k: v for k, v in loaded.items() if k in data or k == "version"})
    except Exception as e:
        print(f"[SAVE] Load failed: {e}")
    return data

def write_save_data(data):
    try:
        SAVE_ROOT.mkdir(parents=True, exist_ok=True)
        payload = default_save_data()
        payload.update(data or {})
        payload["version"] = SAVE_VERSION
        payload["last_saved"] = time.time()
        SAVE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[SAVE] Write failed: {e}")
        return False

SAVE_DATA = load_save_data()

def version_tuple(v):
    parts = []
    for chunk in str(v).split("."):
        try:
            parts.append(int(chunk))
        except Exception:
            digits = "".join(ch for ch in chunk if ch.isdigit())
            parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])

def is_newer_version(remote, local):
    return version_tuple(remote) > version_tuple(local)

def get_app_path():
    return APP_PATH

def check_for_update():
    if not UPDATE_MANIFEST_URL:
        return None
    try:
        with urllib.request.urlopen(UPDATE_MANIFEST_URL, timeout=4) as resp:
            manifest = json.loads(resp.read().decode("utf-8"))
        remote_version = str(manifest.get("version", "")).strip()
        remote_url = str(manifest.get("url", "")).strip()
        notes = str(manifest.get("notes", "")).strip()
        if remote_version and remote_url and is_newer_version(remote_version, APP_VERSION):
            return {"version": remote_version, "url": remote_url, "notes": notes}
    except Exception as e:
        print(f"[UPDATE] Check failed: {e}")
    return None

def download_file(url, dest_path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=15) as resp, open(dest_path, "wb") as out:
        while True:
            chunk = resp.read(1024 * 128)
            if not chunk:
                break
            out.write(chunk)
    return dest_path

def launch_update_worker(target_path, source_path):
    temp_dir = pathlib.Path(tempfile.gettempdir()) / "TrapLEGOFANFamily"
    temp_dir.mkdir(parents=True, exist_ok=True)
    ps1_path = temp_dir / "apply_update.ps1"
    ps1 = rf"""
param(
    [string]$Target,
    [string]$Source,
    [int]$Pid
)
while (Get-Process -Id $Pid -ErrorAction SilentlyContinue) {{
    Start-Sleep -Milliseconds 400
}}
for ($i = 0; $i -lt 45; $i++) {{
    try {{
        Copy-Item -LiteralPath $Source -Destination $Target -Force
        break
    }} catch {{
        Start-Sleep -Milliseconds 400
    }}
}}
Start-Process -FilePath $Target
"""
    ps1_path.write_text(ps1, encoding="utf-8")
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-WindowStyle",
            "Hidden",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ps1_path),
            "-Target",
            str(target_path),
            "-Source",
            str(source_path),
            "-Pid",
            str(os.getpid()),
        ],
        close_fds=True,
    )

def perform_update(manifest):
    if not getattr(sys, "frozen", False):
        print("[UPDATE] Self-update is intended for the packaged EXE build.")
        return False
    try:
        target_path = get_app_path()
        temp_dir = pathlib.Path(tempfile.gettempdir()) / "TrapLEGOFANFamily" / "updates"
        temp_dir.mkdir(parents=True, exist_ok=True)
        downloaded = temp_dir / target_path.name
        print(f"[UPDATE] Downloading {manifest['version']}...")
        download_file(manifest["url"], downloaded)
        launch_update_worker(target_path, downloaded)
        print("[UPDATE] Launched updater.")
        return True
    except Exception as e:
        print(f"[UPDATE] Failed: {e}")
        return False

UPDATE_INFO = check_for_update()

def clamp_window_size(w, h):
    info = pygame.display.Info()
    max_w = max(320, info.current_w - 40)
    max_h = max(240, info.current_h - 80)
    return max(320, min(int(w), max_w)), max(240, min(int(h), max_h))

def fit_rect(src_w, src_h, dst_w, dst_h):
    scale = min(dst_w / src_w, dst_h / src_h)
    out_w = max(1, int(src_w * scale))
    out_h = max(1, int(src_h * scale))
    return out_w, out_h, (dst_w - out_w) // 2, (dst_h - out_h) // 2

# ── Pygame init ───────────────────────────────────────────────────────────────
pygame.init()
_init_info = pygame.display.Info()
_win_w, _win_h = clamp_window_size(min(WIN_W, _init_info.current_w - 80), min(WIN_H, _init_info.current_h - 120))
window = pygame.display.set_mode((_win_w, _win_h), pygame.RESIZABLE)
screen = pygame.Surface((WIN_W, WIN_H)).convert_alpha()
pygame.display.set_caption(f"Trap LEGO FAN 1's Family v{APP_VERSION}")
clock  = pygame.time.Clock()

def present():
    ww, wh = window.get_size()
    rw, rh, ox, oy = fit_rect(WIN_W, WIN_H, ww, wh)
    frame = pygame.transform.smoothscale(screen, (rw, rh))
    window.fill((0, 0, 0))
    window.blit(frame, (ox, oy))
    pygame.display.flip()

def set_window_size(w, h):
    global window
    window = pygame.display.set_mode(clamp_window_size(w, h), pygame.RESIZABLE)

def window_to_game_pos(pos):
    ww, wh = window.get_size()
    rw, rh, ox, oy = fit_rect(WIN_W, WIN_H, ww, wh)
    mx, my = pos
    if mx < ox or my < oy or mx >= ox + rw or my >= oy + rh:
        return None
    sx = (mx - ox) * WIN_W / rw
    sy = (my - oy) * WIN_H / rh
    return sx, sy

try:
    FNT_HUD   = pygame.font.SysFont("consolas", 17, bold=True)
    FNT_SMALL = pygame.font.SysFont("consolas", 13)
    FNT_POP   = pygame.font.SysFont("consolas", 22, bold=True)
    FNT_BIG   = pygame.font.SysFont("consolas", 34, bold=True)
    FNT_INPUT = pygame.font.SysFont("consolas", 26, bold=True)
    FNT_TITLE = pygame.font.SysFont("consolas", 20, bold=True)
    FNT_EXCL  = pygame.font.SysFont("consolas", 20, bold=True)
    FNT_MED   = pygame.font.SysFont("consolas", 15, bold=True)
except:
    f = pygame.font.Font(None, 24)
    FNT_HUD=FNT_SMALL=FNT_POP=FNT_BIG=FNT_INPUT=FNT_TITLE=FNT_EXCL=FNT_MED=f

fog_surf = pygame.Surface((WIN_W, WIN_H-64), pygame.SRCALPHA)

# ── RPC ───────────────────────────────────────────────────────────────────────
def update_rpc(player_name, caught, progress, start_ts):
    if not rpc_connected: return
    try:
        rpc.update(
            name="Trap LEGO FAN 1's Family",
            details="Trap LEGO FAN 1's Family",
            state=f"{player_name} | Progress: {progress}%",
            start=int(start_ts),
            party_size=[caught, TOTAL_MEMBERS],
        )
    except Exception as e: print(f"[RPC] {e}")

# ═════════════════════════════════════════════════════════════════════════════
#  SHARED DRAWING HELPERS
# ═════════════════════════════════════════════════════════════════════════════
def draw_person(surf, px, py, char, size=14, bob=0, face_dir=1,
                leg_swing=0, arm_swing=0, is_female=False, alpha=255):
    """Draw a detailed character at pixel position (px,py)."""
    py += bob
    skin  = safe_rgb(char.get("body"), (240, 200, 170))
    hair  = safe_rgb(char.get("hair"), (60, 40, 20))
    shirt = safe_rgb(char.get("shirt"), (80, 120, 180))
    pants = safe_rgb(char.get("pants"), (40, 40, 60))

    def col_a(c):
        rgb = safe_rgb(c, C_WHITE)
        return (*rgb, clamp(alpha)) if alpha < 255 else rgb

    tmp = pygame.Surface((size*6, size*6), pygame.SRCALPHA)
    cx = size*3; cy = size*3

    # shadow
    sh = pygame.Surface((size*4, size//2+4), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0,0,0,70), sh.get_rect())
    surf.blit(sh, (px-size*2, py+size+2))

    # legs
    lleg_y = cy + size + int(math.sin(leg_swing)*size*0.5)
    rleg_y = cy + size - int(math.sin(leg_swing)*size*0.5)
    pygame.draw.line(tmp, col_a(pants), (cx-4, cy+size//2), (cx-5, lleg_y+size//2), 5)
    pygame.draw.line(tmp, col_a(pants), (cx+4, cy+size//2), (cx+5, rleg_y+size//2), 5)
    # shoes
    pygame.draw.ellipse(tmp, col_a((30,25,20)), (cx-8, lleg_y+size//2-2, 8, 5))
    pygame.draw.ellipse(tmp, col_a((30,25,20)), (cx+1, rleg_y+size//2-2, 8, 5))

    # body / torso
    if is_female:
        pygame.draw.polygon(tmp, col_a(shirt),
            [(cx-size//2, cy-size//3),(cx+size//2, cy-size//3),
             (cx+size//2+2, cy+size//2),(cx-size//2-2, cy+size//2)])
    else:
        pygame.draw.rect(tmp, col_a(shirt),
            (cx-size//2, cy-size//3, size, size), border_radius=3)

    # arms
    la_y = cy - size//4 + int(math.sin(arm_swing)*size*0.4)
    ra_y = cy - size//4 - int(math.sin(arm_swing)*size*0.4)
    pygame.draw.line(tmp, col_a(shirt), (cx-size//2, cy-size//4), (cx-size-2, la_y+size//2), 4)
    pygame.draw.line(tmp, col_a(shirt), (cx+size//2, cy-size//4), (cx+size+2, ra_y+size//2), 4)
    # hands
    pygame.draw.circle(tmp, col_a(skin), (cx-size-2, la_y+size//2), 3)
    pygame.draw.circle(tmp, col_a(skin), (cx+size+2, ra_y+size//2), 3)

    # head
    pygame.draw.circle(tmp, col_a(skin), (cx, cy-size//2), size//2+2)
    # hair
    if is_female:
        pygame.draw.arc(tmp, col_a(hair),
            (cx-size//2-1, cy-size-3, size+2, size//2+4), 0, math.pi, 5)
        pygame.draw.line(tmp, col_a(hair), (cx-size//2, cy-size//2), (cx-size//2-1, cy+2), 3)
        pygame.draw.line(tmp, col_a(hair), (cx+size//2, cy-size//2), (cx+size//2+1, cy+2), 3)
    else:
        pygame.draw.arc(tmp, col_a(hair),
            (cx-size//2, cy-size-2, size, size//2+2), 0, math.pi, 5)
    # eyes
    ex_off = 3*face_dir
    pygame.draw.circle(tmp, col_a(C_WHITE), (cx+ex_off-3, cy-size//2), 2)
    pygame.draw.circle(tmp, col_a(C_WHITE), (cx+ex_off+3, cy-size//2), 2)
    pygame.draw.circle(tmp, col_a((20,15,30)), (cx+ex_off-2, cy-size//2), 1)
    pygame.draw.circle(tmp, col_a((20,15,30)), (cx+ex_off+4, cy-size//2), 1)

    surf.blit(tmp, (px - size*3, py - size*3))

def draw_cage_icon(surf, cx, cy, w=40, h=36):
    """Draw a simple cage (no alpha – works on main screen)."""
    bars = 5
    bar_col  = C_CAGE
    bar_col2 = C_CAGE2
    # top/bottom rails
    pygame.draw.line(surf, bar_col, (cx-w//2, cy-h//2), (cx+w//2, cy-h//2), 3)
    pygame.draw.line(surf, bar_col, (cx-w//2, cy+h//2), (cx+w//2, cy+h//2), 3)
    # side posts
    pygame.draw.line(surf, bar_col2, (cx-w//2, cy-h//2-2), (cx-w//2, cy+h//2+2), 4)
    pygame.draw.line(surf, bar_col2, (cx+w//2, cy-h//2-2), (cx+w//2, cy+h//2+2), 4)
    # vertical bars
    for i in range(bars):
        bx = cx - w//2 + (w*i)//(bars-1)
        pygame.draw.line(surf, bar_col, (bx, cy-h//2), (bx, cy+h//2), 2)

# ═════════════════════════════════════════════════════════════════════════════
#  SCREEN 1 — NAME ENTRY
# ═════════════════════════════════════════════════════════════════════════════
def name_entry_screen():
    player_name=str(SAVE_DATA.get("player_name", "") or ""); cursor_tick=0; error_msg=""
    while True:
        clock.tick(FPS); cursor_tick+=1
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.VIDEORESIZE: set_window_size(event.w, event.h)
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_u and UPDATE_INFO:
                    if perform_update(UPDATE_INFO):
                        pygame.quit()
                        if rpc_connected:
                            try: rpc.close()
                            except: pass
                        sys.exit()
                if event.key==pygame.K_RETURN:
                    n=player_name.strip()
                    if len(n)<2: error_msg="Name must be at least 2 characters!"
                    else: return n
                elif event.key==pygame.K_BACKSPACE:
                    player_name=player_name[:-1]; error_msg=""
                elif event.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                else:
                    if len(player_name)<20 and event.unicode.isprintable():
                        player_name+=event.unicode; error_msg=""

        screen.fill(C_BG)
        for r in range(ROWS):
            for c in range(COLS):
                s,s2=floor_shade(c,r)
                pygame.draw.rect(screen,s if (c+r)%2==0 else s2,(c*TILE,r*TILE,TILE,TILE))
        ov=pygame.Surface((WIN_W,WIN_H),pygame.SRCALPHA); ov.fill((0,0,0,185)); screen.blit(ov,(0,0))
        t1=FNT_BIG.render("Trap LEGO FAN 1's Family",True,C_YELLOW)
        screen.blit(t1,(WIN_W//2-t1.get_width()//2,WIN_H//2-180))
        t2=FNT_HUD.render("Enter your name:",True,(180,180,210))
        screen.blit(t2,(WIN_W//2-t2.get_width()//2,WIN_H//2-110))
        bw,bh=380,52; bx=WIN_W//2-bw//2; by=WIN_H//2-60
        pygame.draw.rect(screen,(22,20,40),(bx,by,bw,bh),border_radius=10)
        pygame.draw.rect(screen,C_YELLOW,(bx,by,bw,bh),2,border_radius=10)
        cur="|" if (cursor_tick//30)%2==0 else ""
        inp=FNT_INPUT.render(player_name+cur,True,C_WHITE)
        screen.blit(inp,(bx+14,by+12))
        hint=FNT_SMALL.render("Press ENTER to continue",True,(120,120,150))
        screen.blit(hint,(WIN_W//2-hint.get_width()//2,by+bh+14))
        if UPDATE_INFO:
            upd=FNT_SMALL.render(f"Update v{UPDATE_INFO['version']} available. Press U to install.",True,(140,200,140))
            screen.blit(upd,(WIN_W//2-upd.get_width()//2,by+bh+36))
        if error_msg:
            err=FNT_SMALL.render(error_msg,True,(255,80,80))
            screen.blit(err,(WIN_W//2-err.get_width()//2,by+bh+36))
        present()

# ═════════════════════════════════════════════════════════════════════════════
#  SCREEN 2 — CHARACTER SELECT
# ═════════════════════════════════════════════════════════════════════════════
def char_select_screen(player_name):
    selected = 0
    tick = 0
    CARD_W, CARD_H = 160, 220
    cols_n = 3
    rows_n = 2
    pad_x = 30
    total_w = cols_n * CARD_W + (cols_n-1)*pad_x
    start_x = WIN_W//2 - total_w//2
    start_y = WIN_H//2 - rows_n*CARD_H//2 - 20

    while True:
        clock.tick(FPS); tick+=1
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.VIDEORESIZE: set_window_size(event.w, event.h)
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if event.key in (pygame.K_RIGHT,pygame.K_d):
                    selected=(selected+1)%len(PLAYER_CHARS)
                if event.key in (pygame.K_LEFT,pygame.K_a):
                    selected=(selected-1)%len(PLAYER_CHARS)
                if event.key in (pygame.K_DOWN,pygame.K_s):
                    selected=(selected+cols_n)%len(PLAYER_CHARS)
                if event.key in (pygame.K_UP,pygame.K_w):
                    selected=(selected-cols_n)%len(PLAYER_CHARS)
                if event.key==pygame.K_RETURN:
                    return PLAYER_CHARS[selected]
            if event.type==pygame.MOUSEBUTTONDOWN:
                gpos = window_to_game_pos(event.pos)
                if gpos is None:
                    continue
                mx,my=gpos
                for i,ch in enumerate(PLAYER_CHARS):
                    ci=i%cols_n; ri=i//cols_n
                    cx2=start_x+ci*(CARD_W+pad_x); cy2=start_y+ri*(CARD_H+20)
                    if cx2<=mx<=cx2+CARD_W and cy2<=my<=cy2+CARD_H:
                        if selected==i: return PLAYER_CHARS[i]
                        selected=i

        screen.fill(C_BG)
        for r in range(ROWS):
            for c in range(COLS):
                s,s2=floor_shade(c,r)
                pygame.draw.rect(screen,s if (c+r)%2==0 else s2,(c*TILE,r*TILE,TILE,TILE))
        ov=pygame.Surface((WIN_W,WIN_H),pygame.SRCALPHA); ov.fill((0,0,0,185)); screen.blit(ov,(0,0))

        t1=FNT_BIG.render(f"Choose your character, {player_name}",True,C_YELLOW)
        screen.blit(t1,(WIN_W//2-t1.get_width()//2,start_y-80))
        hint=FNT_SMALL.render("Arrow keys / click to select  |  ENTER to confirm",True,(130,130,160))
        screen.blit(hint,(WIN_W//2-hint.get_width()//2,start_y-44))

        for i,ch in enumerate(PLAYER_CHARS):
            ci=i%cols_n; ri=i//cols_n
            cx2=start_x+ci*(CARD_W+pad_x); cy2=start_y+ri*(CARD_H+20)
            is_sel=(i==selected)
            border_col=C_YELLOW if is_sel else (60,55,80)
            bg_col=(30,28,50) if is_sel else (18,16,28)
            pygame.draw.rect(screen,bg_col,(cx2,cy2,CARD_W,CARD_H),border_radius=12)
            pygame.draw.rect(screen,border_col,(cx2,cy2,CARD_W,CARD_H),2,border_radius=12)

            # preview character
            bob=int(math.sin(tick*0.05+i)*3) if is_sel else 0
            is_f=(ch["gender"]=="f")
            swing=math.sin(tick*0.08+i)*0.5 if is_sel else 0
            draw_person(screen, cx2+CARD_W//2, cy2+CARD_H//2-10, ch,
                       size=18, bob=bob, face_dir=1,
                       leg_swing=swing, arm_swing=swing, is_female=is_f)

            lbl=FNT_MED.render(ch["label"],True,C_YELLOW if is_sel else C_WHITE)
            screen.blit(lbl,(cx2+CARD_W//2-lbl.get_width()//2, cy2+CARD_H-28))
            if is_sel:
                glow=pygame.Surface((CARD_W,CARD_H),pygame.SRCALPHA)
                pygame.draw.rect(glow,(*C_YELLOW,18),(0,0,CARD_W,CARD_H),border_radius=12)
                screen.blit(glow,(cx2,cy2))

        present()

# ═════════════════════════════════════════════════════════════════════════════
#  CUTSCENE — capture animation
# ═════════════════════════════════════════════════════════════════════════════
def play_capture_cutscene(player_name, player_char, member):
    """
    Plays a short cutscene:
      Phase 0 (0-40):  player runs toward member throwing rope/tape
      Phase 1 (40-80): rope wraps around member, member shakes
      Phase 2 (80-130): player drags member toward cage
      Phase 3 (130-180): member thrown into cage, bars slam shut
      Phase 4 (180-220): fade out with text
    """
    DURATION = 220
    cx = WIN_W//2
    cy = WIN_H//2 + 30

    # positions
    p_start_x = cx - 180
    p_end_x   = cx - 60
    m_x       = cx + 60
    cage_x    = cx + 200
    cage_y    = cy

    is_f = (player_char["gender"]=="f")
    m_col  = member["col"]
    m_dark = tuple(max(0,c-55) for c in m_col)

    # simple member char appearance (reuse a neutral look)
    m_char = {"body":m_col,"hair":m_dark,"shirt":m_dark,"pants":(40,40,60)}
    m_is_f = member["id"] in ("mum","carina","dadsaunt","exwife","niece")

    for frame in range(DURATION):
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.VIDEORESIZE: set_window_size(event.w, event.h)
            if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                return  # skip cutscene

        t = frame / DURATION
        screen.fill((5,4,8))

        # background — blurred dark room suggestion
        pygame.draw.rect(screen,(15,12,22),(cx-260,cy-160,520,230),border_radius=18)
        pygame.draw.rect(screen,(30,25,45),(cx-260,cy-160,520,230),2,border_radius=18)

        # ── Phase 0: player runs in ──
        if frame < 40:
            pf = frame/40
            px2 = int(lerp(p_start_x, p_end_x, pf))
            leg = math.sin(frame*0.4)*0.8
            arm = math.sin(frame*0.4+math.pi)*0.8
            draw_person(screen, px2, cy, player_char, size=20,
                       face_dir=1, leg_swing=leg, arm_swing=arm, is_female=is_f)
            # member stands nervously
            draw_person(screen, m_x, cy, m_char, size=18,
                       face_dir=-1, bob=int(math.sin(frame*0.3)*1), is_female=m_is_f)
            # rope coil held by player
            pygame.draw.circle(screen, C_ROPE, (px2+18, cy-10), 6, 2)
            pygame.draw.circle(screen, C_ROPE, (px2+18, cy-10), 4, 2)

        # ── Phase 1: rope throw ──
        elif frame < 80:
            pf = (frame-40)/40
            # rope arc from player to member
            rope_x = int(lerp(p_end_x+20, m_x, pf))
            rope_y = int(cy - math.sin(pf*math.pi)*60)
            # player standing
            draw_person(screen, p_end_x, cy, player_char, size=20,
                       face_dir=1, arm_swing=math.pi*0.5, is_female=is_f)
            # member reacting — growing ! above head
            shake = int(math.sin(frame*1.2)*3) if pf>0.7 else 0
            draw_person(screen, m_x+shake, cy, m_char, size=18,
                       face_dir=-1, is_female=m_is_f)
            # rope line
            pygame.draw.line(screen, C_ROPE, (p_end_x+18, cy-10), (rope_x, rope_y), 2)
            pygame.draw.circle(screen, C_ROPE, (rope_x, rope_y), 5)
            # ! marker appears on impact
            if pf > 0.8:
                a2 = int((pf-0.8)/0.2*255)
                excl = FNT_BIG.render("!", True, C_RED)
                excl.set_alpha(a2)
                screen.blit(excl,(m_x-excl.get_width()//2, cy-70))

        # ── Phase 2: drag toward cage ──
        elif frame < 130:
            pf = (frame-80)/50
            drag_x = int(lerp(m_x, cage_x-40, pf))
            drag_y = cy + int(math.sin(pf*math.pi)*10)
            # player drags
            draw_person(screen, int(lerp(p_end_x, cage_x-80, pf)), cy,
                       player_char, size=20, face_dir=1,
                       leg_swing=math.sin(frame*0.35)*0.6, is_female=is_f)
            # member dragged — tilted, shaking
            shake2 = int(math.sin(frame*2)*4)
            draw_person(screen, drag_x+shake2, drag_y, m_char, size=16,
                       face_dir=-1, is_female=m_is_f)
            # rope between them
            pygame.draw.line(screen, C_ROPE,
                (int(lerp(p_end_x,cage_x-80,pf))+18, cy-5),
                (drag_x, drag_y-5), 2)
            # cage on right (drawn fully opaque)
            draw_cage_icon(screen, cage_x+20, cage_y, w=50, h=44)

        # ── Phase 3: throw into cage ──
        elif frame < 180:
            pf = (frame-130)/50
            # arc into cage
            throw_x = int(lerp(cage_x-40, cage_x+10, pf))
            throw_y = int(cy - math.sin(pf*math.pi)*50)
            # player celebrating
            draw_person(screen, cage_x-80, cy, player_char, size=20,
                       face_dir=1,
                       arm_swing=math.sin(frame*0.2)*1.2 if pf>0.5 else 0.5,
                       is_female=is_f)
            # member flying into cage — shrink as they go in
            scale = max(8, int(16*(1-pf*0.5)))
            draw_person(screen, throw_x, throw_y, m_char, size=scale,
                       face_dir=-1, is_female=m_is_f)
            # cage (always visible, no alpha fade to avoid error)
            draw_cage_icon(screen, cage_x+20, cage_y, w=50, h=44)
            # stars/impact
            if pf > 0.8:
                for s in range(6):
                    sang = s*(math.pi/3)+frame*0.2
                    sx2 = throw_x+int(math.cos(sang)*20*pf)
                    sy2 = throw_y+int(math.sin(sang)*20*pf)
                    pygame.draw.circle(screen,C_YELLOW,(sx2,sy2),3)

        # ── Phase 4: fade to text ──
        else:
            pf = (frame-180)/40
            draw_person(screen, cage_x-80, cy, player_char, size=20,
                       face_dir=1, arm_swing=0.4, is_female=is_f)
            draw_cage_icon(screen, cage_x+20, cage_y, w=50, h=44)
            # member tiny inside cage
            draw_person(screen, cage_x+20, cage_y+8, m_char, size=8,
                       face_dir=-1, is_female=m_is_f)
            # text fade in
            a2=int(min(1,pf*2)*255)
            msg=FNT_POP.render(f"{member['name']} has been trapped!",True,C_YELLOW)
            msg.set_alpha(a2)
            screen.blit(msg,(WIN_W//2-msg.get_width()//2, cy+110))
            sub=FNT_SMALL.render("(Press any key to continue)",True,(140,140,160))
            sub.set_alpha(a2)
            screen.blit(sub,(WIN_W//2-sub.get_width()//2, cy+140))
            if pf>=0.9:
                present()
                # wait for keypress
                waiting=True
                while waiting:
                    clock.tick(FPS)
                    for ev in pygame.event.get():
                        if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
                        if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                            waiting=False
                    present()
                return

        # title bar during cutscene
        pygame.draw.rect(screen,C_HUD_BG,(0,0,WIN_W,36))
        lbl=FNT_MED.render(f"CAUGHT!  {member['name']}  —  skip: ESC",True,(140,140,160))
        screen.blit(lbl,(10,10))
        present()

# ═════════════════════════════════════════════════════════════════════════════
#  MAIN GAME
# ═════════════════════════════════════════════════════════════════════════════
def run_game(player_name, player_char):
    start_time=time.time()
    caught=0; progress=0
    particles=[]; popup_msg=""; popup_timer=0.0
    win=False; lose=False; loss_msg=""; tick=0; rpc_timer=0.0
    shake_x=0; shake_y=0; shake_timer=0
    pending_cutscene=None
    save_status_msg=""
    save_status_timer=0.0
    hud_quit_rect = pygame.Rect(0, 0, 0, 0)
    hud_defeat_rect = pygame.Rect(0, 0, 0, 0)
    hud_save_rect = pygame.Rect(0, 0, 0, 0)

    # actual logical positions
    px,py=1.0,1.0
    # visual (lerped) positions
    vx,vy=1.0,1.0
    stamina=float(STAMINA_MAX)
    move_dir_x=1

    is_female=(player_char["gender"]=="f")

    members=[]
    used=set()
    spawn_zones = random.sample(SPAWN_ZONES, k=len(FAMILY))
    for fam, zone in zip(FAMILY, spawn_zones):
        cell = rand_floor_in_zone(zone, used)
        used.add(cell)
        ang=random.uniform(0,2*math.pi)
        members.append({
            **fam,
            "x":float(cell[0]),"y":float(cell[1]),
            "vx2":math.cos(ang)*ROAM_SPEED,"vy2":math.sin(ang)*ROAM_SPEED,
            "vis_x":float(cell[0]),"vis_y":float(cell[1]),
            "move_timer":random.randint(80,200),
            "alert_anim":0,"fleeing":False,"caught":False,"stuck_timer":0,
        })

    update_rpc(player_name,caught,progress,start_time)

    def save_current_run(source="manual"):
        nonlocal save_status_msg, save_status_timer
        SAVE_DATA["player_name"] = player_name
        SAVE_DATA["last_character"] = player_char.get("label")
        SAVE_DATA["runs_played"] = int(SAVE_DATA.get("runs_played", 0))
        SAVE_DATA["best_caught"] = max(int(SAVE_DATA.get("best_caught", 0)), caught)
        SAVE_DATA["best_progress"] = max(int(SAVE_DATA.get("best_progress", 0)), progress)
        SAVE_DATA["currency"] = int(SAVE_DATA.get("currency", 0))
        SAVE_DATA["current_run"] = {
            "player_name": player_name,
            "character": player_char.get("label"),
            "caught": caught,
            "progress": progress,
            "win": win,
            "lose": lose,
            "stamina": round(stamina, 2),
            "timestamp": time.time(),
            "source": source,
        }
        if write_save_data(SAVE_DATA):
            save_status_msg = "Saved."
            save_status_timer = 1.6
            return True
        save_status_msg = "Save failed."
        save_status_timer = 1.6
        return False

    def build_fog(pgx,pgy):
        fog_surf.fill((0,0,0,255))
        cx2=int(pgx*TILE+TILE//2); cy2=int(pgy*TILE+TILE//2)
        r=int(3.6*TILE); fade_start=0.60
        for dy in range(-r,r+1):
            dx_max=int(math.sqrt(max(0,r*r-dy*dy)))
            for dx in range(-dx_max,dx_max+1):
                dist=math.sqrt(dx*dx+dy*dy)/r
                alpha=0 if dist<=fade_start else int(((dist-fade_start)/(1-fade_start))**1.3*255)
                sx,sy=cx2+dx,cy2+dy
                if 0<=sx<WIN_W and 0<=sy<WIN_H-64:
                    fog_surf.set_at((sx,sy),(0,0,0,alpha))

    def draw_final_hint():
        remaining = [m for m in members if not m["caught"]]
        if len(remaining) > 2:
            return
        if not remaining:
            return
        target = min(remaining, key=lambda m: math.hypot(m["x"]-px, m["y"]-py))
        ang = math.atan2(target["y"] - py, target["x"] - px)
        cx = WIN_W // 2
        cy = 58
        vec_x = math.cos(ang)
        vec_y = math.sin(ang)
        tip = (cx + int(vec_x * 20), cy + int(vec_y * 20))
        left = (cx + int(math.cos(ang + 2.6) * 12), cy + int(math.sin(ang + 2.6) * 12))
        right = (cx + int(math.cos(ang - 2.6) * 12), cy + int(math.sin(ang - 2.6) * 12))
        pulse = 160 + int(60 * (0.5 + 0.5 * math.sin(tick * 0.2)))
        hint_surf = pygame.Surface((WIN_W, 82), pygame.SRCALPHA)
        pygame.draw.polygon(hint_surf, (255, 220, 80, pulse), [tip, left, right])
        txt = FNT_SMALL.render("You hear movement nearby...", True, (220, 210, 170))
        hint_surf.blit(txt, (cx - txt.get_width() // 2, 22))
        screen.blit(hint_surf, (0, 0))

    def wall_at(gx,gy):
        c,r=int(gx),int(gy)
        if c<0 or c>=COLS or r<0 or r>=ROWS: return True
        return LEVEL[r][c]==1

    def can_move(nx,ny,margin=0.27):
        for ox,oy in [(margin,margin),(1-margin,margin),(margin,1-margin),(1-margin,1-margin)]:
            if wall_at(nx+ox,ny+oy): return False
        return True

    def spawn_particles(gx,gy,col,n=26):
        base_col = safe_rgb(col, C_YELLOW)
        for _ in range(n):
            ang2=random.uniform(0,2*math.pi); spd=random.uniform(0.5,3.5)
            particles.append({"x":gx*TILE+TILE//2,"y":gy*TILE+TILE//2,
                "vx":math.cos(ang2)*spd,"vy":math.sin(ang2)*spd-2.0,
                "life":random.randint(25,60),"col":base_col,"r":random.randint(2,5)})

    def draw_map(ox,oy):
        for r in range(ROWS):
            for c in range(COLS):
                x,y=c*TILE+ox,r*TILE+oy+64
                if LEVEL[r][c]==1:
                    pygame.draw.rect(screen,C_WALL_S,(x+2,y+2,TILE,TILE))
                    pygame.draw.rect(screen,C_WALL,(x,y,TILE,TILE))
                    pygame.draw.rect(screen,C_WALL_T,(x,y,TILE,5))
                    pygame.draw.rect(screen,C_WALL_T,(x,y,5,TILE))
                else:
                    shade,shade2=floor_shade(c,r)
                    col=shade if (c+r)%2==0 else shade2
                    pygame.draw.rect(screen,col,(x,y,TILE,TILE))
                    pygame.draw.rect(screen,(0,0,0,30),(x,y,TILE,1))
                    pygame.draw.rect(screen,(0,0,0,30),(x,y,1,TILE))

        # room dressing so the house reads as a lived-in space
        # kitchen
        pygame.draw.rect(screen, (76, 58, 34), (16*TILE+ox+4, 1*TILE+oy+64+8, 6*TILE-8, 16), border_radius=3)
        pygame.draw.rect(screen, (98, 84, 60), (17*TILE+ox+4, 2*TILE+oy+64+2, 5*TILE-8, 12), border_radius=3)
        pygame.draw.rect(screen, (160, 168, 176), (22*TILE+ox+8, 1*TILE+oy+64+6, TILE-16, 2*TILE-12), border_radius=4)
        pygame.draw.rect(screen, (210, 210, 220), (22*TILE+ox+12, 1*TILE+oy+64+10, TILE-24, 12), border_radius=3)
        pygame.draw.rect(screen, (60, 60, 70), (22*TILE+ox+17, 1*TILE+oy+64+25, 14, 18), border_radius=2)

        # living room
        pygame.draw.rect(screen, (62, 74, 88), (10*TILE+ox+10, 5*TILE+oy+64+10, 4*TILE-20, 2*TILE-20), border_radius=10)
        pygame.draw.rect(screen, (86, 96, 108), (11*TILE+ox+6, 6*TILE+oy+64+6, 3*TILE-12, TILE-18), border_radius=8)
        pygame.draw.rect(screen, (92, 72, 48), (12*TILE+ox+14, 6*TILE+oy+64+10, TILE-28, 16), border_radius=4)
        pygame.draw.rect(screen, (138, 118, 84), (12*TILE+ox+2, 4*TILE+oy+64+12, 3*TILE-4, 14), border_radius=3)
        pygame.draw.rect(screen, (112, 92, 68), (12*TILE+ox+10, 4*TILE+oy+64+8, TILE-20, 10), border_radius=3)

        # bedroom / office
        pygame.draw.rect(screen, (132, 96, 74), (2*TILE+ox+6, 11*TILE+oy+64+8, 4*TILE-12, 2*TILE-16), border_radius=8)
        pygame.draw.rect(screen, (220, 212, 206), (2*TILE+ox+12, 11*TILE+oy+64+12, 3*TILE-24, 12), border_radius=3)
        pygame.draw.rect(screen, (180, 170, 160), (5*TILE+ox+10, 13*TILE+oy+64+8, TILE+4, TILE-10), border_radius=4)
        pygame.draw.rect(screen, (96, 72, 52), (5*TILE+ox+20, 13*TILE+oy+64+16, 18, 18), border_radius=2)
        pygame.draw.rect(screen, (72, 78, 92), (6*TILE+ox+8, 14*TILE+oy+64+14, 18, 18), border_radius=3)

        # dining / hall accents
        pygame.draw.ellipse(screen, (96, 82, 60), (10*TILE+ox+16, 10*TILE+oy+64+10, 3*TILE-32, 2*TILE-20))
        pygame.draw.rect(screen, (126, 110, 84), (13*TILE+ox+12, 11*TILE+oy+64+14, TILE-24, TILE-28), border_radius=5)
        pygame.draw.rect(screen, (70, 64, 82), (14*TILE+ox+8, 12*TILE+oy+64+4, TILE-16, 12), border_radius=3)

    def draw_hud(stam):
        nonlocal hud_quit_rect, hud_defeat_rect, hud_save_rect
        pygame.draw.rect(screen,C_HUD_BG,(0,0,WIN_W,64))
        pygame.draw.line(screen,C_WALL_T,(0,64),(WIN_W,64),2)
        tt=FNT_TITLE.render("Trap LEGO FAN 1's Family",True,C_YELLOW)
        screen.blit(tt,(10,8))
        pn=FNT_SMALL.render(f"Trapper: {player_name}",True,(160,200,255))
        screen.blit(pn,(10,34))
        bx,by,bw,bh=WIN_W//2-140,6,280,18
        pygame.draw.rect(screen,C_BAR_BG,(bx,by,bw,bh),border_radius=9)
        fw=int(bw*progress/100)
        bc=C_BAR_DONE if progress>=100 else C_BAR_FG
        if fw>0: pygame.draw.rect(screen,bc,(bx,by,fw,bh),border_radius=9)
        pygame.draw.rect(screen,C_WHITE,(bx,by,bw,bh),1,border_radius=9)
        pt=FNT_HUD.render(f"Progress: {progress}%",True,C_WHITE)
        screen.blit(pt,(bx+bw//2-pt.get_width()//2,by+1))
        sx2,sy2,sw,sh2=WIN_W//2-140,30,280,10
        pygame.draw.rect(screen,C_BAR_BG,(sx2,sy2,sw,sh2),border_radius=5)
        sf=int(sw*stam/STAMINA_MAX)
        sc=C_STAM_LO if stam<STAMINA_MAX*0.3 else C_STAM_HI
        if sf>0: pygame.draw.rect(screen,sc,(sx2,sy2,sf,sh2),border_radius=5)
        pygame.draw.rect(screen,(100,100,130),(sx2,sy2,sw,sh2),1,border_radius=5)
        sl=FNT_SMALL.render("SPRINT",True,(100,100,130))
        screen.blit(sl,(sx2+sw+6,sy2-1))
        ct=FNT_HUD.render(f"Caught: {caught}/{TOTAL_MEMBERS}",True,C_WHITE)
        screen.blit(ct,(WIN_W-ct.get_width()-12,8))
        ht=FNT_SMALL.render("WASD=move  SHIFT=sprint",True,(90,90,120))
        screen.blit(ht,(WIN_W-ht.get_width()-12,36))
        hud_save_rect = pygame.Rect(WIN_W-214, 34, 60, 20)
        hud_defeat_rect = pygame.Rect(WIN_W-148, 34, 60, 20)
        hud_quit_rect = pygame.Rect(WIN_W-82, 34, 60, 20)
        pygame.draw.rect(screen,(60,88,64),hud_save_rect,border_radius=5)
        pygame.draw.rect(screen,(110,150,118),hud_save_rect,1,border_radius=5)
        pygame.draw.rect(screen,(88,52,52),hud_defeat_rect,border_radius=5)
        pygame.draw.rect(screen,(150,80,80),hud_defeat_rect,1,border_radius=5)
        pygame.draw.rect(screen,(54,60,82),hud_quit_rect,border_radius=5)
        pygame.draw.rect(screen,(120,130,165),hud_quit_rect,1,border_radius=5)
        s_txt = FNT_SMALL.render("SAVE",True,C_WHITE)
        d_txt = FNT_SMALL.render("DEFEAT",True,C_WHITE)
        q_txt = FNT_SMALL.render("QUIT",True,C_WHITE)
        screen.blit(s_txt,(hud_save_rect.centerx-s_txt.get_width()//2,hud_save_rect.centery-s_txt.get_height()//2))
        screen.blit(d_txt,(hud_defeat_rect.centerx-d_txt.get_width()//2,hud_defeat_rect.centery-d_txt.get_height()//2))
        screen.blit(q_txt,(hud_quit_rect.centerx-q_txt.get_width()//2,hud_quit_rect.centery-q_txt.get_height()//2))
        if save_status_timer > 0 and save_status_msg:
            st=FNT_SMALL.render(save_status_msg,True,(170,220,170))
            screen.blit(st,(WIN_W-st.get_width()-12,56))

    def draw_popup(msg,alpha_f):
        txt=FNT_POP.render(msg,True,C_YELLOW)
        w,h=txt.get_width()+44,txt.get_height()+22
        x,y=WIN_W//2-w//2,WIN_H//2-h//2+40
        box=pygame.Surface((w,h),pygame.SRCALPHA); a=int(215*alpha_f)
        box.fill((18,18,36,a))
        pygame.draw.rect(box,(*C_YELLOW,a),(0,0,w,h),2,border_radius=10)
        screen.blit(box,(x,y))
        ts=pygame.Surface(txt.get_size(),pygame.SRCALPHA); ts.blit(txt,(0,0))
        ts.set_alpha(int(255*alpha_f)); screen.blit(ts,(x+22,y+11))

    def draw_win():
        ov=pygame.Surface((WIN_W,WIN_H),pygame.SRCALPHA); ov.fill((0,0,0,175))
        screen.blit(ov,(0,0))
        b=int(math.sin(tick*0.08)*8)
        m1=FNT_BIG.render("FAMILY FULLY TRAPPED!",True,C_YELLOW)
        m2=FNT_HUD.render(f"{player_name} caught them all — 100%!",True,C_BAR_FG)
        m3=FNT_SMALL.render("R = restart     ESC = quit",True,(170,170,200))
        screen.blit(m1,(WIN_W//2-m1.get_width()//2,WIN_H//2-70+b))
        screen.blit(m2,(WIN_W//2-m2.get_width()//2,WIN_H//2+b))
        screen.blit(m3,(WIN_W//2-m3.get_width()//2,WIN_H//2+44+b))

    def draw_lose():
        ov=pygame.Surface((WIN_W,WIN_H),pygame.SRCALPHA); ov.fill((0,0,0,185))
        screen.blit(ov,(0,0))
        b=int(math.sin(tick*0.08)*5)
        m1=FNT_BIG.render("DEFEATED",True,(255,120,120))
        m2=FNT_HUD.render(loss_msg or "The trap has failed.",True,C_WHITE)
        m3=FNT_SMALL.render("R = restart     ESC = quit",True,(170,170,200))
        screen.blit(m1,(WIN_W//2-m1.get_width()//2,WIN_H//2-70+b))
        screen.blit(m2,(WIN_W//2-m2.get_width()//2,WIN_H//2+b))
        screen.blit(m3,(WIN_W//2-m3.get_width()//2,WIN_H//2+44+b))

    # ── Main loop ────────────────────────────────────────────────────────────
    while True:
        dt=clock.tick(FPS)/1000.0
        tick+=1; rpc_timer+=dt

        # ── trigger pending cutscene outside of draw loop ──
        if pending_cutscene is not None:
            m=pending_cutscene; pending_cutscene=None
            play_capture_cutscene(player_name, player_char, m)
            if progress>=100: win=True

        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                save_current_run("exit")
                pygame.quit()
                if rpc_connected:
                    try: rpc.close()
                    except: pass
                sys.exit()
            if event.type==pygame.VIDEORESIZE:
                set_window_size(event.w, event.h)
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:
                    save_current_run("exit")
                    pygame.quit()
                    if rpc_connected:
                        try: rpc.close()
                        except: pass
                    sys.exit()
                if event.key==pygame.K_r and (win or lose): return True
            if event.type==pygame.MOUSEBUTTONDOWN:
                game_pos = window_to_game_pos(event.pos)
                if game_pos is not None:
                    if hud_save_rect.collidepoint(game_pos):
                        save_current_run("manual")
                        popup_msg = "Game saved."
                        popup_timer = 1.5
                        continue
                    if hud_quit_rect.collidepoint(game_pos):
                        save_current_run("exit")
                        pygame.quit()
                        if rpc_connected:
                            try: rpc.close()
                            except: pass
                        sys.exit()
                    if hud_defeat_rect.collidepoint(game_pos) and not win:
                        lose = True
                        loss_msg = "You chose to give up."
                        save_current_run("defeat")

        spd_frac=0.0; leg_s=0.0; arm_s=0.0; bob=0
        if not win and not lose:
            keys=pygame.key.get_pressed()
            dx,dy=0.0,0.0
            if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx-=1; move_dir_x=-1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx+=1; move_dir_x=1
            if keys[pygame.K_UP]    or keys[pygame.K_w]: dy-=1
            if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy+=1
            moving=dx!=0 or dy!=0
            sprinting=(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and moving and stamina>0

            if sprinting:
                stamina=max(0,stamina-STAMINA_DRAIN); spd=SPRINT_SPEED
            else:
                stamina=min(STAMINA_MAX,stamina+STAMINA_REGEN); spd=PLAYER_SPEED
                if stamina<10: spd*=0.7

            if moving:
                length = math.hypot(dx, dy)
                if length:
                    dx /= length
                    dy /= length
            if moving:
                spd_frac=spd/SPRINT_SPEED
                if can_move(px+dx*spd,py): px+=dx*spd
                if can_move(px,py+dy*spd): py+=dy*spd
                # more visible leg swing + body bob
                leg_s=math.sin(tick*0.5)*spd_frac*1.8
                arm_s=math.sin(tick*0.5+math.pi)*spd_frac*1.4
                bob = int(abs(math.sin(tick*0.5))*3*spd_frac)
                if sprinting and tick%6==0:
                    shake_x=random.randint(-1,1); shake_y=random.randint(-1,1); shake_timer=3
            if shake_timer>0: shake_timer-=1
            else: shake_x=0; shake_y=0

            # smooth visual lerp
            vx=lerp(vx,px,LERP_SPEED)
            vy=lerp(vy,py,LERP_SPEED)

            # ── Member AI ──
            for m in members:
                if m["caught"]: continue
                dist2=math.hypot(px-m["x"],py-m["y"])
                fspd=FLEE_SPEED*m["speed_mult"]
                if dist2<FLEE_RADIUS:
                    m["fleeing"]=True
                    m["alert_anim"]=min(30,m["alert_anim"]+3)
                    flee_ang=math.atan2(m["y"]-py,m["x"]-px)+random.uniform(-0.35,0.35)
                    fdx=math.cos(flee_ang)*fspd; fdy=math.sin(flee_ang)*fspd
                    moved=False
                    if can_move(m["x"]+fdx,m["y"]): m["x"]+=fdx; moved=True
                    if can_move(m["x"],m["y"]+fdy): m["y"]+=fdy; moved=True
                    if not moved:
                        for alt in [flee_ang+math.pi/2,flee_ang-math.pi/2,
                                    flee_ang+math.pi,flee_ang+random.uniform(-1,1)]:
                            adx=math.cos(alt)*fspd; ady=math.sin(alt)*fspd
                            if can_move(m["x"]+adx,m["y"]+ady):
                                m["x"]+=adx; m["y"]+=ady; break
                else:
                    m["fleeing"]=False
                    m["alert_anim"]=max(0,m["alert_anim"]-2)
                    m["move_timer"]-=1
                    if m["move_timer"]<=0:
                        ang2=random.uniform(0,2*math.pi); rspd=random.uniform(0.015,0.030)
                        m["vx2"]=math.cos(ang2)*rspd; m["vy2"]=math.sin(ang2)*rspd
                        m["move_timer"]=random.randint(60,220)
                    nx2=m["x"]+m["vx2"]; ny2=m["y"]+m["vy2"]
                    if can_move(nx2,m["y"]): m["x"]=nx2
                    else: m["vx2"]*=-1; m["move_timer"]=0
                    if can_move(m["x"],ny2): m["y"]=ny2
                    else: m["vy2"]*=-1; m["move_timer"]=0

                m["vis_x"]=lerp(m["vis_x"],m["x"],LERP_SPEED)
                m["vis_y"]=lerp(m["vis_y"],m["y"],LERP_SPEED)

            # ── Catch check ──
            for m in members:
                if m["caught"]: continue
                if math.hypot(px-m["x"],py-m["y"])<0.82:
                    m["caught"]=True
                    caught+=1
                    progress=int(round(caught * 100 / TOTAL_MEMBERS))
                    if caught>=TOTAL_MEMBERS: progress=100
                    spawn_particles(m["x"],m["y"],m["col"])
                    shake_x=random.randint(-3,3); shake_y=random.randint(-3,3); shake_timer=8
                    print(f"[GAME] {m['name']} caught! {caught}/{TOTAL_MEMBERS} {progress}%")
                    update_rpc(player_name,caught,progress,start_time)
                    save_current_run("auto")
                    pending_cutscene=m
                    popup_msg=f"{m['name']} has been trapped!"
                    popup_timer=3.0
                    break

            if popup_timer>0: popup_timer-=dt
            if save_status_timer>0: save_status_timer=max(0.0,save_status_timer-dt)

        if rpc_timer>=15:
            update_rpc(player_name,caught,progress,start_time); rpc_timer=0

        # ── Draw ─────────────────────────────────────────────────────────
        ox=shake_x; oy=shake_y
        screen.fill(C_BG)
        draw_map(ox,oy)

        # member characters
        for m in members:
            if not m["caught"]:
                m_is_f=m["id"] in ("mum","carina","dadsaunt","exwife","niece")
                m_char={"body":m["col"],"hair":tuple(max(0,c-55) for c in m["col"]),
                        "shirt":tuple(max(0,c-55) for c in m["col"]),"pants":(40,40,60)}
                mpx=int(m["vis_x"]*TILE+TILE//2+ox)
                mpy=int(m["vis_y"]*TILE+TILE//2+64+oy)
                f_leg=math.sin(tick*0.06+hash(m["id"]))*0.4 if m["fleeing"] else math.sin(tick*0.04+hash(m["id"]))*0.2
                draw_person(screen,mpx,mpy,m_char,size=14,
                           face_dir=-1,leg_swing=f_leg,arm_swing=f_leg,is_female=m_is_f)
                if m["alert_anim"]>0:
                    a_alpha=min(255,m["alert_anim"]*8)
                    excl=FNT_EXCL.render("!",True,C_RED); excl.set_alpha(a_alpha)
                    screen.blit(excl,(mpx-excl.get_width()//2,mpy-44))
                lbl=FNT_SMALL.render(m["name"],True,m["col"])
                screen.blit(lbl,(mpx-lbl.get_width()//2,mpy-38))

        # player with bob and equipment
        ppx=int(vx*TILE+TILE//2+ox)
        ppy=int(vy*TILE+TILE//2+64+oy)
        draw_person(screen,ppx,ppy,player_char,size=16,
                   face_dir=move_dir_x,leg_swing=leg_s,arm_swing=arm_s,
                   bob=bob, is_female=is_female)

        # rope coil in hand
        hand_offset_x = 14 * move_dir_x
        hand_offset_y = -8
        bob_equip = bob  # sync with body bob
        coil_x = ppx + hand_offset_x
        coil_y = ppy + hand_offset_y + bob_equip
        pygame.draw.circle(screen, C_ROPE, (coil_x, coil_y), 5, 2)
        pygame.draw.circle(screen, C_ROPE, (coil_x + move_dir_x*2, coil_y + 1), 4, 2)
        pygame.draw.circle(screen, (220, 180, 80), (coil_x, coil_y), 3)

        # player name
        pnl=FNT_SMALL.render(player_name,True,C_YELLOW)
        screen.blit(pnl,(ppx-pnl.get_width()//2,ppy-44))

        # particles
        alive=[]
        for p in particles:
            p["x"]+=p["vx"]; p["y"]+=p["vy"]; p["vy"]+=0.14; p["life"]-=1
            if p["life"]>0:
                a=clamp(255*p["life"]/55)
                ps=pygame.Surface((p["r"]*2,p["r"]*2),pygame.SRCALPHA)
                pygame.draw.circle(ps,safe_rgba(p["col"],a),(p["r"],p["r"]),p["r"])
                screen.blit(ps,(int(p["x"])-p["r"],int(p["y"])-p["r"]))
                alive.append(p)
        particles[:]=alive

        if not lose:
            build_fog(vx,vy)
            screen.blit(fog_surf,(0,64))
        draw_hud(stamina)
        if not win and not lose:
            draw_final_hint()
        if popup_msg and popup_timer>0:
            draw_popup(popup_msg,min(1.0,popup_timer/0.5))
        if win:
            draw_win()
        elif lose:
            draw_lose()
        present()

# ═════════════════════════════════════════════════════════════════════════════
#  ENTRY
# ═════════════════════════════════════════════════════════════════════════════
while True:
    name  = name_entry_screen()
    char  = char_select_screen(name)
    again = run_game(name, char)
    if not again: break

pygame.quit()
if rpc_connected:
    try: rpc.close()
    except: pass
sys.exit()
