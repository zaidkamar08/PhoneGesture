"""
Phone-to-Laptop Gesture Controller — Step 2 (updated for current mediapipe)

Builds on step 1. The laptop looks at each picture coming from the phone,
finds your hand, and recognizes two simple gestures:

    OPEN PALM   -> Play/Pause media
    CLOSED FIST -> Mute/unmute volume

NOTE: mediapipe recently removed its old "solutions" API (the version most
tutorials online still show). This script uses their current replacement,
the "Tasks" API, which needs one extra one-time step: downloading a small
hand-detection model file. The script does this automatically the first
time it runs.
"""

from flask import Flask, request, Response, render_template_string, jsonify
import threading
import time
import os
import urllib.request
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
import pyautogui

app = Flask(__name__)

latest_frame = None
lock = threading.Lock()

# ---------- Hand detection model setup ----------
MODEL_PATH = "hand_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

if not os.path.exists(MODEL_PATH):
    print("Downloading hand detection model (one-time, ~8 MB)...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Model downloaded.")

detector = HandLandmarker.create_from_options(
    HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=0.6,
    )
)

last_gesture = None
last_action_time = 0
COOLDOWN_SECONDS = 2 # don't repeat the same action faster than this
last_status = "No hand detected"


def classify_gesture(landmarks):
    """
    landmarks: 21 (x, y) points, each 0-1 (fraction of image width/height).
    Returns 'open_palm', 'fist', or None (gesture not recognized).

    For each of the 4 main fingers, we check whether the fingertip is
    ABOVE its middle knuckle (smaller y = higher up in the image = finger
    extended) or BELOW it (finger curled down = fist).
    """
    tips = [8, 12, 16, 20]   # index, middle, ring, pinky fingertip
    pips = [6, 10, 14, 18]   # the knuckle joint just below each fingertip

    fingers_up = 0
    for tip, pip in zip(tips, pips):
        if landmarks[tip][1] < landmarks[pip][1]:
            fingers_up += 1

    if fingers_up >= 3:
        return "open_palm"
    if fingers_up == 0:
        return "fist"
    return None  # in-between position, ignore to avoid false triggers


def trigger_action(gesture):
    global last_status
    if gesture == "open_palm":
        pyautogui.press("playpause")
        last_status = "Open palm detected -> Play/Pause"
    elif gesture == "fist":
        pyautogui.press("volumemute")
        last_status = "Fist detected -> Mute toggled"


def process_frame(jpeg_bytes):
    """Runs on every picture the phone sends. Detects hand + gesture,
    and triggers a laptop action if a new gesture is confirmed."""
    global last_gesture, last_action_time, last_status

    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = detector.detect(mp_image)

    if not result.hand_landmarks:
        last_status = "No hand detected"
        last_gesture = None
        return

    hand = result.hand_landmarks[0]  # first detected hand
    points = [(lm.x, lm.y) for lm in hand]
    gesture = classify_gesture(points)

    if gesture is None:
        last_status = "Hand detected, gesture unclear"
        return

    now = time.time()
    if gesture != last_gesture and (now - last_action_time) > COOLDOWN_SECONDS:
        trigger_action(gesture)
        last_action_time = now
    last_gesture = gesture


# ---------- Page shown on the PHONE (same as step 1) ----------
PHONE_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <title>Phone Camera</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;background:#000;">
  <video id="video" autoplay playsinline muted style="width:100%;"></video>
  <canvas id="canvas" style="display:none;"></canvas>
  <div id="status" style="color:#0f0;text-align:center;padding:12px;
       font-family:sans-serif;font-size:16px;">Starting camera...</div>
  <script>
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const status = document.getElementById('status');
    const ctx = canvas.getContext('2d');

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      .then(stream => {
        video.srcObject = stream;
        status.innerText = 'Streaming to laptop...';
        setInterval(sendFrame, 150);
      })
      .catch(err => { status.innerText = 'Camera error: ' + err.message; });

    function sendFrame() {
      if (video.videoWidth === 0) return;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);
      canvas.toBlob(blob => {
        fetch('/upload', { method: 'POST', body: blob })
          .catch(e => { status.innerText = 'Send failed: ' + e.message; });
      }, 'image/jpeg', 0.6);
    }
  </script>
</body>
</html>
"""

# ---------- Page shown on the LAPTOP (shows gesture status) ----------
VIEW_PAGE = """
<!DOCTYPE html>
<html>
<head><title>Laptop Viewer</title></head>
<body style="margin:0;background:#111;text-align:center;">
  <h2 style="color:white;font-family:sans-serif;">Live Phone Feed</h2>
  <img id="feed" style="max-width:90%;border:2px solid #444;border-radius:8px;">
  <p id="status" style="color:#0f0;font-family:sans-serif;font-size:18px;">Waiting...</p>
  <script>
    const img = document.getElementById('feed');
    const status = document.getElementById('status');
    setInterval(() => { img.src = '/frame.jpg?t=' + Date.now(); }, 150);
    setInterval(() => {
      fetch('/status').then(r => r.json()).then(d => { status.innerText = d.status; });
    }, 300);
  </script>
</body>
</html>
"""


@app.route('/')
def index():
    return '''
    <h2>Phone-to-Laptop Gesture Controller</h2>
    <p>Open <a href="/phone">/phone</a> on your PHONE.</p>
    <p>Open <a href="/view">/view</a> on your LAPTOP.</p>
    '''


@app.route('/phone')
def phone():
    return render_template_string(PHONE_PAGE)


@app.route('/view')
def view():
    return render_template_string(VIEW_PAGE)


@app.route('/upload', methods=['POST'])
def upload():
    global latest_frame
    data = request.data
    with lock:
        latest_frame = data
    process_frame(data)
    return '', 204


@app.route('/frame.jpg')
def frame():
    with lock:
        if latest_frame is None:
            return '', 404
        data = latest_frame
    return Response(data, mimetype='image/jpeg')


@app.route('/status')
def status():
    return jsonify({"status": last_status})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, ssl_context='adhoc', threaded=True)
