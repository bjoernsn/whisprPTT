# WhisperPTT

<p align="center">
  <img src="whisprPTT.png" width="160" alt="WhisperPTT logo">
</p>

Push-to-talk speech-to-text dictation for Windows. Hold a hotkey or mouse button, speak, release — your words are typed at the cursor. Runs as a **system tray app** with no console window. No cloud, no internet required — everything runs locally using [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## How it works

- Hold **Right Ctrl** or **Mouse X2** (forward thumb button) to record
- Release to transcribe and type the text at your cursor
- Whisper PTT sits in the system tray — right-click to quit
- Works in any application that accepts keyboard input

## Quick start (prebuilt exe)

1. Download the latest `whispr.zip` from [Releases](../../releases)
2. Extract the zip anywhere
3. Double-click `whispr.exe`
4. A mic icon appears in your system tray — you're ready

> **First launch note:** Windows may show a SmartScreen warning ("Windows protected your PC"). Click **More info → Run anyway**. This is standard for unsigned open-source software.

> **First run:** faster-whisper downloads the Whisper model (~240 MB for `small.en`) on first launch. This happens once.

## Run from source

**Requirements:** Windows 10/11, Python 3.10+

```bat
:: 1. Install dependencies
setup.bat

:: 2. Run
.venv\Scripts\activate
python whispr_ptt.py

:: 3. List available microphone indices (if default mic isn't right)
python whispr_ptt.py --list-mics
```

## Build the exe yourself

```bat
build.bat
```

Output is in `dist\whispr\`. Zip the entire folder to share — no Python needed on the target machine.

## Configuration

Edit the constants at the top of `whispr_ptt.py`:

| Setting | Default | Description |
|---|---|---|
| `MODEL_SIZE` | `small.en` | Whisper model size. Smaller = faster, larger = more accurate. Options: `tiny.en`, `base.en`, `small.en`, `medium.en`, `large-v3` |
| `DEVICE` | `auto` | `cuda` for GPU, `cpu` to force CPU, `auto` to detect |
| `COMPUTE_TYPE` | `int8` | `int8` (fast/low RAM), `float16` (GPU), `float32` (most accurate) |
| `MIC_INDEX` | `None` | Pin a specific mic by index. Run `--list-mics` to find yours. `None` = system default. |
| `HOTKEY` | `ctrl_r` | Keyboard key to hold for recording |
| `MOUSE_BUTTON` | `x2` | Mouse button to hold for recording (X2 = forward thumb) |
| `HALLUCINATE_THRESHOLD` | `300` | Skip audio quieter than this amplitude (silence guard) |

## Privacy

All transcription runs locally on your machine. No audio or text is ever sent to any server.

## License

MIT
