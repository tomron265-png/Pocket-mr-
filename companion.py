"""PocketMR Windows Companion: authenticated desktop JPEG stream + mouse/keyboard input.
Use only on your own PC and private Tailscale network. Designed as an early prototype.
"""
import asyncio, json, os, secrets, sys, time
from pathlib import Path
from aiohttp import web, WSMsgType
import mss
from PIL import Image
import io
import pyautogui

BASE = Path(__file__).resolve().parent
TOKEN_FILE = BASE / "token.txt"
HOST = "127.0.0.1"
PORT = int(os.environ.get("POCKETMR_PORT", "8765"))
FPS = max(1, min(15, int(os.environ.get("POCKETMR_FPS", "10"))))
JPEG_QUALITY = max(25, min(85, int(os.environ.get("POCKETMR_JPEG_QUALITY", "55"))))
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


def get_token():
    if TOKEN_FILE.exists():
        value = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = secrets.token_urlsafe(32)
    TOKEN_FILE.write_text(value, encoding="utf-8")
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass
    return value

TOKEN = get_token()
ALLOWED_KEYS = {
    "enter": "enter", "esc": "esc", "escape": "esc", "backspace": "backspace",
    "tab": "tab", "up": "up", "down": "down", "left": "left", "right": "right",
    "space": "space", "delete": "delete", "home": "home", "end": "end",
    "pageup": "pageup", "pagedown": "pagedown", "f1": "f1", "f2": "f2", "f3": "f3",
    "f4": "f4", "f5": "f5", "f6": "f6", "f7": "f7", "f8": "f8", "f9": "f9",
    "f10": "f10", "f11": "f11", "f12": "f12"
}

async def index(request):
    return web.json_response({"service": "PocketMR Windows Companion", "status": "running", "websocket": "/ws", "security": "token required"})

async def websocket(request):
    supplied = request.query.get("token", "")
    if not secrets.compare_digest(supplied, TOKEN):
        return web.Response(status=401, text="Unauthorized")
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=1024 * 1024)
    await ws.prepare(request)
    with mss.mss() as sct:
        monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        width, height = monitor["width"], monitor["height"]
        await ws.send_str(json.dumps({"type": "hello", "width": width, "height": height, "fps_target": FPS}))
        stop = asyncio.Event()

        async def stream_screen():
            interval = 1.0 / FPS
            while not stop.is_set() and not ws.closed:
                started = time.monotonic()
                try:
                    shot = sct.grab(monitor)
                    image = Image.frombytes("RGB", shot.size, shot.rgb)
                    # Downscale large desktops to reduce mobile bandwidth and latency.
                    max_width = 1600
                    if image.width > max_width:
                        new_h = round(image.height * max_width / image.width)
                        image = image.resize((max_width, new_h), Image.Resampling.BILINEAR)
                    buff = io.BytesIO()
                    image.save(buff, format="JPEG", quality=JPEG_QUALITY, optimize=True)
                    await ws.send_bytes(buff.getvalue())
                except (ConnectionResetError, asyncio.CancelledError):
                    break
                except Exception as exc:
                    try:
                        await ws.send_str(json.dumps({"type": "error", "message": "Screen capture failed: " + str(exc)[:180]}))
                    except Exception:
                        break
                await asyncio.sleep(max(0, interval - (time.monotonic() - started)))

        streamer = asyncio.create_task(stream_screen())
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await handle_input(data, width, height)
                    except Exception as exc:
                        await ws.send_str(json.dumps({"type": "error", "message": "Input rejected: " + str(exc)[:140]}))
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                    break
        finally:
            stop.set()
            streamer.cancel()
            try:
                await streamer
            except (asyncio.CancelledError, Exception):
                pass
    return ws

async def handle_input(data, width, height):
    kind = data.get("type")
    if kind in ("mouse_move", "mouse_down", "mouse_up"):
        x = int(max(0, min(width - 1, float(data.get("x", 0)) * width)))
        y = int(max(0, min(height - 1, float(data.get("y", 0)) * height)))
        if kind == "mouse_move":
            pyautogui.moveTo(x, y, _pause=False)
        else:
            button = "right" if data.get("button") == "right" else "left"
            pyautogui.moveTo(x, y, _pause=False)
            (pyautogui.mouseDown if kind == "mouse_down" else pyautogui.mouseUp)(button=button)
    elif kind == "scroll":
        amount = int(max(-10, min(10, int(data.get("dy", 0)))))
        if amount:
            pyautogui.scroll(-amount)
    elif kind == "key":
        key = str(data.get("key", "")).lower()
        if key not in ALLOWED_KEYS:
            return
        (pyautogui.keyDown if data.get("down") else pyautogui.keyUp)(ALLOWED_KEYS[key])
    elif kind == "shortcut":
        name = str(data.get("name", ""))
        shortcuts = {
            "alt-tab": ["alt", "tab"], "win": ["win"], "esc": ["esc"], "enter": ["enter"],
            "ctrl-alt-del": ["ctrl", "alt", "delete"]
        }
        keys = shortcuts.get(name)
        if keys:
            pyautogui.hotkey(*keys)
    elif kind == "text":
        value = str(data.get("text", ""))[:500]
        # Avoid control chars; pyautogui writes literal text where supported.
        value = "".join(ch for ch in value if ch >= " " or ch in "\n\t")
        if value:
            pyautogui.write(value, interval=0.001)

async def on_startup(app):
    print("\nPocketMR Windows Companion is running.")
    print(f"Local status: http://127.0.0.1:{PORT}/")
    print(f"Listening on port {PORT}. Use Tailscale Serve for secure HTTPS/WSS access.")
    print("Token is stored in token.txt beside this script. Keep it private.\n")

app = web.Application(client_max_size=1024 * 1024)
app.router.add_get("/", index)
app.router.add_get("/ws", websocket)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    print("PocketMR companion token:")
    print(TOKEN)
    print("Copy this token into PocketMR on your phone. Do not share it.\n")
    web.run_app(app, host=HOST, port=PORT, access_log=None)
