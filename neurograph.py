import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import requests
import numpy as np
import pandas as pd
import cv2
from PIL import Image
import io
import math
import os
from datetime import datetime
import json

st.set_page_config(
    page_title="Solar Panel Detector",
    page_icon="☀️",
    layout="wide"
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .stApp { background-color: #0f1117; }
    h1, h2, h3 { color: #FFD700; }
    .metric-card {
        background: #1e2130;
        border: 1px solid #FFD700;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .stButton > button {
        background: linear-gradient(135deg, #FFD700, #FFA500);
        color: #0f1117;
        font-weight: bold;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        width: 100%;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #FFA500, #FF8C00);
        color: white;
    }
    .info-box {
        background: #1e2130;
        border-left: 4px solid #FFD700;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin: 8px 0;
        font-size: 14px;
        color: #ccc;
    }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
TILE_SIZE = 256
ZOOM_LEVEL = 18   # high zoom for rooftop detail
MAX_TILES  = 200  # safety cap

# ── Helpers ───────────────────────────────────────────────────────────────────

def lat_lon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.log(math.tan(math.radians(lat)) +
              1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
    return x, y

def tile_to_lat_lon(x, y, zoom):
    n = 2 ** zoom
    lon = x / n * 360 - 180
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon

def fetch_tile(x, y, zoom):
    """Fetch a single Bing-style satellite tile via ArcGIS World Imagery (free)."""
    url = (
        f"https://server.arcgisonline.com/ArcGIS/rest/services/"
        f"World_Imagery/MapServer/tile/{zoom}/{y}/{x}"
    )
    try:
        r = requests.get(url, timeout=10,
                         headers={"User-Agent": "SolarPanelDetector/1.0"})
        if r.status_code == 200:
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            return np.array(img)
    except Exception:
        pass
    return None

def detect_solar_panels_cv(tile_img, tile_x, tile_y, zoom, min_area=200):
    """
    Heuristic solar-panel detector using colour + contour analysis.

    Solar panels on satellite imagery tend to be:
      - Blue-ish or dark blue/grey
      - Rectangular with moderate reflectance
    """
    detections = []
    img_bgr = cv2.cvtColor(tile_img, cv2.COLOR_RGB2BGR)
    hsv     = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # Blue-tinted panels (crystalline silicon)
    lower_blue = np.array([90,  30,  30])
    upper_blue = np.array([140, 255, 200])
    mask_blue  = cv2.inRange(hsv, lower_blue, upper_blue)

    # Dark grey / near-black panels (thin film)
    lower_dark = np.array([0, 0, 20])
    upper_dark = np.array([180, 60, 90])
    mask_dark  = cv2.inRange(hsv, lower_dark, upper_dark)

    combined = cv2.bitwise_or(mask_blue, mask_dark)

    # Morphological cleanup
    kernel   = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN,  kernel, iterations=1)

    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)

    h_img, w_img = tile_img.shape[:2]

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue

        rect   = cv2.minAreaRect(cnt)
        box    = cv2.boxPoints(rect)
        box    = np.int0(box)
        cX     = int(rect[0][0])
        cY     = int(rect[0][1])
        w_r, h_r = rect[1]
        if w_r == 0 or h_r == 0:
            continue
        aspect = max(w_r, h_r) / min(w_r, h_r)
        if aspect > 6:      # too elongated
            continue

        # Pixel → lat/lon
        px_frac_x = cX / w_img
        px_frac_y = cY / h_img
        lat, lon  = tile_to_lat_lon(tile_x + px_frac_x,
                                    tile_y + px_frac_y, zoom)

        # Confidence heuristic: bigger + more square = more confident
        conf = min(0.95, 0.4 + (area / 4000) * 0.3 +
                   (1 / aspect) * 0.25)

        # Approx panel area in m² (1 pixel ≈ 0.6 m at zoom 18)
        pixel_m  = 0.6
        area_m2  = round(area * pixel_m ** 2, 1)

        detections.append({
            "lat":       round(lat, 7),
            "lon":       round(lon, 7),
            "confidence": round(conf, 3),
            "area_m2":   area_m2,
            "tile_x":    tile_x,
            "tile_y":    tile_y,
        })

    return detections


def run_detection(bbox, progress_bar, status_text):
    """Tile the bbox, fetch imagery, run detection, return detections list."""
    lat_min, lon_min, lat_max, lon_max = bbox

    x_min, y_max = lat_lon_to_tile(lat_min, lon_min, ZOOM_LEVEL)
    x_max, y_min = lat_lon_to_tile(lat_max, lon_max, ZOOM_LEVEL)

    x_min, x_max = min(x_min, x_max), max(x_min, x_max)
    y_min, y_max = min(y_min, y_max), max(y_min, y_max)

    total_tiles = (x_max - x_min + 1) * (y_max - y_min + 1)

    if total_tiles > MAX_TILES:
        st.warning(
            f"⚠️ Area requires {total_tiles} tiles — capped at {MAX_TILES}. "
            "Zoom in or draw a smaller box for full coverage."
        )
        # Shrink range proportionally
        ratio = (MAX_TILES / total_tiles) ** 0.5
        cx, cy = (x_min + x_max) // 2, (y_min + y_max) // 2
        dx = int((x_max - x_min) * ratio / 2)
        dy = int((y_max - y_min) * ratio / 2)
        x_min, x_max = cx - dx, cx + dx
        y_min, y_max = cy - dy, cy + dy
        total_tiles  = (x_max - x_min + 1) * (y_max - y_min + 1)

    all_detections = []
    processed = 0

    for tx in range(x_min, x_max + 1):
        for ty in range(y_min, y_max + 1):
            tile = fetch_tile(tx, ty, ZOOM_LEVEL)
            if tile is not None:
                dets = detect_solar_panels_cv(tile, tx, ty, ZOOM_LEVEL)
                all_detections.extend(dets)

            processed += 1
            progress_bar.progress(processed / total_tiles)
            status_text.text(
                f"Processing tile {processed}/{total_tiles}  "
                f"— {len(all_detections)} detections so far"
            )

    return all_detections


def build_results_map(bbox, detections):
    lat_min, lon_min, lat_max, lon_max = bbox
    center = [(lat_min + lat_max) / 2, (lon_min + lon_max) / 2]

    m = folium.Map(location=center, zoom_start=15,
                   tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
                          "World_Imagery/MapServer/tile/{z}/{y}/{x}",
                   attr="Esri World Imagery")

    # Draw bounding box
    folium.Rectangle(
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        color="#FFD700", weight=2, fill=True,
        fill_color="#FFD700", fill_opacity=0.05
    ).add_to(m)

    # Add markers
    for d in detections:
        conf  = d["confidence"]
        color = "#00FF88" if conf > 0.75 else "#FFA500" if conf > 0.5 else "#FF4444"
        folium.CircleMarker(
            location=[d["lat"], d["lon"]],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(
                f"<b>Solar Panel</b><br>"
                f"Confidence: {conf:.0%}<br>"
                f"Est. Area: {d['area_m2']} m²<br>"
                f"Lat: {d['lat']}<br>Lon: {d['lon']}",
                max_width=200
            )
        ).add_to(m)

    return m


# ── UI ────────────────────────────────────────────────────────────────────────

st.markdown("# ☀️ Solar Panel Detector")
st.markdown(
    '<div class="info-box">Draw a bounding box on the map <b>or</b> enter '
    'coordinates manually, then click <b>Run Detection</b>.</div>',
    unsafe_allow_html=True
)

tab_map, tab_coords = st.tabs(["🗺️ Draw on Map", "📐 Enter Coordinates"])

bbox = None

# ── Tab 1: interactive draw ───────────────────────────────────────────────────
with tab_map:
    st.markdown("**Draw a rectangle** on the map below to define your search area.")
    draw_map = folium.Map(location=[-15.4167, 28.2833], zoom_start=12,
                          tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
                                "World_Imagery/MapServer/tile/{z}/{y}/{x}",
                          attr="Esri World Imagery")
    folium.TileLayer("OpenStreetMap", name="Street Map").add_to(draw_map)
    folium.LayerControl().add_to(draw_map)
    Draw(
        export=False,
        draw_options={
            "rectangle": True, "polygon": False, "polyline": False,
            "circle": False,   "marker": False,   "circlemarker": False
        }
    ).add_to(draw_map)

    map_data = st_folium(draw_map, height=480, width="100%",
                         returned_objects=["all_drawings"])

    if map_data and map_data.get("all_drawings"):
        drawings = map_data["all_drawings"]
        if drawings:
            last = drawings[-1]
            if last.get("geometry", {}).get("type") == "Polygon":
                coords = last["geometry"]["coordinates"][0]
                lats = [c[1] for c in coords]
                lons = [c[0] for c in coords]
                bbox = (min(lats), min(lons), max(lats), max(lons))
                st.success(
                    f"✅ Bounding box: "
                    f"({bbox[0]:.5f}, {bbox[1]:.5f}) → "
                    f"({bbox[2]:.5f}, {bbox[3]:.5f})"
                )

# ── Tab 2: manual coordinates ─────────────────────────────────────────────────
with tab_coords:
    st.markdown("Enter the bounding box corners (decimal degrees).")
    col1, col2 = st.columns(2)
    with col1:
        lat_min_inp = st.number_input("Min Latitude  (South)", value=-15.45, format="%.6f")
        lon_min_inp = st.number_input("Min Longitude (West)",  value=28.25,  format="%.6f")
    with col2:
        lat_max_inp = st.number_input("Max Latitude  (North)", value=-15.38, format="%.6f")
        lon_max_inp = st.number_input("Max Longitude (East)",  value=28.35,  format="%.6f")

    if st.button("Use These Coordinates"):
        if lat_min_inp < lat_max_inp and lon_min_inp < lon_max_inp:
            bbox = (lat_min_inp, lon_min_inp, lat_max_inp, lon_max_inp)
            st.success(f"✅ Coordinates set: {bbox}")
        else:
            st.error("Min values must be less than Max values.")

# ── Run Detection ─────────────────────────────────────────────────────────────
st.divider()

if bbox:
    lat_min, lon_min, lat_max, lon_max = bbox
    area_km2 = (
        abs(lat_max - lat_min) * 111 *
        abs(lon_max - lon_min) * 111 * math.cos(math.radians((lat_min + lat_max) / 2))
    )
    st.markdown(
        f'<div class="info-box">📍 Selected area: <b>{area_km2:.2f} km²</b></div>',
        unsafe_allow_html=True
    )

    if st.button("🔍 Run Solar Panel Detection"):
        with st.spinner("Fetching satellite tiles and running detection…"):
            pb     = st.progress(0)
            status = st.empty()
            detections = run_detection(bbox, pb, status)
            pb.empty()
            status.empty()

        st.session_state["detections"] = detections
        st.session_state["bbox"]       = bbox

# ── Results ───────────────────────────────────────────────────────────────────
if "detections" in st.session_state and st.session_state["detections"] is not None:
    detections = st.session_state["detections"]
    bbox_r     = st.session_state["bbox"]

    st.markdown("## 📊 Results")

    c1, c2, c3, c4 = st.columns(4)
    total   = len(detections)
    hi_conf = sum(1 for d in detections if d["confidence"] > 0.75)
    avg_conf= np.mean([d["confidence"] for d in detections]) if detections else 0
    tot_area= sum(d["area_m2"] for d in detections)

    for col, label, value in [
        (c1, "Panels Detected",     total),
        (c2, "High Confidence",     hi_conf),
        (c3, "Avg Confidence",      f"{avg_conf:.0%}"),
        (c4, "Total Est. Area",     f"{tot_area:,.0f} m²"),
    ]:
        col.markdown(
            f'<div class="metric-card"><h3>{value}</h3><p style="color:#aaa;margin:0">'
            f'{label}</p></div>',
            unsafe_allow_html=True
        )

    if detections:
        st.markdown("### 🗺️ Detection Map")
        results_map = build_results_map(bbox_r, detections)
        st_folium(results_map, height=500, width="100%")

        # Legend
        st.markdown("""
        <div style="display:flex;gap:20px;margin:8px 0;font-size:13px">
            <span>🟢 High confidence (&gt;75%)</span>
            <span>🟠 Medium (50–75%)</span>
            <span>🔴 Low (&lt;50%)</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 📋 Detection Data")
        df = pd.DataFrame(detections)
        df["confidence_pct"] = (df["confidence"] * 100).round(1).astype(str) + "%"
        display_df = df[["lat", "lon", "confidence_pct", "area_m2"]].rename(columns={
            "lat": "Latitude", "lon": "Longitude",
            "confidence_pct": "Confidence", "area_m2": "Est. Area (m²)"
        })
        st.dataframe(display_df, use_container_width=True, height=300)

        # CSV download
        csv = df[["lat", "lon", "confidence", "area_m2"]].to_csv(index=False)
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f"solar_panels_{ts}.csv",
            mime="text/csv"
        )
    else:
        st.info(
            "No solar panels detected in this area. Try a different region, "
            "or zoom in further on a known solar installation."
        )
else:
    st.markdown(
        '<div class="info-box">👆 Draw a bounding box or enter coordinates above, '
        'then click <b>Run Detection</b>.</div>',
        unsafe_allow_html=True
    )