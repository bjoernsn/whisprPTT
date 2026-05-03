#!/usr/bin/env python3
"""WhisperPTT — push-to-talk local speech dictation. Hold Right Ctrl or Mouse X2 to record, release to transcribe and type."""

import os
import sys
import threading

import numpy as np
import pyaudio
import pystray
from PIL import Image
from faster_whisper import WhisperModel
from pynput import keyboard, mouse

# --- Config ---
MODEL_SIZE = "small.en"       # tiny.en, base.en, small.en, medium.en, large-v3
DEVICE = "auto"               # "cuda" for GPU, "cpu" to force CPU, "auto" to detect
COMPUTE_TYPE = "int8"         # "int8" (fast/low RAM), "float16" (GPU), "float32" (accurate)
MIC_INDEX = None              # None = system default. Run --list-mics to find your index.
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
HOTKEY = keyboard.Key.ctrl_r          # Keyboard key to hold for recording
MOUSE_BUTTON = mouse.Button.x2        # Mouse button to hold for recording (X2 = forward thumb)
ENTER_BUTTON = mouse.Button.x1        # Left-click sends Enter (handy on touchpads)
HALLUCINATE_THRESHOLD = 300           # Skip audio below this amplitude (silence guard)


def _asset_path(filename: str) -> str:
    """Resolve asset path whether running from source or as a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)


def list_mics() -> list[str]:
    pa = pyaudio.PyAudio()
    result = []
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            result.append(f"[{i}] {info['name']}")
    pa.terminate()
    return result


class PushToTalkRecorder:
    def __init__(self, model: WhisperModel, tray: pystray.Icon):
        self.model = model
        self.tray = tray
        self.typer = keyboard.Controller()
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.frames: list[bytes] = []
        self.recording = False
        self.lock = threading.Lock()

    def _status(self, text: str):
        self.tray.title = f"Whisper PTT — {text}"

    def _audio_callback(self, in_data, frame_count, time_info, status):
        self.frames.append(in_data)
        return (None, pyaudio.paContinue)

    def _start_recording(self):
        with self.lock:
            if self.recording:
                return
            self.recording = True
            self.frames = []
            self.stream = self.pa.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=MIC_INDEX,
                frames_per_buffer=CHUNK_SIZE,
                stream_callback=self._audio_callback,
            )
            self._status("Recording...")

    def _stop_recording(self):
        with self.lock:
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

    def on_press(self, key):
        if key == HOTKEY:
            self._start_recording()

    def on_release(self, key):
        if key == HOTKEY:
            self._stop_recording()

    def on_click(self, x, y, button, pressed):
        if button == MOUSE_BUTTON:
            if pressed:
                self._start_recording()
            else:
                self._stop_recording()
        elif button == ENTER_BUTTON and pressed:
            self.typer.press(keyboard.Key.enter)
            self.typer.release(keyboard.Key.enter)

    def _transcribe_and_type(self, frames: list[bytes]):
        audio_bytes = b"".join(frames)
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)

        if np.mean(np.abs(audio_np)) < HALLUCINATE_THRESHOLD:
            self._status("Ready")
            return

        audio_float = audio_np.astype(np.float32) / 32768.0
        segments, _ = self.model.transcribe(audio_float, beam_size=1, vad_filter=True, language="en")
        text = "".join(seg.text for seg in segments).strip()

        if text:
            self.typer.type(text)

        self._status("Ready")

    def run(self):
        self._status("Ready")
        mouse_listener = mouse.Listener(on_click=self.on_click)
        mouse_listener.start()
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()
        mouse_listener.stop()

    def cleanup(self):
        self.pa.terminate()


def main():
    if "--list-mics" in sys.argv:
        for m in list_mics():
            print(m)
        return

    icon_image = Image.open(_asset_path("whisprPTT.png"))

    tray = pystray.Icon(
        "WhisperPTT",
        icon_image,
        "Whisper PTT — Loading model...",
        menu=pystray.Menu(
            pystray.MenuItem("Quit", lambda icon, item: icon.stop()),
        ),
    )

    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    recorder = PushToTalkRecorder(model, tray)

    threading.Thread(target=recorder.run, daemon=True).start()

    tray.run()  # blocks until user clicks Quit
    recorder.cleanup()


if __name__ == "__main__":
    main()
