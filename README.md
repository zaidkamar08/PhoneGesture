# Step 1: Phone Camera → Laptop (Live Feed)

This gets your phone's camera showing up live on your laptop screen, over
your home WiFi. No app install on the phone, no rooting, no rebooting.

## What you need
- Your laptop, with **Python** installed (if you don't have it, download
  from python.org — during install, tick "Add Python to PATH").
- Your phone and laptop connected to the **same WiFi network**.

## Setup (do this once)

1. Open a terminal / command prompt on your laptop, and go into this folder:
   ```
   cd path/to/phone-controller
   ```
2. Install the two small libraries this script needs:
   ```
   pip install -r requirements.txt
   ```
   - **Flask** = a tiny library that lets a Python script act as a web server
     (a program that can serve webpages and receive data, like a mini
     website host).
   - **pyopenssl** = lets that server use HTTPS (a secure connection).
     Phones block camera access on non-secure ("http") pages, so this is
     required.

     ->or else we can install manually using 'pip install flask' and 'pip install pyopenssl"

## Running it

1. Find your laptop's local IP address (this is the address your phone
   will use to reach your laptop — like a phone number, but for devices
   on a network):
   - **Windows**: open Command Prompt, type `ipconfig`, look for "IPv4
     Address" (something like `192.168.1.23`).
   - **Mac/Linux**: open Terminal, type `ifconfig` or `ip addr`, look for
     something similar under your WiFi adapter.

2. Start the server:
   ```
   python server.py
   ```
   Leave this terminal window open — closing it stops the server.

3. **On your laptop**, open a browser and go to:
   ```
   https://localhost:5000/view
   ```
   You'll likely see a warning like "Your connection is not private" —
   this is expected (it's because the certificate is self-signed, made by
   the script itself, not a trusted company). Click **Advanced** → **Proceed**.
   You should see a blank "Live Phone Feed" page for now — that's normal,
   the phone hasn't connected yet.

4. **On your phone**, open a browser and go to:
   ```
   https://<your-laptop-ip>:5000/phone
   ```
   Example: `https://192.168.1.23:5000/phone`

   You'll get the same "not private" warning — tap **Advanced** → **Proceed**
   (wording differs slightly by phone browser, e.g "visit this site" on Chrome).
   Then it will ask for **camera permission** — allow it.

5. Go back to your laptop's browser tab — you should now see your phone's
   camera feed updating live.

## If it doesn't work
- **Frame doesn't update**: make sure both devices are truly on the same
  WiFi network (not phone on mobile data).
- **Camera permission blocked**: check your phone browser's site settings
  and allow camera access for that page.
- **Can't reach the page from phone at all**: your laptop's firewall might
  be blocking incoming connections on port 5000 — you may need to allow it
  once (Windows will usually pop up an "Allow access?" prompt the first
  time you run the script — click Allow).

## What's next
Once this is working reliably, step 2 adds **gesture recognition** —
the laptop will look at each incoming picture and detect hand movements
(wave, swipe, fist), then trigger an action like skipping a song or
muting the volume.
