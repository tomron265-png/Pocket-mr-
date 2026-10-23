# PocketMR Remote Desktop — early working prototype

This project extends the PocketMR Handspace idea with a movable Remote Desktop panel and a Windows companion. The panel receives JPEG desktop frames over an authenticated WebSocket and sends mouse, scroll, keyboard, and text input to the companion.

## Important limits

- This is an early prototype, not a polished or audited remote-access product.
- The first version sends desktop frames at a modest frame rate (default 10 fps). It can show and control ordinary desktop apps and may show games, but it is **not** a substitute for Sunshine/Moonlight for high-frame-rate gaming. For competitive games, use a dedicated game-streaming solution.
- The companion controls the interactive desktop session. UAC secure-desktop prompts, the Windows lock screen, protected video, and some elevated apps may not be capturable or controllable.
- The page's SBS VR mode is a visual layout preview, not true stereoscopic rendering or head tracking.
- Camera/hand tracking requires an HTTPS site (or localhost) and internet access to load MediaPipe assets.
- Only connect through a private network you control. Do not port-forward port 8765 or expose it directly to the public internet.

## Part A — Run the Windows companion

1. On your Windows 11 Pro PC, install Python 3.11 or 3.12 from <https://www.python.org/downloads/windows/>. During installation, check **Add Python to PATH**.
2. Extract this project folder somewhere you can find it, such as your Desktop.
3. Open `windows-companion` and double-click `setup_windows.bat`. Wait for it to finish.
4. Double-click `start_companion.bat`. Leave its window open. It prints a long private token; the same token is saved in `token.txt`. Keep it secret.
5. On the PC itself, open <http://127.0.0.1:8765/>. A small JSON status response means the companion is running.

## Part B — Secure access from anywhere with Tailscale

1. Install Tailscale on the PC from <https://tailscale.com/download> and sign in.
2. Install Tailscale on your Galaxy S10 from the Google Play Store and sign in to the **same tailnet/account**.
3. Confirm both devices show as connected in Tailscale.
4. On the PC, open a normal PowerShell window and run:

   ```powershell
   tailscale serve --bg 8765
   tailscale serve status
   ```

   Tailscale Serve publishes the local companion through your tailnet's HTTPS endpoint. Use the hostname shown by `tailscale serve status`. Do not use Funnel and do not open router ports.
5. Keep the PC awake and the companion running whenever you want to connect remotely. Use Ethernet if possible for best performance.

If the `tailscale serve` command differs in your installed version, consult <https://tailscale.com/kb/1312/serve/>. You should see an HTTPS hostname similar to `https://your-pc.your-tailnet.ts.net`. In PocketMR, use its WebSocket form by replacing `https://` with `wss://` and adding `/ws`, for example `wss://your-pc.your-tailnet.ts.net/ws`.

## Part C — Open the phone web app

The file `web/index.html` is the PocketMR phone interface. For camera access, host the `web` folder on an HTTPS static host (GitHub Pages is one option), or use an HTTPS site you already control. You can still open it locally to inspect the interface, but browsers may block camera access from a `file://` page.

In PocketMR:

1. Tap **Remote PC**.
2. Paste the secure `wss://.../ws` address from Tailscale Serve.
3. Paste the private token printed by `start_companion.bat`.
4. Tap **Connect to PC**. The desktop should appear in the panel.
5. Tap the desktop image to click; hold and move to drag. Use the shortcut buttons or **Type text…** for keyboard input.

## Security notes

- The token grants control of the Windows desktop. Never post it in a public repository, screenshot, or chat.
- Tailscale access is restricted to your tailnet, but anyone who has both tailnet access and the token may control the PC. Use device approval and account MFA if available.
- The prototype currently sends the token in the WebSocket query string. Avoid sharing browser URLs or diagnostic logs that might contain it. A future production version should use a short-lived session handshake instead.
- Do not connect from a shared/untrusted device. Disconnect in PocketMR when finished.

## Project layout

- `web/index.html` — mobile-first PocketMR interface and Remote Desktop panel
- `web/PocketMR_Handspace_legacy.html` — copy of the previous Handspace prototype
- `windows-companion/companion.py` — desktop capture and input companion
- `windows-companion/setup_windows.bat` — installs the Python environment
- `windows-companion/start_companion.bat` — starts the companion
