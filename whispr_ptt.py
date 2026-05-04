#!/usr/bin/env python3
"""WhisperPTT — push-to-talk local speech dictation. Tray app, no console window."""

import json
import os
import sys
import threading

import numpy as np
import pyaudio
import pystray
from PIL import Image
from faster_whisper import WhisperModel
from pynput import keyboard, mouse

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEVICE = "auto"          # "cuda" for GPU, "cpu" to force CPU, "auto" to detect
COMPUTE_TYPE = "int8"    # "int8" (fast/low RAM), "float16" (GPU), "float32" (accurate)
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
HALLUCINATE_THRESHOLD = 300  # skip audio below this RMS amplitude (silence guard)

HOTKEY_OPTIONS: dict[str, keyboard.Key] = {
    "Right Ctrl":  keyboard.Key.ctrl_r,
    "Left Ctrl":   keyboard.Key.ctrl_l,
    "Right Alt":   keyboard.Key.alt_r,
    "Right Shift": keyboard.Key.shift_r,
    "Caps Lock":   keyboard.Key.caps_lock,
    "Scroll Lock": keyboard.Key.scroll_lock,
}

MOUSE_OPTIONS: dict[str, mouse.Button | None] = {
    "X2 (Forward thumb)": mouse.Button.x2,
    "X1 (Back thumb)":    mouse.Button.x1,
    "Middle button":      mouse.Button.middle,
    "Disabled":           None,
}

LANGUAGE_OPTIONS: dict[str, str | None] = {
    "English":     "en",
    "German":      "de",
    "French":      "fr",
    "Spanish":     "es",
    "Auto-detect": None,
}

DEFAULT_CONFIG: dict = {
    "mic_index":    None,
    "language":     "en",
    "hotkey":       "Right Ctrl",
    "mouse_button": "X2 (Forward thumb)",
    "enter_button": "X1 (Back thumb)",
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _asset_path(filename: str) -> str:
    base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)

def _config_path() -> str:
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "config.json")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class Config:
    def __init__(self):
        self._data: dict = dict(DEFAULT_CONFIG)
        path = _config_path()
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self._data.update(json.load(f))
            except Exception:
                pass

    def save(self):
        try:
            with open(_config_path(), "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    @property
    def mic_index(self) -> int | None:
        return self._data["mic_index"]

    @mic_index.setter
    def mic_index(self, v: int | None):
        self._data["mic_index"] = v
        self.save()

    @property
    def language(self) -> str | None:
        return self._data["language"]

    @language.setter
    def language(self, v: str | None):
        self._data["language"] = v
        self.save()

    @property
    def hotkey(self) -> str:
        return self._data.get("hotkey", DEFAULT_CONFIG["hotkey"])

    @hotkey.setter
    def hotkey(self, v: str):
        self._data["hotkey"] = v
        self.save()

    @property
    def mouse_button(self) -> str:
        return self._data.get("mouse_button", DEFAULT_CONFIG["mouse_button"])

    @mouse_button.setter
    def mouse_button(self, v: str):
        self._data["mouse_button"] = v
        self.save()

    @property
    def enter_button(self) -> str:
        return self._data.get("enter_button", DEFAULT_CONFIG["enter_button"])

    @enter_button.setter
    def enter_button(self, v: str):
        self._data["enter_button"] = v
        self.save()

# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------

def _model_name(lang: str | None) -> str:
    # Use the English-optimised model when set to English, multilingual otherwise.
    return "small.en" if lang == "en" else "small"

def _load_model(lang: str | None) -> WhisperModel:
    return WhisperModel(_model_name(lang), device=DEVICE, compute_type=COMPUTE_TYPE)

# ---------------------------------------------------------------------------
# Mic enumeration
# ---------------------------------------------------------------------------

def list_mics() -> list[tuple[int | None, str]]:
    pa = pyaudio.PyAudio()
    result: list[tuple[int | None, str]] = [(None, "System default")]
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            result.append((i, info["name"]))
    pa.terminate()
    return result

# ---------------------------------------------------------------------------
# Recorder
# ---------------------------------------------------------------------------

class PushToTalkRecorder:
    def __init__(self, model: WhisperModel, config: Config, tray: pystray.Icon):
        self.config = config
        self.tray = tray
        self._model = model
        self._model_lock = threading.Lock()
        self._rec_lock = threading.Lock()
        self.typer = keyboard.Controller()
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.frames: list[bytes] = []
        self.recording = False

    # -- Status ---------------------------------------------------------------

    def _status(self, text: str):
        self.tray.title = f"Whisper PTT — {text}"

    # -- Model hot-swap -------------------------------------------------------

    def reload_model(self, lang: str | None):
        name = _model_name(lang)
        self._status(f"Loading {name}...")
        new_model = _load_model(lang)
        with self._model_lock:
            self._model = new_model
        self._status("Ready")

    # -- Audio ----------------------------------------------------------------

    def _audio_callback(self, in_data, frame_count, time_info, status):
        self.frames.append(in_data)
        return (None, pyaudio.paContinue)

    def _start_recording(self):
        with self._rec_lock:
            if self.recording:
                return
            self.recording = True
            self.frames = []
            self.stream = self.pa.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=self.config.mic_index,
                frames_per_buffer=CHUNK_SIZE,
                stream_callback=self._audio_callback,
            )
            self._status("Recording...")

    def _stop_recording(self):
        with self._rec_lock:
            if not self.recording:
                return
            self.recording = False
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            captured = self.frames
            self.frames = []

        if not captured:
            self._status("Ready")
            return

        self._status("Transcribing...")
        threading.Thread(target=self._transcribe_and_type, args=(captured,), daemon=True).start()

    # -- Input listeners ------------------------------------------------------

    def on_press(self, key):
        if key == HOTKEY_OPTIONS.get(self.config.hotkey):
            self._start_recording()

    def on_release(self, key):
        if key == HOTKEY_OPTIONS.get(self.config.hotkey):
            self._stop_recording()

    def on_click(self, x, y, button, pressed):
        record_btn = MOUSE_OPTIONS.get(self.config.mouse_button)
        if record_btn is not None and button == record_btn:
            if pressed:
                self._start_recording()
            else:
                self._stop_recording()
            return

        enter_btn = MOUSE_OPTIONS.get(self.config.enter_button)
        if enter_btn is not None and button == enter_btn and pressed:
            self.typer.press(keyboard.Key.enter)
            self.typer.release(keyboard.Key.enter)

    # -- Transcription --------------------------------------------------------

    def _transcribe_and_type(self, frames: list[bytes]):
        audio_bytes = b"".join(frames)
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)

        if np.mean(np.abs(audio_np)) < HALLUCINATE_THRESHOLD:
            self._status("Ready")
            return

        audio_float = audio_np.astype(np.float32) / 32768.0

        with self._model_lock:
            segments, _ = self._model.transcribe(
                audio_float,
                beam_size=1,
                vad_filter=True,
                language=self.config.language,
            )
            text = "".join(seg.text for seg in segments).strip()

        if text:
            self.typer.type(text)

        self._status("Ready")

    # -- Run ------------------------------------------------------------------

    def run(self):
        self._status("Ready")
        mouse_listener = mouse.Listener(on_click=self.on_click)
        mouse_listener.start()
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()
        mouse_listener.stop()

    def cleanup(self):
        self.pa.terminate()

# ---------------------------------------------------------------------------
# Tray menu
# ---------------------------------------------------------------------------

def _radio(label: str, action, is_checked) -> pystray.MenuItem:
    return pystray.MenuItem(label, action, checked=is_checked, radio=True)

def build_menu(recorder: PushToTalkRecorder, config: Config, mics: list[tuple]) -> pystray.Menu:

    # Microphone submenu
    mic_items = []
    for idx, name in mics:
        display = "System default" if idx is None else f"[{idx}]  {name[:45]}"
        def _mic_action(icon, item, i=idx):
            config.mic_index = i
        mic_items.append(_radio(display, _mic_action, lambda item, i=idx: config.mic_index == i))

    # Language submenu
    lang_items = []
    for label, code in LANGUAGE_OPTIONS.items():
        def _lang_action(icon, item, c=code):
            if config.language != c:
                config.language = c
                threading.Thread(target=recorder.reload_model, args=(c,), daemon=True).start()
        lang_items.append(_radio(label, _lang_action, lambda item, c=code: config.language == c))

    # Hotkey submenu
    hotkey_items = []
    for label in HOTKEY_OPTIONS:
        def _hotkey_action(icon, item, lbl=label):
            config.hotkey = lbl
        hotkey_items.append(_radio(label, _hotkey_action, lambda item, lbl=label: config.hotkey == lbl))

    # Record mouse button submenu
    mouse_items = []
    for label in MOUSE_OPTIONS:
        def _mouse_action(icon, item, lbl=label):
            config.mouse_button = lbl
        mouse_items.append(_radio(label, _mouse_action, lambda item, lbl=label: config.mouse_button == lbl))

    # Enter mouse button submenu
    enter_items = []
    for label in MOUSE_OPTIONS:
        def _enter_action(icon, item, lbl=label):
            config.enter_button = lbl
        enter_items.append(_radio(label, _enter_action, lambda item, lbl=label: config.enter_button == lbl))

    return pystray.Menu(
        pystray.MenuItem("Microphone",    pystray.Menu(*mic_items)),
        pystray.MenuItem("Language",      pystray.Menu(*lang_items)),
        pystray.MenuItem("Hotkey",        pystray.Menu(*hotkey_items)),
        pystray.MenuItem("Record Button", pystray.Menu(*mouse_items)),
        pystray.MenuItem("Enter Button",  pystray.Menu(*enter_items)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda icon, item: icon.stop()),
    )

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if "--list-mics" in sys.argv:
        for idx, name in list_mics():
            print(f"[{idx}]  {name}")
        return

    config = Config()
    mics = list_mics()

    icon_image = Image.open(_asset_path("whisprPTT.png"))
    tray = pystray.Icon("WhisperPTT", icon_image, "Whisper PTT — Loading model...")

    model = _load_model(config.language)
    recorder = PushToTalkRecorder(model, config, tray)
    tray.menu = build_menu(recorder, config, mics)

    threading.Thread(target=recorder.run, daemon=True).start()

    tray.run()  # blocks until user clicks Quit
    recorder.cleanup()


if __name__ == "__main__":
    main()
