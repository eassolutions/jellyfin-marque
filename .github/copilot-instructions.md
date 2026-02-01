# Jellyfin Marquee - AI Coding Agent Instructions

## Project Overview
**Jellyfin Marquee** is a Python digital signage application that displays rotating movie posters from a Jellyfin media server on a vertical Linux display. It's a single-file application using Pygame for rendering with minimal dependencies.

## Architecture & Key Components

### Core Classes
- **JellyfinClient** (`jellyfin_marquee.py` lines 28-65): Handles API communication with Jellyfin server
  - Fetches latest movies via `/Items?IncludeItemTypes=Movie&SortBy=DateCreated`
  - Primary authentication via `X-Emby-Token` header
  - Image URLs constructed as `/Items/{id}/Images/Primary`
  
- **MarqueeApp** (`jellyfin_marquee.py` lines 68-end): Main display loop and rendering engine
  - Manages Pygame fullscreen display initialization
  - Handles rotation transformations for vertical displays
  - Implements scroll-and-pause marquee logic with configurable timing

### Critical Data Flow
1. `load_content()` → Fetches items from Jellyfin → Downloads poster images → Stores as rotated Pygame surfaces
2. `run()` → Continuous game loop → Scroll horizontally at `SCROLL_SPEED` → Auto-pause at poster center for 8 seconds → Resume scroll
3. Rotation logic applied at **two stages**: image surfaces rotated at load-time, and physical screen positioning recalculated per-frame

## Configuration & Deployment

### Environment Variables (all optional with defaults)
- `JELLYFIN_URL`: Server endpoint (default: `http://localhost:8096`)
- `JELLYFIN_API_KEY`: Required for API access (no default)
- `ROTATION`: Screen rotation in degrees—0, 90, 180, 270 (default: 0)
- `POSTER_SCALE`: Poster size relative to screen (0.1–1.0, default: 0.8)
- `USER_ID`: Optional user context for Jellyfin queries

### Setup & Running
- **Installation**: `./setup.sh` installs `python3-pygame`, `python3-requests`, and SDL2
- **Execution**: `export $(cat .env | xargs) && python3 jellyfin_marquee.py`
- **Exit**: Press ESC key

## Project-Specific Patterns

### Rotation Handling
Rotation is **not a display setting**—it's baked into:
- **Logical dimensions**: `logical_w/h` swap with physical `width/height` when `ROTATION in [90, 270]`
- **Image transforms**: Surfaces rotated via `pygame.transform.rotate()` at load-time
- **Coordinate conversion**: Physical display positions recalculated using rotation-specific mappings (lines 293–304)

**Why this approach**: Hardware rotation on ARM boards (Raspberry Pi) is unreliable; software rotation in Pygame is more portable.

### Marquee Scroll-and-Pause Logic
- **Stride**: Each poster occupies `stride = logical_w` pixels (full screen width)
- **Pause trigger**: When `scroll_x % stride < SCROLL_SPEED`, the app snaps the current poster to center and pauses for 8 seconds
- **Wrap-around**: Total scrollable width = `len(items) * stride`; scroll resets to 0 at loop end
- **Duplicate prevention**: `last_centered_index` prevents re-pausing on same poster

### Border Overlay
Optional custom frame image:
- File: `border.png` (must be PNG with alpha channel)
- Loaded at initialization, rotated if needed, always drawn last (on top of posters)
- Enables kiosk-style custom framing without UI modifications

## Common Developer Tasks

### Adding Jellyfin Filters
Edit `JellyfinClient.get_now_playing()` URL parameters:
- Filter by library: Add `&ParentId={library_id}`
- Change sort order: Modify `SortBy=DateCreated` (try `SortBy=CommunityRating`)
- Limit results: Adjust `&Limit=20`

### Debugging Display Issues
1. Check actual screen resolution: `pygame.display.get_surface().get_size()`
2. Verify rotation math: Print `logical_w`, `logical_h`, `margin_x`, `margin_y`
3. Test border overlay: Temporarily comment out `if self.border_surf:` block

### Tuning Performance
- **Slow scrolling on Raspberry Pi?** Reduce `FPS = 30` or increase `SCROLL_SPEED` increment
- **Image loading delays?** Add timeout handling in `load_content()` loop or cache images locally
- **GPU memory constraints**: Ensure `/boot/config.txt` allocates ≥128MB GPU RAM

## Integration Points
- **Jellyfin API**: HTTP REST API (Emby-compatible)—no websockets, polling-based
- **Pygame**: Fullscreen exclusive mode on Linux; may conflict with desktop environments
- **System**: Requires `.env` file in working directory; logs to stdout via Python logging module

## Notes for Agents
- Single-file application—changes are localized but interdependent (rotation logic spans multiple functions)
- No external build system; Python 3 + imports only
- Logging is INFO-level; increase to DEBUG for scroll/pause diagnostics
- Test rotation changes thoroughly; coordinate conversion is error-prone
