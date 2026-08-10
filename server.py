"""
Phone-to-Laptop Camera Streamer — Step 1

WHAT THIS DOES:
- Runs a small web server on your LAPTOP.
- Your PHONE opens a webpage (served by this script) that turns on the
  phone's camera and sends video frames to the laptop, one picture at a time.
- Your LAPTOP opens a different webpage (also served by this script) that
  shows those pictures live, like a video feed.

Both devices just need to be on the SAME WiFi network. No app installs,
no rooting, no rebooting.
"""

from flask import Flask, request, Response, render_template_string
import threading

app = Flask(__name__)

# This holds the most recent picture (frame) sent by the phone.
# "lock" makes sure we don't read/write it at the exact same time from
# two different requests (that can happen with web servers).
latest_frame = None
lock = threading.Lock()

# ---------- Page shown on the PHONE ----------
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

    // Ask the phone browser for camera access.
    // facingMode 'environment' = back camera (better for gestures later).
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      .then(stream => {
        video.srcObject = stream;
        status.innerText = 'Streaming to laptop...';
        setInterval(sendFrame, 150); // send a picture ~6-7 times per second
      })
      .catch(err => {
        status.innerText = 'Camera error: ' + err.message;
      });

    function sendFrame() {
      if (video.videoWidth === 0) return; // camera not ready yet
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

# ---------- Page shown on the LAPTOP ----------
VIEW_PAGE = """
<!DOCTYPE html>
<html>
<head><title>Laptop Viewer</title></head>
<body style="margin:0;background:#111;text-align:center;">
  <h2 style="color:white;font-family:sans-serif;">Live Phone Feed</h2>
  <img id="feed" style="max-width:90%;border:2px solid #444;border-radius:8px;">
  <script>
    const img = document.getElementById('feed');
    // Keep asking the server for the newest picture, ~6-7 times a second.
    setInterval(() => { img.src = '/frame.jpg?t=' + Date.now(); }, 150);
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return '''
    <h2>Phone-to-Laptop Camera Streamer</h2>
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
    """The phone sends a picture here. We just store it."""
    global latest_frame
    with lock:
        latest_frame = request.data
    return '', 204

@app.route('/frame.jpg')
def frame():
    """The laptop viewer page asks for the newest picture here."""
    with lock:
        if latest_frame is None:
            return '', 404
        data = latest_frame
    return Response(data, mimetype='image/jpeg')

if __name__ == '__main__':
    # ssl_context='adhoc' turns on HTTPS with a self-signed certificate.
    # Phones require a secure (https) connection to allow camera access,
    # so this step is required, not optional.
    app.run(host='0.0.0.0', port=5000, ssl_context='adhoc')
