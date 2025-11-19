# Jellyfin Marquee for Raspberry Pi

A lightweight digital signage application that displays a rotating marquee of movies from a local Jellyfin server and plays them on demand. Designed for the Raspberry Pi with a vertical display.

## Hardware Requirements
- Raspberry Pi
- MicroSD Card (8GB+) with Raspberry Pi OS Lite (Legacy or Bullseye recommended for best SDL support, though Bookworm works with Wayland/X11 or direct DRM if configured).
- Monitor (rotated vertically)

## Configuration for Vertical Display

### Method 1: Hardware/OS Rotation (Recommended for Performance)
Ensure your Raspberry Pi is configured for a vertical display.
In `/boot/config.txt` (or `/boot/firmware/config.txt` on newer OS):

```ini
# Rotate display 90 degrees (if supported by firmware/driver)
display_rotate=1 
# OR use xrandr if running X11, or kernel command line arguments.
```

### Method 2: Software Rotation
If `display_rotate` does not work or you prefer a software solution, you can use the built-in rotation feature.
Set the `ROTATION` environment variable before running the script.

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
    # Optional: Rotate UI (0, 90, 180, 270). Default is 0.
    export ROTATION=90
    ```

## Running the Application

Run the script with Python 3:
```bash
python3 jellyfin_marquee.py
```

### Controls
- **SPACE**: Play the **trailer** for the poster currently in the center (requires YouTube URL in Jellyfin metadata).
- **ESC**: Exit the application.

## Customization

### Border Overlay
You can add a custom border overlay (e.g., a frame) by placing a file named `border.png` in the same directory as the script.
- The image should be a PNG with transparency.
- It will be automatically resized to fit the screen.
- Posters are scaled to 90% of the screen size to fit within a border.

## Performance Tips for Pi

- **GPU Memory**: Increase GPU memory to at least 128MB or 256MB via `sudo raspi-config`.
- **Trailers**: This app uses `mpv` + `yt-dlp` to stream trailers. Ensure you have a good internet connection.
- **Video Player**: The script uses `mpv`. If `mpv` struggles, try installing `vlc` and changing the subprocess command in the script to `cvlc`.
