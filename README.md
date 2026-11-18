<div align="center">

# 「 V e X L 」
### _encoding system // pattern: blue_


`STATUS: BETA — SYNCHRONIZATION IN PROGRESS`

</div>

---

## ▚ CONFIGURATION // MAGI PARAMETERS

_(For local/VPS deployment, rename [.env.sample](.env.sample) to `.env` and edit accordingly.)_
_(list of available variables isn't complete.)_

### ● Required

| Variable | Function |
|:---|:---|
| `APP_ID` `API_HASH` `BOT_TOKEN` | First two from *[Telegram.org](https://telegram.org)*, third from *[@Botfather](https://t.me/botfather)* |
| `OWNER` | User IDs authorized to command VeXL, space-separated |

### ● Optional

| Variable | Function |
|:---|:---|
| `THUMBNAIL` `ICON` | Telegraph link to image used as thumbnail / watermark |
| `FFMPEG` | Custom FFmpeg or HandBrake-CLI command, with `"""{}"""` as input/output placeholders. Example: `ffmpeg -i """{}""" -preset veryfast -vcodec libx265 -crf 27 """{}"""` — escape `"` characters for local deployment |
| `TEMP_USERS` | Additional restricted users allowed to operate VeXL |
| `LOG_CHANNEL` | Log group/channel ID (VeXL must be admin) |
| `DATABASE_URL` | Valid MongoDB database URL |
| `ENCODER` | Encoder name/alias included in captions, may include encode info |
| `FCHANNEL` `FCHANNEL_STATS` | Channel ID where only output videos are forwarded; message ID used as live encode status |
| `LOGS_IN_CHANNEL` `bool` | Send error logs to log channel — off by default |
| `ALWAYS_DEPLOY_LATEST` `bool` | Pull latest code from upstream (or default repo) on startup |
| `CMD_SUFFIX` | VeXL only responds to commands ending in this suffix |
| `TELEGRAPH_API` | Alternate API to `api.telegra.ph` for posting mediainfo |
| `LOCK_ON_STARTUP` | Pause VeXL on startup until manually unpaused |
| `FS_THRESHOLD` | Sleep threshold (seconds) on floodwait |
| `ALLOW_ACTION` `bool` | Enable/disable encoding chat actions |
| `UPSTREAM_REPO` `UPSTREAM_BRANCH` | Custom repo + branch for the update function — *note: update fails if new dependencies are introduced; redeploy instead* |
| `SKIP_VIDEO_CHECK` `bool` | Skip video validation for links — accept all links without checking (default: false). Resets on restart. |
| `BUZZHEAVIER_TOKEN` | BuzzHeavier.com Account ID (optional — from [buzzheavier.com](https://buzzheavier.com/), authenticated uploads) |
| `FILEDITCH_TOKEN` | Fileditch.com API token (optional — from [new.fileditch.com](https://new.fileditch.com/), account uploads) |
| `PIXELDRAIN_API_KEY` | Pixeldrain.com API key (required — from [pixeldrain.com](https://pixeldrain.com/), no anonymous uploads) |
| `TELEGRAM_UPLOAD_LIMIT` | Max file size for Telegram upload (default: 2126000000 = 2GB) |
| `FILE_HOST_PRIMARY` | Primary file host: `buzzheavier`, `fileditch`, or `pixeldrain` (default: `buzzheavier`) |
| `FILE_HOST_FALLBACK` | First fallback file host: `buzzheavier`, `fileditch`, or `pixeldrain` (default: `fileditch`) |
| `FILE_HOST_FALLBACK2` | Second fallback file host: `buzzheavier`, `fileditch`, or `pixeldrain` (default: `pixeldrain`) |

---

## ▚ COMMAND INTERFACE

```
start        - check if VeXL is awake, get usage
restart      - restart VeXL
update       - update VeXL
nuke         - ☢️ nuke VeXL
bash         - /bash + command
eval         - evaluate code
peval        - eval, pyrogram context
pause        - halt encoding
ping         - ping!
add          - queue a video
leech        - queue a link
qbleech      - queue a torrent link
select       - select files from a batch to encode
permit       - grant temporary user access
unpermit     - revoke temporary user access
queue        - list current queue
batch        - preview batches
list         - list all files in a torrent
forward      - manually forward a message to fchannel
v            - toggle v2/v3/v4… (with message)
download     - download a file or link
upload       - upload from local directory or link
rename       - rename a video file/link
mediainfo    - get mediainfo of a replied file/link
mux          - remux a file
get          - view current ffmpeg code
set          - set custom ffmpeg code
reset        - reset default ffmpeg code
filter       - filter & stuff
vfilter      - view filter
delfilter    - delete filter
rss          - edit, delete, subscribe to rss feeds
anime        - get anime info
airing       - get anime's airing info
setrename    - set custom_rename format
name         - quick filter with anime_title
vname        - list name filters
delname      - delete a name filter
status       - 🆕 get VeXL's status
showthumb    - 🖼️ show current thumbnail
parse        - toggle caption/anilist parsing
groupenc     - toggle encoding in groups
svc / skipvideocheck - toggle video validation check for links (owner only)
cancelall    - ❌ clear cached downloads & queued files
clear        - clear queued files
logs         - get VeXL's logs
filehost     - 🆕 configure file hosting for large files
forcehost    - 🆕 force file hosting for encoded files
help         - same as start
```

---

## ▚ FILE HOSTING FOR LARGE FILES (>2GB)

When an encoded file exceeds Telegram's 2GB bot upload limit, VeXL automatically uploads to a file host and sends the download link instead.

**Supported hosts:**
| Host | Auth | Limits | Notes |
|:---|:---|:---|:---|
| **buzzheavier.com** | Optional Account ID | No explicit limit | Primary by default, fast & reliable |
| **fileditch.com** | Optional token | 150GB/file (250GB with token) | First fallback |
| **pixeldrain.com** | Required API key | Unlimited with key | Second fallback |

**Runtime configuration:**
```
/filehost                  # Show interactive configuration panel with buttons
/filehost reset            # Reset to defaults (buzzheavier → fileditch → pixeldrain)
```

**Interactive Panel:**
When you run `/filehost`, an inline keyboard appears showing:
- Three rows for each position (Primary, Fallback, Fallback 2)
- Buttons to select any host for each position (buzzheavier, fileditch, pixeldrain, or disabled)
- Reset and Close buttons

Tap any button to instantly change the configuration — no command arguments needed.

**Force File Host (resets on restart):**
```
/forcehost on      # Force ALL encoded files to file host
/forcehost off     # Disable force file host (default)
/forcehost show    # Show current status
```

**Skip Video Check (resets on restart):**
By default, VeXL validates that leech/qbleech links point to actual video files (checking file extension, Content-Type header, and magic bytes). Some direct-download links fail this check even when they are videos.

```
/svc on        # Skip video check — accept ALL links without validation
/svc off       # Enable video validation (default)
/svc           # Show current state
```
Equivalent long command: `/skipvideocheck on|off`

Also configurable via `SKIP_VIDEO_CHECK=true` in `.env` (persists across restarts).

---

## ▚ DEPLOYMENT PROTOCOL

**With Docker**
1. Install Docker
2. Clone repository to preferred location
3. Ensure you're in the directory containing `Dockerfile` and `.env`
4. *(Optional, faster build — don't run from `scripts/`)*:
   `python3 scripts/update_docker.py` — to undo: `python3 scripts/update_docker.py undo`
5. Run:
   ```
   docker build . -t vexl
   docker run vexl
   ```

**Without Docker**
- Install dependencies — see [Dockerfile](Dockerfile) or [local_deploy.sh](scripts/local_deploy.sh) *(unmaintained — run at your own risk)*
- Requires `python3.10`, `ffmpeg`, `ffprobe`, `mediainfo`
- Run:
  - `bash run.sh` — normal start
  - `bash srun.sh` — silent start

---

## ▚ FEATURES
_`[ DATA CLASSIFIED — PENDING DISCLOSURE ]`_

---

<div align="center">

### ⋄ SOURCE
Heavily modified fork of *[Danish CompressorQueue](https://github.com/1Danish-00/CompressorQueue)*

`VeXL // an encoding entity`

