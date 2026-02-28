import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import subprocess
import os
import shutil
import warnings
import urllib.request
from urllib.error import HTTPError, URLError
import random
import pandas as pd

# Suppress warnings for cleaner terminal output
warnings.filterwarnings("ignore")

# --- Configuration ---
TEMP_DIR = "temp_map_frames"
OUTPUT_VIDEO = "/storage/emulated/0/Download/advanced_dynamic_map.mp4"

# Map Data URLs
WORLD_MAP_URL = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"

# Highly stable URLs for India with full state boundaries
INDIA_MAP_URL = "https://raw.githubusercontent.com/geohacker/india/master/state/india_state.geojson"
INDIA_FALLBACK_URL = "https://raw.githubusercontent.com/adarshbiradar/maps-of-india/master/india.geojson"

# Timing Settings (30 FPS)
FPS = 30
ZOOM_FRAMES = 25   # Frames it takes to zoom into a country
HOLD_FRAMES = 45   # Frames to hold and shake on the country
WORLD_BOUNDS = [-170, 170, -55, 85]

# Content
TITLE_TEXT = "Secret Underground\nAlien Bases"
DATA_COUNTRIES = ['United States of America', 'Russia', 'Brazil', 'Australia', 'India']

def ease_in_out(t):
    """Creates a smooth zoom effect (starts slow, speeds up, slows down at the end)"""
    return t * t * (3.0 - 2.0 * t)

def get_target_bounds(gdf, country_name, pad=15):
    """Calculates the camera bounding box for a specific country, forcing a 9:16 ratio"""
    if country_name == 'World':
        return WORLD_BOUNDS
        
    try:
        bounds = gdf[gdf.name == country_name].total_bounds
        minx, miny, maxx, maxy = bounds
    except ValueError:
        return WORLD_BOUNDS

    # Find center
    cx = (minx + maxx) / 2
    cy = (miny + maxy) / 2
    
    # Width and height with padding
    w = (maxx - minx) + pad
    h = (maxy - miny) + pad

    # Force 9:16 Aspect Ratio for Shorts
    target_ratio = 9 / 16
    if w / h > target_ratio:
        h = w / target_ratio
    else:
        w = h * target_ratio

    return [cx - w/2, cx + w/2, cy - h/2, cy + h/2]

def download_file(url, filename):
    """Robust download function with User-Agent to prevent blocking"""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(filename, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

def create_video():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)

    # 1. Download and Prepare Map Data
    print("Fetching World Map Data...")
    if not os.path.exists("world.geojson"):
        download_file(WORLD_MAP_URL, "world.geojson")
    
    world = gpd.read_file("world.geojson")
    world = world[(world.name != "Antarctica")]
    
    print("Fetching High-Quality India Map Data...")
    if not os.path.exists("india_full.geojson"):
        try:
            download_file(INDIA_MAP_URL, "india_full.geojson")
        except (HTTPError, URLError):
            print("Primary India map source failed, trying fallback URL...")
            try:
                download_file(INDIA_FALLBACK_URL, "india_full.geojson")
            except Exception as e:
                print(f"Warning: Could not fetch custom India map ({e}).")

    if os.path.exists("india_full.geojson"):
        try:
            india_full = gpd.read_file("india_full.geojson")
            # Force the name column so the script can target it
            india_full['name'] = 'India'
            
            # If the GeoJSON has separate states, dissolve them into one solid country border
            india_boundary = india_full.dissolve(by='name').reset_index()
            
            # Remove the old fragmented India map and concat the complete one
            world = world[world.name != 'India']
            world = gpd.GeoDataFrame(pd.concat([world, india_boundary], ignore_index=True))
            print("Success: Full unified India map applied.")
        except Exception as e:
            print(f"Warning: Failed to merge custom India map ({e}). Using default map.")

    print("\nGenerating Video Frames (This will take a few minutes)...")
    
    frame_count = 0
    current_bounds = WORLD_BOUNDS
    current_highlights = []

    # Reusable function to render a single frame
    def render_frame(bounds, highlights, text, shake_intensity=0.0):
        nonlocal frame_count
        
        fig = plt.figure(figsize=(9, 16), facecolor='#121212') 
        ax = fig.add_axes([0, 0, 1, 1]) 
        ax.set_facecolor('#121212')
        ax.axis('off')

        # Apply Camera Shake
        sx = random.uniform(-shake_intensity, shake_intensity)
        sy = random.uniform(-shake_intensity, shake_intensity)
        ax.set_xlim([bounds[0] + sx, bounds[1] + sx])
        ax.set_ylim([bounds[2] + sy, bounds[3] + sy])

        # Draw base map
        world.plot(ax=ax, color='#2A2A2A', edgecolor='#444444', linewidth=0.8)

        # Draw highlights
        if highlights:
            highlighted_gdf = world[world.name.isin(highlights)]
            highlighted_gdf.plot(ax=ax, color='#FF3366', edgecolor='#FFFFFF', linewidth=1.5)

        # Title and Bottom Text
        fig.text(0.5, 0.88, TITLE_TEXT, ha='center', va='center', 
                 fontsize=32, color='white', weight='bold')
        fig.text(0.5, 0.12, text, ha='center', va='center', 
                 fontsize=28, color='#00FFCC', weight='bold')

        frame_path = os.path.join(TEMP_DIR, f"frame_{frame_count:04d}.png")
        plt.savefig(frame_path, dpi=100, facecolor=fig.get_facecolor())
        plt.close(fig)
        
        if frame_count > 0 and frame_count % 30 == 0:
            print(f"Rendered {frame_count} frames... ({frame_count//30} seconds of video)")
        frame_count += 1

    # --- THE ANIMATION SEQUENCE ---

    # 1. Start at World View (1 second hold)
    for _ in range(30):
        render_frame(current_bounds, [], "Initiating Scan...")
    
    # 2. Loop through countries
    for country in DATA_COUNTRIES:
        target_bounds = get_target_bounds(world, country)
        
        # ZOOM IN Phase
        for i in range(ZOOM_FRAMES):
            t = ease_in_out(i / float(ZOOM_FRAMES))
            interp_bounds = [
                current_bounds[j] + (target_bounds[j] - current_bounds[j]) * t 
                for j in range(4)
            ]
            render_frame(interp_bounds, current_highlights, f"Scanning: {country}")
            
        current_highlights.append(country)
        current_bounds = target_bounds
        
        # HOLD AND SHAKE Phase (Camera is locked onto the country)
        for i in range(HOLD_FRAMES):
            # The 0.8 is the shake intensity. Increase it for a more violent shake.
            render_frame(current_bounds, current_highlights, f"TARGET LOCKED: {country}", shake_intensity=0.8)

    # 3. Zoom back out to World Map for the Finale
    target_bounds = WORLD_BOUNDS
    for i in range(ZOOM_FRAMES):
        t = ease_in_out(i / float(ZOOM_FRAMES))
        interp_bounds = [
            current_bounds[j] + (target_bounds[j] - current_bounds[j]) * t 
            for j in range(4)
        ]
        render_frame(interp_bounds, current_highlights, "Global Analysis Complete")
        
    # Final Hold Frame (2 seconds)
    current_bounds = target_bounds
    for i in range(60):
        render_frame(current_bounds, current_highlights, "The Truth is Out There...")

    # --- FFMPEG COMPILATION ---
    print("\nStitching video with FFmpeg...")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", f"{TEMP_DIR}/frame_%04d.png",
        "-c:v", "libx264",
        "-r", str(FPS),
        "-pix_fmt", "yuv420p",
        OUTPUT_VIDEO
    ]

    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    shutil.rmtree(TEMP_DIR)
    print(f"\nBOOM! Dynamic Video saved to: {OUTPUT_VIDEO}")

if __name__ == "__main__":
    create_video()

