#!/usr/bin/env python3
"""Push-to-talk dictation using faster_whisper. Hold Right Ctrl or Mouse X2 (forward thumb) to record, release to transcribe and type."""

import threading
import numpy as np
import pyaudio
from pynput import keyboard, mouse

from faster_whisper import WhisperModel

# --- Config ---
MODEL_SIZE = "small.en"       # Options: tiny.en, base.en, small.en, medium.en, large-v3
DEVICE = "auto"               # "cuda" for GPU, "cpu" for CPU, "auto" to detect
COMPUTE_TYPE = "int8"         # "int8" (fast, low RAM), "float16" (GPU), "float32" (accurate)
MIC_INDEX = None              # Set to an int to pin a specific mic (run list_mics() to find yours)
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
HOTKEY = keyboard.Key.ctrl_r          # Hold this key to record
MOUSE_BUTTON = mouse.Button.x2        # Or hold this mouse button (X2 = forward thumb)
ENTER_BUTTON = mouse.Button.x1        # Left click sends Enter (useful on touchpads)
HALLUCINATE_THRESHOLD = 300           # Skip audio quieter than this amplitude


def list_mics():
    """Print available microphone devices and their indices."""
    pa = pyaudio.PyAudio()
    print("Available microphones:")
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            print(f"  [{i}] {info['name']}")
    pa.terminate()


class PushToTalkRecorder:
    def __init__(self, model: WhisperModel):
        self.model = model
        self.typer = keyboard.Controller()
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.frames: list[bytes] = []
        self.recording = False
        self.lock = threading.Lock()

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
            print("Recording...", flush=True)

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
            print("(too short, skipped)", flush=True)
            return

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

        amplitude = np.mean(np.abs(audio_np))
        if amplitude < HALLUCINATE_THRESHOLD:
            print("(too quiet, skipped)", flush=True)
            return

        audio_float = audio_np.astype(np.float32) / 32768.0
        print("Transcribing...", flush=True)

        segments, _ = self.model.transcribe(audio_float, beam_size=1, vad_filter=True, language="en")
        text = "".join(seg.text for seg in segments).strip()

        if text:
            print(f'Typed: "{text}"', flush=True)
            self.typer.type(text)
        else:
            print("(no speech detected)", flush=True)

    def run(self):
        mouse_listener = mouse.Listener(on_click=self.on_click)
        mouse_listener.start()
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()
        mouse_listener.stop()

    def cleanup(self):
        self.pa.terminate()


if __name__ == "__main__":
    import sys
    if "--list-mics" in sys.argv:
        list_mics()
        sys.exit(0)

    print(f"Loading model {MODEL_SIZE}...")
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    print("Model loaded. Hold Right Ctrl or Mouse X2 (forward thumb) to record, Ctrl+C to exit.", flush=True)

    recorder = PushToTalkRecorder(model)
    try:
        recorder.run()
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        recorder.cleanup()
