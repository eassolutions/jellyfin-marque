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
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 1920
FPS = 30
SCROLL_SPEED = 2  # Pixels per frame
POSTER_WIDTH = 300
POSTER_HEIGHT = 450
GAP = 20
FONT_SIZE = 64
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
        url = f"{self.base_url}/Items?Recursive=true&IncludeItemTypes=Movie&SortBy=DateCreated&SortOrder=Descending&Limit=20&Fields=PrimaryImageAspectRatio"
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
        # Initialize display
        # For Pi Framebuffer, we might need specific flags.
        # pygame.FULLSCREEN is standard.
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, FONT_SIZE)
        
        self.client = JellyfinClient(JELLYFIN_URL, JELLYFIN_API_KEY, USER_ID)
        self.items = []
        self.images = [] # List of (image_surface, item_data)
        self.scroll_x = 0
        self.running = True
        self.selected_index = 0 # For simulation of selection if we want to highlight

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
                    # Resize to fit poster dimensions
                    surf = pygame.transform.scale(surf, (POSTER_WIDTH, POSTER_HEIGHT))
                    self.images.append({'surface': surf, 'data': item})
            except Exception as e:
                logger.error(f"Failed to load image for item {item.get('Name')}: {e}")

        if not self.images:
            logger.warning("No images loaded. Creating placeholders.")
            # Create a placeholder if no images found
            surf = pygame.Surface((POSTER_WIDTH, POSTER_HEIGHT))
            surf.fill((50, 50, 50))
            self.images.append({'surface': surf, 'data': {'Name': 'No Content', 'Id': None}})

    def play_video(self, item):
        if not item.get('Id'):
            return
            
        video_url = self.client.get_video_stream_url(item['Id'])
        logger.info(f"Playing video: {item['Name']} from {video_url}")
        
        # Stop Pygame loop temporarily
        pygame.display.iconify() # Minimize if possible, or just pause drawing
        
        # Launch mpv
        # --fs = fullscreen
        # --ontop = keep on top
        try:
            cmd = ['mpv', '--fs', '--ontop', video_url]
            # specific args for Pi can be added here, e.g. --vo=gpu --hwdec=mmal
            subprocess.run(cmd, check=True)
        except Exception as e:
            logger.error(f"Error playing video: {e}")
        
        # Restore display
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)

    def run(self):
        self.load_content()
        
        # Calculate total width of the marquee
        total_width = len(self.images) * (POSTER_WIDTH + GAP)
        
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
                        # Determine which poster is "center" or selected
                        # For simplicity, let's play the one currently closest to center
                        center_x = self.scroll_x + (SCREEN_WIDTH / 2)
                        # Map scroll position to index
                        # This is a bit rough for a continuous loop, but works for simple selection
                        # Let's just play the first one for the demo or random?
                        # Requirement: "When a poster is selected (simulated by a simple keypress)"
                        # Let's pick the one in the middle of the screen.
                        
                        # effective_scroll = self.scroll_x % total_width
                        # index = int((effective_scroll + SCREEN_WIDTH/2) / (POSTER_WIDTH + GAP)) % len(self.images)
                        
                        # Actually, let's just play the one that is visually in the middle
                        # We need to find which image is at screen center
                        
                        # Visual offset of first image is -self.scroll_x
                        # Center of screen is SCREEN_WIDTH / 2
                        # Image i center is: i * (W+G) + W/2 - scroll_x
                        # We want i where |(i*(W+G) + W/2 - scroll_x) - SCREEN_WIDTH/2| is minimized
                        
                        best_idx = 0
                        min_dist = float('inf')
                        
                        for i in range(len(self.images)):
                            # We need to account for wrapping if we implement infinite scroll
                            # For now, let's assume simple scrolling or infinite wrapping logic
                            # Simple infinite wrap logic:
                            # The position of image i is (i * (POSTER_WIDTH + GAP)) - self.scroll_x
                            # If we wrap, we have multiple instances.
                            pass
                        
                        # Simplified: Just play the first item in the list for now, 
                        # or the one currently "active" if we had a cursor.
                        # Let's play the one roughly in the center.
                        offset = (self.scroll_x + SCREEN_WIDTH // 2) % total_width
                        idx = int(offset // (POSTER_WIDTH + GAP))
                        if idx < len(self.images):
                            self.play_video(self.images[idx]['data'])

            # Update
            self.scroll_x += SCROLL_SPEED
            if self.scroll_x >= total_width:
                self.scroll_x = 0
            
            # Draw
            self.screen.fill(BG_COLOR)
            
            # Draw Marquee
            # We need to draw enough images to fill the screen, wrapping around
            # Start index
            start_idx = int(self.scroll_x // (POSTER_WIDTH + GAP))
            # Draw until we fill screen
            current_x = -(self.scroll_x % (POSTER_WIDTH + GAP))
            
            # We might need to draw from start_idx to ...
            # Actually, simpler approach for infinite scroll:
            # Loop through all images, if they are visible, draw them.
            # Handle wrapping by drawing a second copy if needed.
            
            # Better approach for infinite scroll:
            # Calculate offset.
            
            for i in range(len(self.images)):
                x_pos = (i * (POSTER_WIDTH + GAP)) - self.scroll_x
                
                # Wrap around logic
                while x_pos < -POSTER_WIDTH:
                    x_pos += total_width
                while x_pos > SCREEN_WIDTH:
                    x_pos -= total_width
                
                # Only draw if visible
                if -POSTER_WIDTH < x_pos < SCREEN_WIDTH:
                    # Vertical centering
                    y_pos = (SCREEN_HEIGHT - POSTER_HEIGHT) // 2
                    self.screen.blit(self.images[i]['surface'], (x_pos, y_pos))

            # Draw Overlay Text
            text_surf = self.font.render("Now Playing", True, TEXT_COLOR)
            text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, (SCREEN_HEIGHT - POSTER_HEIGHT) // 2 - 50))
            self.screen.blit(text_surf, text_rect)
            
            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    app = MarqueeApp()
    app.run()
