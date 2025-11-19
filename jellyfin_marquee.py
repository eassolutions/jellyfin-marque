#!/usr/bin/env python3
import os
import sys
import time
import requests
import pygame
import subprocess
import logging
from io import BytesIO

# Configuration
JELLYFIN_URL = os.environ.get('JELLYFIN_URL', 'http://localhost:8096')
JELLYFIN_API_KEY = os.environ.get('JELLYFIN_API_KEY', 'YOUR_API_KEY_HERE')
USER_ID = os.environ.get('JELLYFIN_USER_ID', '') # Optional: specific user context
ROTATION = int(os.environ.get('ROTATION', '0')) # 0, 90, 180, 270

# Display Settings
# Resolution will be detected dynamically
FPS = 30
SCROLL_SPEED = 4  # Faster scroll
GAP = 0 

BG_COLOR = (0, 0, 0)

# Input Settings
PLAY_KEY = pygame.K_SPACE
EXIT_KEY = pygame.K_ESCAPE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JellyfinClient:
    def __init__(self, base_url, api_key, user_id=None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.user_id = user_id
        self.headers = {
            'X-Emby-Token': self.api_key,
            'Content-Type': 'application/json'
        }

    def get_now_playing(self):
        """
        Fetches items that are 'Now Playing' or 'Latest'.
        Since 'Now Playing' usually refers to active sessions, we might want 'Latest' or a specific library.
        For this demo, we'll fetch 'Latest' movies to populate the marquee.
        """
        # Endpoint for latest movies. Adjust params as needed.
        # If user_id is provided, use it to get user-specific views if needed.
        # Here we just get latest movies from all libraries.
        url = f"{self.base_url}/Items?Recursive=true&IncludeItemTypes=Movie&SortBy=DateCreated&SortOrder=Descending&Limit=20&Fields=PrimaryImageAspectRatio,RemoteTrailers"
        if self.user_id:
            url += f"&UserId={self.user_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('Items', [])
        except Exception as e:
            logger.error(f"Error fetching data from Jellyfin: {e}")
            return []

    def get_image_url(self, item_id):
        return f"{self.base_url}/Items/{item_id}/Images/Primary"

    def get_video_stream_url(self, item_id):
        # Construct a stream URL. 
        # Note: This is a direct stream URL. Transcoding might be needed depending on the player and file support.
        # Using Static=true to try and get the original file if possible, or let Jellyfin decide.
        return f"{self.base_url}/Videos/{item_id}/stream?static=true&api_key={self.api_key}"

class MarqueeApp:
    def __init__(self):
        pygame.init()
        # Initialize display with dynamic resolution
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.width, self.height = pygame.display.get_surface().get_size()
        logger.info(f"Display initialized at {self.width}x{self.height} with Rotation: {ROTATION}")
        
        # Determine logical dimensions based on rotation
        if ROTATION in [90, 270]:
            self.logical_w = self.height
            self.logical_h = self.width
        else:
            self.logical_w = self.width
            self.logical_h = self.height

        # Set poster dimensions to 90% of logical screen
        self.poster_w = int(self.logical_w * 0.9)
        self.poster_h = int(self.logical_h * 0.9)
        
        # Calculate margins to center the poster
        self.margin_x = (self.logical_w - self.poster_w) // 2
        self.margin_y = (self.logical_h - self.poster_h) // 2
        
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        
        # Load Border Image
        self.border_surf = None
        if os.path.exists('border.png'):
            try:
                border = pygame.image.load('border.png').convert_alpha()
                # Resize border to fit physical screen
                self.border_surf = pygame.transform.scale(border, (self.width, self.height))
                logger.info("Loaded border.png")
            except Exception as e:
                logger.error(f"Failed to load border.png: {e}")
        
        self.client = JellyfinClient(JELLYFIN_URL, JELLYFIN_API_KEY, USER_ID)
        self.items = []
        self.images = [] # List of (image_surface, item_data)
        self.scroll_x = 0
        self.running = True
        self.paused = False
        self.pause_start_time = 0
        self.last_centered_index = -1 # To prevent re-pausing on the same poster immediately

    def load_content(self):
        logger.info("Loading content from Jellyfin...")
        items = self.client.get_now_playing()
        self.items = items
        self.images = []
        
        for item in items:
            try:
                img_url = self.client.get_image_url(item['Id'])
                # Fetch image data
                r = requests.get(img_url, timeout=5)
                if r.status_code == 200:
                    img_data = BytesIO(r.content)
                    surf = pygame.image.load(img_data).convert()
                    # Resize to fit logical poster dimensions
                    surf = pygame.transform.scale(surf, (self.poster_w, self.poster_h))
                    # Rotate if needed
                    if ROTATION != 0:
                        surf = pygame.transform.rotate(surf, ROTATION)
                    self.images.append({'surface': surf, 'data': item})
            except Exception as e:
                logger.error(f"Failed to load image for item {item.get('Name')}: {e}")

        if not self.images:
            logger.warning("No images loaded. Creating placeholders.")
            # Create a placeholder if no images found
            surf = pygame.Surface((self.poster_w, self.poster_h))
            surf.fill((50, 50, 50))
            if ROTATION != 0:
                surf = pygame.transform.rotate(surf, ROTATION)
            self.images.append({'surface': surf, 'data': {'Name': 'No Content', 'Id': None}})

    def play_video(self, item):
        # Check for trailers first
        video_url = None
        remote_trailers = item.get('RemoteTrailers', [])
        if remote_trailers:
            # Use the first trailer
            video_url = remote_trailers[0].get('Url')
            logger.info(f"Found trailer URL: {video_url}")
        
        if not video_url and item.get('Id'):
             # Fallback to movie if no trailer? User said "Instead of trying to play the movie... play the trailer"
             # But if no trailer exists, maybe we shouldn't play anything or fallback?
             # I'll fallback to movie for robustness, or maybe just log.
             # "Instead of" implies replacement. I will try trailer, if not found, log warning and maybe skip.
             logger.warning(f"No trailer found for {item.get('Name')}")
             return

        logger.info(f"Playing video: {item.get('Name')} from {video_url}")
        
        # Stop Pygame loop temporarily
        pygame.display.iconify() 
        
        try:
            # mpv handles youtube URLs natively if yt-dlp is installed
            cmd = ['mpv', '--fs', '--ontop', video_url]
            if ROTATION != 0:
                # mpv rotation is clockwise 0-360
                # We pass the rotation directly
                cmd.append(f'--video-rotate={ROTATION}')
            subprocess.run(cmd, check=True)
        except Exception as e:
            logger.error(f"Error playing video: {e}")
        
        # Restore display
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)

    def run(self):
        self.load_content()
        
        # Calculate total width of the marquee
        # Since posters are 90% width, we treat the "slot" size as the full logical width?
        # Or do we just scroll them with spacing?
        # If we want them to pause in the center, it's easiest if we treat each item as taking up the full screen width (logical_w),
        # but the image itself is only 90% of that, centered.
        # So the "stride" is self.logical_w.
        
        stride = self.logical_w
        total_width = len(self.images) * stride
        
        while self.running:
            dt = self.clock.tick(FPS)
            current_time = time.time()
            
            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == EXIT_KEY:
                        self.running = False
                    elif event.key == PLAY_KEY:
                        # Play the one roughly in the center.
                        offset = (self.scroll_x + self.logical_w // 2) % total_width
                        idx = int(offset // stride)
                        if idx < len(self.images):
                            self.play_video(self.images[idx]['data'])

            # Update
            if self.paused:
                if current_time - self.pause_start_time >= 5:
                    self.paused = False
                    self.last_centered_index = -1 # Allow pausing again on next one
            else:
                self.scroll_x += SCROLL_SPEED
                if self.scroll_x >= total_width:
                    self.scroll_x = 0
                
                # Check for pause condition
                # We want to pause when a poster is centered.
                # A poster i is centered when its "slot" is centered.
                # Slot i starts at i * stride.
                # It is centered when i * stride - scroll_x = 0.
                # (Since the slot is full screen width, aligning left edge aligns center).
                
                # We check if scroll_x is close to a multiple of stride
                # We need to handle wrap around logic for the check too, but scroll_x resets.
                
                # Find closest index
                # We want to snap if abs(scroll_x - i*stride) < speed
                
                # effective_scroll = self.scroll_x
                # But we only care about the one currently visible?
                # Actually, we just need to check if scroll_x % stride is close to 0.
                
                remainder = self.scroll_x % stride
                # If remainder is small (just started a new slot) or large (about to end)
                # We want to stop exactly at 0.
                
                # Since we increment by SPEED, we might skip 0.
                # If remainder < SPEED, we are close to the start of a slot.
                # But we want to pause when the poster is CENTERED.
                # Since stride = logical_w, and poster is centered in stride,
                # The poster is centered when the slot is aligned with the screen (offset 0).
                
                if remainder < SCROLL_SPEED and not self.paused:
                    # Which index is this?
                    idx = int(self.scroll_x // stride)
                    if idx != self.last_centered_index:
                        # Snap to exact position
                        self.scroll_x = idx * stride
                        self.paused = True
                        self.pause_start_time = current_time
                        self.last_centered_index = idx

            # Draw
            self.screen.fill(BG_COLOR)
            
            for i in range(len(self.images)):
                # Calculate logical position
                # The slot starts at i * stride
                slot_x = (i * stride) - self.scroll_x
                
                # Wrap around logic (Logical)
                while slot_x < -stride:
                    slot_x += total_width
                while slot_x > total_width - stride: # Wait, if it's too far right?
                     # Standard wrap: if it's off screen to left, move to end.
                     # If we use modulo arithmetic for scroll_x, we handle the main loop.
                     # But for drawing we need to handle the "seam".
                     pass
                
                # Better wrap logic for drawing:
                # We iterate through all, but only draw if visible.
                # We also need to draw the "wrapped" version if we are at the seam.
                
                # Let's use the standard loop with wrap check
                # Position of slot i
                base_x = i * stride
                dist = base_x - self.scroll_x
                
                # Handle wrapping
                # If dist is very negative (scrolled past), add total_width
                while dist < -stride:
                    dist += total_width
                while dist > self.logical_w:
                    dist -= total_width
                
                # Now dist is the screen x position of the left edge of the slot
                # Only draw if visible
                if -stride < dist < self.logical_w:
                    # Calculate where to put the image within the slot
                    # Image is centered in the slot
                    # Slot width = stride = logical_w
                    # Image width = poster_w
                    # Image x relative to slot = margin_x
                    # Image y relative to slot = margin_y (since slot height = logical_h)
                    
                    img_x = dist + self.margin_x
                    img_y = self.margin_y
                    
                    # Physical conversion
                    dest_pos = (0, 0)
                    
                    # We need to rotate the final position logic
                    # logical (img_x, img_y) -> physical
                    
                    if ROTATION == 0:
                        dest_pos = (img_x, img_y)
                    elif ROTATION == 90:
                        # 90 CCW: (x, y) -> (y, height - x - w)
                        # Wait, let's verify 90 CCW mapping again.
                        # Input x is Right, y is Down.
                        # Output x is Up, y is Left (relative to original).
                        # Physical: x is Right, y is Down.
                        # 90 CCW Image: Top points Left.
                        # We want "Logical X" (Scroll direction) to map to "Physical Y" (Up/Down).
                        # If we scroll "Right" logically, we scroll "Up" physically?
                        # Let's assume standard mapping:
                        # Logical (0,0) is Top-Left.
                        # 90 Rotated (0,0) is Bottom-Left physically?
                        # Let's stick to the previous working logic for 90:
                        # dest_pos = (0, self.height - logical_x - self.poster_h)
                        # Here logical_x is img_x.
                        # And width is poster_w (which is logical width of image).
                        # Height is poster_h (logical height).
                        
                        # But wait, we rotated the SURFACE too.
                        # If surface is rotated 90, its width/height swapped.
                        # surf.get_width() is now poster_h.
                        # surf.get_height() is now poster_w.
                        
                        dest_pos = (img_y, self.height - img_x - self.images[i]['surface'].get_height())
                        
                    elif ROTATION == 180:
                        dest_pos = (self.width - img_x - self.images[i]['surface'].get_width(), self.height - img_y - self.images[i]['surface'].get_height())
                    elif ROTATION == 270:
                        # 270 CCW
                        dest_pos = (self.width - img_y - self.images[i]['surface'].get_width(), img_x)
                        
                    self.screen.blit(self.images[i]['surface'], dest_pos)

            # Draw Border Overlay
            if self.border_surf:
                self.screen.blit(self.border_surf, (0, 0))
            
            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    app = MarqueeApp()
    app.run()
