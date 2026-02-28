#pip install shapely pyproj matplotlib geopandas requests


import geopandas as gpd
import matplotlib.pyplot as plt
import subprocess
import os
import shutil
import warnings
import urllib.request

# Suppress geopandas future warnings for cleaner output
warnings.filterwarnings("ignore")

# --- Configuration ---
TEMP_DIR = "temp_map_frames"
OUTPUT_VIDEO = "/storage/emulated/0/Download/geographic_fact_short.mp4"
MAP_FILE = "world_map.geojson"
MAP_URL = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"

# --- The Fake Data ---
TITLE_TEXT = "Countries with Secret\nUnderground Alien Bases"
DATA_COUNTRIES = ['United States of America', 'Russia', 'Brazil', 'Australia', 'India']

def create_video():
    # 1. Setup temporary directory for frames
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)

    # 2. Download and Load the world map
    if not os.path.exists(MAP_FILE):
        print("Downloading world map GeoJSON...")
        urllib.request.urlretrieve(MAP_URL, MAP_FILE)

    print("Loading world map data...")
    world = gpd.read_file(MAP_FILE)
    
    # Remove Antarctica to make the map look better and larger on a vertical screen
    world = world[(world.name != "Antarctica")]

    # 3. Frame Generation Function
    def save_frame(highlighted_list, frame_index, bottom_text):
        # 9:16 Aspect Ratio for YouTube Shorts
        fig = plt.figure(figsize=(9, 16), facecolor='#121212') 
        ax = fig.add_axes([0, 0, 1, 1]) 
        ax.set_facecolor('#121212')
        ax.axis('off')

        # Draw the base map in a sleek dark grey
        world.plot(ax=ax, color='#2A2A2A', edgecolor='#444444', linewidth=0.8)

        # Draw the highlighted countries
        if highlighted_list:
            highlighted = world[world.name.isin(highlighted_list)]
            # Neon pink/red highlight
            highlighted.plot(ax=ax, color='#FF3366', edgecolor='#FFFFFF', linewidth=1.2)

        # Static Top Title
        fig.text(0.5, 0.85, TITLE_TEXT, ha='center', va='center', 
                 fontsize=32, color='white', weight='bold', family='sans-serif')

        # Dynamic Bottom Text
        fig.text(0.5, 0.15, bottom_text, ha='center', va='center', 
                 fontsize=26, color='#00FFCC', weight='bold', family='sans-serif')

        # Ensure the map stays perfectly centered
        ax.set_xlim([-180, 180])
        ax.set_ylim([-60, 90]) 

        # Save the frame
        frame_path = os.path.join(TEMP_DIR, f"frame_{frame_index:03d}.png")
        plt.savefig(frame_path, dpi=120, facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"Generated frame {frame_index:03d}")

    # 4. Generate the sequence
    print("Generating frames...")
    current_highlights = []
    
    # Intro Frame (Empty map)
    save_frame(current_highlights, 0, "Declassifying files...")

    # Reveal countries one by one
    for i, country in enumerate(DATA_COUNTRIES, 1):
        current_highlights.append(country)
        save_frame(current_highlights, i, f"Target Acquired: {country}")

    # Final hold frame
    save_frame(current_highlights, len(DATA_COUNTRIES) + 1, "The Truth is Out There...")

    # 5. Compile into video using FFMPEG via Subprocess
    print("Stitching frames with FFmpeg...")
    
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", "1/1.5",
        "-i", f"{TEMP_DIR}/frame_%03d.png",
        "-c:v", "libx264",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        OUTPUT_VIDEO
    ]

    try:
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True)
        print(f"\nSuccess! Video saved to: {OUTPUT_VIDEO}")
    except subprocess.CalledProcessError as e:
        print(f"\nFFmpeg failed to run. Make sure FFmpeg is installed in Termux.")
        print(f"Error details: {e}")

    # 6. Cleanup
    shutil.rmtree(TEMP_DIR)

if __name__ == "__main__":
    create_video()

