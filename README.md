# Jellyfin Marquee for Linux

A lightweight digital signage application that displays a rotating marquee of movie posters from a local Jellyfin server. Designed for Linux systems with a vertical display.

## Hardware Requirements
- Linux System (Debian/Ubuntu based recommended)
- Monitor (rotated vertically)

## Display Rotation

The application supports built-in software rotation. You can configure this by setting the `ROTATION` environment variable.

- **0**: No rotation (Landscape)
- **90**: Rotate 90 degrees clockwise (Portrait)
- **180**: Rotate 180 degrees (Inverted Landscape)
- **270**: Rotate 270 degrees clockwise (Inverted Portrait)

Set this variable in the `.env` file or export it before running the script.

## Installation

1.  **Clone the repository** or copy the files to your system.
2.  **Run the setup script**:
    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```
    *Note: This script installs `python3-pygame` and dependencies.*

3.  **Configure Jellyfin Connection**:
    Edit the `.env` file (created by setup.sh) or export the variables manually:
    ```bash
    export JELLYFIN_URL="http://192.168.1.100:8096"
    export JELLYFIN_API_KEY="your_jellyfin_api_key"
    # Optional: Rotate UI (0, 90, 180, 270). Default is 0.
    export ROTATION=90
    # Optional: Scale of poster relative to screen size (0.1 to 1.0). Default is 0.8.
    export POSTER_SCALE=0.8
    ```

## Running the Application

Run the script with Python 3:
```bash
export $(cat .env | xargs) && python3 jellyfin_marquee.py
```

### Controls
- **ESC**: Exit the application.

## Customization

### Border Overlay
You can add a custom border overlay (e.g., a frame) by placing a file named `border.png` in the same directory as the script.
- The image should be a PNG with transparency.
- It will be automatically resized to fit the screen.
- Posters are scaled to 80% of the screen size by default to fit within a border (configurable via `POSTER_SCALE`).

## Performance Tips

- **GPU Memory**: If running on low-end hardware (like a Raspberry Pi), ensure sufficient GPU memory is allocated (e.g., 128MB+).
