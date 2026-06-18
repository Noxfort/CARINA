# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# File: ui/loader/map_tile_downloader.py
# Author: Gabriel Moraes

import os
import math
import urllib.request
import logging
import json
from PIL import Image
import sumolib

def lonlat_to_tile(lon, lat, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return xtile, ytile

def tile_to_lonlat(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lon_deg, lat_deg

def generate_background_map(net_file_path: str, output_image_path: str) -> dict | None:
    """
    Downloads OpenStreetMap tiles for the SUMO network boundary,
    stitches them, and saves the image.
    Returns the SUMO coordinate bounds of the image for rendering alignment.
    """
    try:
        logging.info(f"[TileDownloader] Reading net file: {net_file_path}")
        net = sumolib.net.readNet(net_file_path)
        
        # Get network bounds
        boundary = net.getBoundary() # (xmin, ymin, xmax, ymax)
        xmin, ymin, xmax, ymax = boundary
        
        # Convert bounds to Lon/Lat
        lon_min, lat_min = net.convertXY2LonLat(xmin, ymin)
        lon_max, lat_max = net.convertXY2LonLat(xmax, ymax)
        
        # OpenStreetMap tiles are zoom-based
        zoom = 17
        
        # Get tile indices
        x_min, y_min = lonlat_to_tile(lon_min, lat_max, zoom)
        x_max, y_max = lonlat_to_tile(lon_max, lat_min, zoom)
        
        # Ensure correct ordering
        x_start, x_end = min(x_min, x_max), max(x_min, x_max)
        y_start, y_end = min(y_min, y_max), max(y_min, y_max)
        
        # Download tiles
        tile_width = 256
        tile_height = 256
        cols = x_end - x_start + 1
        rows = y_end - y_start + 1
        
        logging.info(f"[TileDownloader] Bounding Box SUMO: x=[{xmin}, {xmax}], y=[{ymin}, {ymax}]")
        logging.info(f"[TileDownloader] Bounding Box GPS: Lon=[{lon_min}, {lon_max}], Lat=[{lat_min}, {lat_max}]")
        logging.info(f"[TileDownloader] Downloading {cols}x{rows} = {cols*rows} tiles at zoom {zoom}...")
        
        # Create output image
        stitched_image = Image.new('RGB', (cols * tile_width, rows * tile_height))
        
        # OSM tile server requires User-Agent
        headers = {
            'User-Agent': 'CARIN-Traffic-Simulator/1.0 (contact@noxfort.com)'
        }
        
        temp_dir = os.path.dirname(output_image_path)
        os.makedirs(temp_dir, exist_ok=True)
        
        for c in range(cols):
            for r in range(rows):
                xtile = x_start + c
                ytile = y_start + r
                url = f"https://tile.openstreetmap.org/{zoom}/{xtile}/{ytile}.png"
                
                # Download with custom User-Agent
                req = urllib.request.Request(url, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=5) as response:
                        tile_data = response.read()
                    from io import BytesIO
                    tile_image = Image.open(BytesIO(tile_data))
                    stitched_image.paste(tile_image, (c * tile_width, r * tile_height))
                except Exception as e:
                    logging.warning(f"[TileDownloader] Failed to download tile {xtile},{ytile}: {e}")
                    # Keep it light gray on failure
                    tile_image = Image.new('RGB', (tile_width, tile_height), color='#EAEAEA')
                    stitched_image.paste(tile_image, (c * tile_width, r * tile_height))
        
        # Apply high-end dark theme styling to make it look professional and blend with Flet's theme
        try:
            from PIL import ImageEnhance, ImageOps
            # 1. Grayscale
            stitched_image = ImageOps.grayscale(stitched_image).convert("RGB")
            # 2. Invert colors (light backgrounds become dark, roads become light)
            stitched_image = ImageOps.invert(stitched_image)
            # 3. Dim down so vector details stand out
            enhancer = ImageEnhance.Brightness(stitched_image)
            stitched_image = enhancer.enhance(0.35)
            # 4. Blend with solid slate-900 (#0F172A) to match the dashboard background color
            bg_tint = Image.new("RGB", stitched_image.size, color="#0F172A")
            stitched_image = Image.blend(stitched_image, bg_tint, 0.4)
        except Exception as e:
            logging.warning(f"[TileDownloader] Dark theme enhancements failed: {e}")

        stitched_image.save(output_image_path)
        logging.info(f"[TileDownloader] Saved stitched background map to: {output_image_path}")
        
        # Compute GPS coordinates of the stitched image boundaries
        lon_left, lat_top = tile_to_lonlat(x_start, y_start, zoom)
        lon_right, lat_bottom = tile_to_lonlat(x_end + 1, y_end + 1, zoom)
        
        # Convert image bounds back to SUMO coordinates
        x_min_sumo, y_max_sumo = net.convertLonLat2XY(lon_left, lat_top)
        x_max_sumo, y_min_sumo = net.convertLonLat2XY(lon_right, lat_bottom)
        
        meta = {
            "x_min": x_min_sumo,
            "y_min": y_min_sumo,
            "x_max": x_max_sumo,
            "y_max": y_max_sumo
        }
        
        # Save metadata to json for reuse
        meta_path = output_image_path + ".json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f)
            
        return meta
    except Exception as e:
        logging.error(f"[TileDownloader] Error generating background map: {e}", exc_info=True)
        return None
