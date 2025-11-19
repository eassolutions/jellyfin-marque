# Jellyfin Marquee for Raspberry Pi Zero W

A lightweight digital signage application that displays a rotating marquee of movies from a local Jellyfin server and plays them on demand. Designed for the Raspberry Pi Zero W with a vertical 1080p display.

## Hardware Requirements
- Raspberry Pi Zero W
- MicroSD Card (8GB+) with Raspberry Pi OS Lite (Legacy or Bullseye recommended for best SDL support, though Bookworm works with Wayland/X11 or direct DRM if configured).
- 1080p Monitor (rotated vertically)

## Configuration for Vertical Display

Ensure your Raspberry Pi is configured for a vertical display.
In `/boot/config.txt` (or `/boot/firmware/config.txt` on newer OS):

```ini
# Rotate display 90 degrees (if supported by firmware/driver)
display_rotate=1 
# OR use xrandr if running X11, or kernel command line arguments.
```

If the display is natively portrait (e.g. phone screen via HDMI), no rotation is needed. The application will **automatically detect the screen resolution** and scale the posters to fill the screen.

## Installation

1.  **Clone the repository** or copy the files to your Pi.
2.  **Run the setup script**:
    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```
    *Note: This script installs `python3-pygame`, `mpv`, and `yt-dlp` (for YouTube trailers).*

3.  **Configure Jellyfin Connection**:
    Edit the `.env` file (created by setup.sh) or export the variables manually:
    ```bash
    export JELLYFIN_URL="http://192.168.1.100:8096"
    export JELLYFIN_API_KEY="your_jellyfin_api_key"
    ```

## Running the Application

Run the script with Python 3:
```bash
python3 jellyfin_marquee.py
```

### Controls
- **SPACE**: Play the **trailer** for the poster currently in the center (requires YouTube URL in Jellyfin metadata).
- **ESC**: Exit the application.

## Performance Tips for Pi Zero W

- **GPU Memory**: Increase GPU memory to at least 128MB or 256MB via `sudo raspi-config`.
- **Resolution**: If 1080p is too slow, lower the resolution in `config.txt` to 720p (720x1280) for smoother animations.
- **Trailers**: This app uses `mpv` + `yt-dlp` to stream trailers. Ensure you have a good internet connection.
- **Video Player**: The script uses `mpv`. If `mpv` struggles, try installing `vlc` and changing the subprocess command in the script to `cvlc`.
