# whisprPTT

Push-to-talk speech-to-text dictation for Windows. Hold a hotkey or mouse button, speak, release — your words are typed at the cursor. No cloud. Runs entirely local using [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## How it works

- Hold **Right Ctrl** or **Mouse X2** (forward thumb button) to start recording
- Release to transcribe and type the text at your cursor
- Works in any application that accepts keyboard input

## Requirements

- Windows 10/11
- Python 3.10+ (or use the prebuilt `.exe`)
- A microphone

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On first run, faster-whisper will download the Whisper model (~240 MB for `small.en`).

## Usage

```bash
python whispr_ptt.py
```

```bash
# List available microphone indices
python whispr_ptt.py --list-mics
```

## Configuration

Edit the constants at the top of `whispr_ptt.py`:

| Setting | Default | Description |
|---|---|---|
| `MODEL_SIZE` | `small.en` | Whisper model. Smaller = faster, larger = more accurate. Options: `tiny.en`, `base.en`, `small.en`, `medium.en`, `large-v3` |
| `DEVICE` | `auto` | `cuda` for GPU, `cpu` for CPU, `auto` to detect |
| `COMPUTE_TYPE` | `int8` | `int8` (fast, low RAM), `float16` (GPU), `float32` (most accurate) |
| `MIC_INDEX` | `None` | Pin a specific microphone by index. Run `--list-mics` to find yours. `None` uses the system default. |
| `HOTKEY` | `ctrl_r` | Keyboard key that triggers recording |
| `MOUSE_BUTTON` | `x2` | Mouse button that triggers recording |
| `HALLUCINATE_THRESHOLD` | `300` | Skip audio below this amplitude (prevents transcribing silence) |

## Build a standalone executable

Requires PyInstaller:

```bash
pip install pyinstaller
pyinstaller whispr_ptt.spec
```

Output is in `dist/whispr/whispr.exe`. Copy the entire `dist/whispr/` folder to any Windows machine — no Python needed.

## Privacy

All transcription runs locally. No audio or text is sent to any server.

## License

MIT
