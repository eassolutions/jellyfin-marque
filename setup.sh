#!/bin/bash

# Jellyfin Marquee Setup Script for Raspberry Pi Zero W

echo "Updating system..."
sudo apt-get update

echo "Installing dependencies... this may take awhile..."
# python3-pygame: SDL2 bindings for Python
# python3-requests: HTTP client
# mpv: Video player (hardware accelerated on Pi)
# libsdl2-2.0-0: SDL2 library
sudo apt-get install -y python3-pygame python3-requests mpv libsdl2-2.0-0

echo "Dependencies installed."

echo "Creating configuration file..."
if [ ! -f .env ]; then
    echo "JELLYFIN_URL=http://your-jellyfin-ip:8096" > .env
    echo "JELLYFIN_API_KEY=your_api_key" >> .env
    echo "Created .env file. Please edit it with your Jellyfin details."
else
    echo ".env file already exists."
fi

echo "Setup complete."
echo "To run the application:"
echo "  export $(cat .env | xargs) && python3 jellyfin_marquee.py"
