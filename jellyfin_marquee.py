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

# Display Settings
# Resolution will be detected dynamically
FPS = 30
SCROLL_SPEED = 2  # Pixels per frame
GAP = 0 # No gap if we want full screen posters, or maybe small gap? User said "poster width and height to take up the entire screen". 
# If they take up the entire screen, there is only one visible at a time? Or is it a scrolling list of fullscreen images?
# "Rotating Marquee" usually implies multiple. But "poster width and height to take up the entire screen" implies one.
# If they are fullscreen, scrolling them might look like a slideshow or a filmstrip.
# I will assume "take up the entire screen" means the height fills the screen, and width is proportional, OR they literally mean 1080x1920 posters.
# Given "Rotating Marquee", I'll assume they mean the posters should be scaled to fit the screen HEIGHT, and width is proportional, 
# OR if they want "entire screen" maybe they mean the poster fills the whole view?
# "Set the poster width and height to take up the entire screen (therefor the same as the screen width and height variables)."
# This implies 1 poster visible at a time, or they are just huge.
# If they are huge, scrolling them is fine.
# I will set POSTER_WIDTH/HEIGHT variables dynamically in the class.

FONT_SIZE = 120 # Larger font for "pop"
BG_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 215, 0) # Gold

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
        logger.info(f"Display initialized at {self.width}x{self.height}")
        
        # Set poster dimensions to match screen
        self.poster_w = self.width
        self.poster_h = self.height
        
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, FONT_SIZE, bold=True)
        
        self.client = JellyfinClient(JELLYFIN_URL, JELLYFIN_API_KEY, USER_ID)
        self.items = []
        self.images = [] # List of (image_surface, item_data)
        self.scroll_x = 0
        self.running = True

    def draw_text_with_shadow(self, text, center_pos):
        # Shadow
        shadow_surf = self.font.render(text, True, (0, 0, 0))
        shadow_rect = shadow_surf.get_rect(center=(center_pos[0] + 4, center_pos[1] + 4))
        self.screen.blit(shadow_surf, shadow_rect)
        
        # Main text
        text_surf = self.font.render(text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=center_pos)
        self.screen.blit(text_surf, text_rect)

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
                    # Resize to fit poster dimensions (Fullscreen)
                    surf = pygame.transform.scale(surf, (self.poster_w, self.poster_h))
                    self.images.append({'surface': surf, 'data': item})
            except Exception as e:
                logger.error(f"Failed to load image for item {item.get('Name')}: {e}")

        if not self.images:
            logger.warning("No images loaded. Creating placeholders.")
            # Create a placeholder if no images found
            surf = pygame.Surface((self.poster_w, self.poster_h))
            surf.fill((50, 50, 50))
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
            subprocess.run(cmd, check=True)
        except Exception as e:
            logger.error(f"Error playing video: {e}")
        
        # Restore display
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)

    def run(self):
        self.load_content()
        
        # Calculate total width of the marquee
        # Since posters are full screen width, total width is count * width
        total_width = len(self.images) * self.poster_w
        
        while self.running:
            dt = self.clock.tick(FPS)
            
            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == EXIT_KEY:
                        self.running = False
                    elif event.key == PLAY_KEY:
                        # Play the one roughly in the center.
                        offset = (self.scroll_x + self.width // 2) % total_width
                        idx = int(offset // self.poster_w)
                        if idx < len(self.images):
                            self.play_video(self.images[idx]['data'])

            # Update
            self.scroll_x += SCROLL_SPEED
            if self.scroll_x >= total_width:
                self.scroll_x = 0
            
            # Draw
            self.screen.fill(BG_COLOR)
            
            for i in range(len(self.images)):
                x_pos = (i * self.poster_w) - self.scroll_x
                
                # Wrap around logic
                while x_pos < -self.poster_w:
                    x_pos += total_width
                while x_pos > self.width:
                    x_pos -= total_width
                
                # Only draw if visible
                if -self.poster_w < x_pos < self.width:
                    self.screen.blit(self.images[i]['surface'], (x_pos, 0))

            # Draw Overlay Text
            # Center of screen
            self.draw_text_with_shadow("Now Playing", (self.width // 2, self.height // 2))
            
            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    app = MarqueeApp()
    app.run()
