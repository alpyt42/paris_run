import streamlit as st
import folium
import leafmap.foliumap as leafmap
from streamlit_folium import folium_static
import gpxpy
import os
import glob
import pandas as pd
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.colors as mcolors
from io import BytesIO, StringIO
import math
import geopandas as gpd
from shapely.geometry import LineString
import branca.colormap as cm
import concurrent.futures
import json
import pickle
from pathlib import Path
import hashlib
import base64
import urllib.parse
import webbrowser

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Visualisation des Traces Paris Run",
    page_icon="🏃‍♂️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://docs.streamlit.io",
        "Report a bug": "mailto:admin@yourdomain.com",
        "About": "Application pour visualiser, animer et analyser les traces de Paris Run."
    }
)

# Configuration supplémentaire
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'
if 'map_style' not in st.session_state:
    st.session_state['map_style'] = 'CartoDB positron'

# Appliquer un style CSS personnalisé
st.markdown("""
<style>
    .main {
        background-color: #f5f7f9;
    }
    .st-emotion-cache-16txtl3 h1, .block-container h1 {
        color: #3366cc;
        text-align: center;
        font-weight: 700;
        margin-bottom: 30px;
    }
    .st-emotion-cache-16txtl3 h2, .block-container h2 {
        color: #4a80b4;
        margin-top: 40px;
        margin-bottom: 20px;
    }
    .st-emotion-cache-1kyxreq {
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-radius: 10px;
        padding: 20px;
        background-color: white;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: white;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 5px;
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3366cc !important;
        color: white !important;
        font-weight: bold;
    }
    .map-container {
        border: 1px solid #ddd;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    .export-btn {
        background-color: #4CAF50;
        color: white;
        padding: 10px 15px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-weight: bold;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 10px 0;
        transition: 0.3s;
    }
    .export-btn:hover {
        background-color: #45a049;
    }
    .stButton>button {
        background-color: #3366cc;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #254e8f;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    iframe {
        border: none !important;
        width: 100% !important;
    }
    .stSelectbox label, .stSlider label {
        font-weight: 500;
        color: #2c3e50;
    }
    .stTabs [data-baseweb="tab"] p {
        font-size: 1rem;
        margin-bottom: 0;
    }
    .stat-card {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 20px;
    }
    .stat-card h3 {
        margin-top: 0;
        color: #3366cc;
        font-size: 1.2rem;
    }
    .stat-card p {
        font-size: 1.8rem;
        font-weight: bold;
        margin: 10px 0;
        color: #2c3e50;
    }
    .dark-mode {
        background-color: #2c3e50;
        color: #ecf0f1;
    }
    .dark-mode .stat-card {
        background-color: #34495e;
        color: #ecf0f1;
    }
    .dark-mode .stTabs [data-baseweb="tab-list"] {
        background-color: #34495e;
    }
    .tooltip-card {
        position: relative;
        display: inline-block;
        margin: 0 5px;
    }
    .tooltip-card:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    .tooltip-text {
        visibility: hidden;
        width: 200px;
        background-color: #555;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 5px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -100px;
        opacity: 0;
        transition: opacity 0.3s;
    }
    .animate {
        transition: all 0.3s ease;
    }
    .segment-active {
        stroke-width: 5;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% {
            stroke-opacity: 0.7;
        }
        50% {
            stroke-opacity: 1;
        }
        100% {
            stroke-opacity: 0.7;
        }
    }
    .progress-container {
        width: 100%;
        background-color: #ddd;
        border-radius: 5px;
        margin: 10px 0;
        overflow: hidden;
    }
    .progress-bar {
        height: 10px;
        background-color: #3366cc;
        width: 0%;
        border-radius: 5px;
        transition: width 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# CACHE ET OPTIMISATION
# ----------------------------------------------------------

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

if 'session_id' not in st.session_state:
    st.session_state['session_id'] = str(time.time())

if 'map_data' not in st.session_state:
    st.session_state['map_data'] = None
if 'animation_data' not in st.session_state:
    st.session_state['animation_data'] = None


def get_cache_key(directory, segments=None):
    """Génère une clé de cache basée sur le répertoire et les segments sélectionnés"""
    key = f"{directory}"
    if segments:
        key += f"_{'-'.join(map(str, sorted(segments)))}"
    return hashlib.md5(key.encode()).hexdigest()


def save_to_cache(data, cache_key):
    """Sauvegarde les données dans le cache"""
    cache_file = CACHE_DIR / f"{cache_key}.pkl"
    with open(cache_file, 'wb') as f:
        pickle.dump(data, f)


def load_from_cache(cache_key):
    """Charge les données depuis le cache si disponibles"""
    cache_file = CACHE_DIR / f"{cache_key}.pkl"
    if cache_file.exists():
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return None


@st.cache_data(ttl=3600)
def load_all_gpx_files(directory):
    """
    Charge tous les fichiers relai_*.gpx dans 'directory' et
    retourne une liste de dicts {segment, points, file}.
    """
    cache_key = get_cache_key(directory)
    cached_data = load_from_cache(cache_key)
    if cached_data:
        return cached_data

    if not os.path.exists(directory):
        st.warning(f"Le répertoire {directory} n'existe pas!")
        return []

    gpx_files = sorted(
        glob.glob(os.path.join(directory, "relai_*.gpx")),
        key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0])
    )

    if not gpx_files:
        st.warning(f"Aucun fichier GPX trouvé dans {directory}")
        return []

    all_traces = []

    def process_gpx_file(gpx_file):
        try:
            with open(gpx_file, 'r') as f:
                gpx = gpxpy.parse(f)
                track_points = []
                for track in gpx.tracks:
                    for segment in track.segments:
                        points = segment.points
                        # Echantillonnage si > 500 points
                        if len(points) > 500:
                            step = len(points) // 500 + 1
                            points = points[::step]

                        for point in points:
                            track_points.append((point.latitude, point.longitude))

                segment_num = int(os.path.basename(gpx_file).split('_')[1].split('.')[0])
                return {
                    'segment': segment_num,
                    'points': track_points,
                    'file': gpx_file
                }
        except Exception as e:
            st.error(f"Erreur lors du chargement de {gpx_file}: {str(e)}")
            return {'segment': 0, 'points': [], 'file': gpx_file}

    # Chargement en parallèle
    with concurrent.futures.ThreadPoolExecutor() as executor:
        all_traces = list(executor.map(process_gpx_file, gpx_files))

    all_traces = [t for t in all_traces if t is not None]
    all_traces.sort(key=lambda x: x['segment'])

    save_to_cache(all_traces, cache_key)
    return all_traces


def load_gpx_file_full(file_path):
    """Charge tous les points d'un fichier GPX sans échantillonnage."""
    try:
        with open(file_path, 'r') as f:
            gpx = gpxpy.parse(f)
            track_points = []
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        track_points.append(
                            (point.latitude, point.longitude, point.elevation, point.time)
                        )
            return track_points
    except Exception as e:
        st.error(f"Erreur lors du chargement de {file_path}: {str(e)}")
        return []


def generate_color_palette(n):
    """Génère une palette de n couleurs distinctes."""
    if n <= 0:
        return []
    color_list = list(plt.cm.rainbow(np.linspace(0, 1, max(1, n))))
    return [mcolors.rgb2hex(color) for color in list(color_list)]


@st.cache_data(ttl=3600)
def convert_to_geojson(traces, selected_segments=None):
    """Convertit les traces en GeoJSON pour un rendu plus efficace."""
    if not traces:
        return {"type": "FeatureCollection", "features": []}

    if not selected_segments:
        selected_segments = [t['segment'] for t in traces]

    features = []
    for trace in traces:
        if trace['segment'] in selected_segments:
            if not trace['points'] or len(trace['points']) < 2:
                continue
            coords = [(p[1], p[0]) for p in trace['points']]  # GeoJSON = (lon, lat)
            try:
                line = LineString(coords)  # On vérifie la validité
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords
                    },
                    "properties": {
                        "segment": trace['segment'],
                        "nb_points": len(trace['points'])
                    }
                }
                features.append(feature)
            except Exception as e:
                st.error(f"Erreur pour le segment {trace['segment']}: {str(e)}")

    return {
        "type": "FeatureCollection",
        "features": features
    }


def create_single_segment_map(trace, with_markers=True):
    """Crée une carte pour un segment donné."""
    if not trace or not trace.get('points'):
        return folium.Map(location=[48.8566, 2.3522], zoom_start=12)

    points = trace['points']
    center_lat = sum(p[0] for p in points) / len(points)
    center_lon = sum(p[1] for p in points) / len(points)

    tile_style = st.session_state['map_style']
    tile_attributions = {
        'CartoDB positron': '&copy; OpenStreetMap contributors &copy; CARTO',
        'CartoDB dark_matter': '&copy; OpenStreetMap contributors &copy; CARTO',
        'OpenStreetMap': '&copy; OpenStreetMap contributors',
        'Stamen Terrain': '&copy; Stamen Design &copy; OSM contributors',
        'Stamen Toner': '&copy; Stamen Design &copy; OSM contributors'
    }

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles=tile_style,
        attr=tile_attributions.get(tile_style, 'Map data contributors')
    )

    folium.PolyLine(
        points,
        color='blue',
        weight=5,
        opacity=0.8,
        tooltip=f"Segment {trace['segment']}"
    ).add_to(m)

    if with_markers and points:
        folium.Marker(
            location=points[0],
            popup=f"Début du segment {trace['segment']}",
            tooltip="Départ",
            icon=folium.Icon(color='green', icon='flag', prefix='fa')
        ).add_to(m)

        folium.Marker(
            location=points[-1],
            popup=f"Fin du segment {trace['segment']}",
            tooltip="Arrivée",
            icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa')
        ).add_to(m)

    folium.plugins.MeasureControl(
        position='bottomleft',
        primary_length_unit='kilometers'
    ).add_to(m)
    return m


def create_optimized_map(traces, selected_segments=None):
    """Crée une carte Folium optimisée en affichant un GeoJSON."""
    if not traces:
        return folium.Map(location=[48.8566, 2.3522], zoom_start=12,
                          tiles="CartoDB positron", attr="CartoDB")

    if not selected_segments:
        selected_segments = [t['segment'] for t in traces]

    all_points = []
    for trace in traces:
        if trace['segment'] in selected_segments and trace['points']:
            # On prend quelques points pour le calcul du centre
            sample_points = trace['points'][:1] + trace['points'][-1:]
            all_points.extend(sample_points)

    if not all_points:
        center_lat, center_lon = 48.8566, 2.3522
    else:
        center_lat = sum(p[0] for p in all_points) / len(all_points)
        center_lon = sum(p[1] for p in all_points) / len(all_points)

    tile_style = st.session_state['map_style']
    tile_attributions = {
        'CartoDB positron': '&copy; OpenStreetMap contributors &copy; CARTO',
        'CartoDB dark_matter': '&copy; OpenStreetMap contributors &copy; CARTO',
        'OpenStreetMap': '&copy; OpenStreetMap contributors',
        'Stamen Terrain': '&copy; Stamen Design &copy; OSM contributors',
        'Stamen Toner': '&copy; Stamen Design &copy; OSM contributors'
    }

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles=tile_style,
        attr=tile_attributions.get(tile_style, 'Map data contributors')
    )

    geojson_data = convert_to_geojson(traces, selected_segments)

    if not geojson_data["features"]:
        st.warning("Aucune trace à afficher pour les segments sélectionnés.")
        return m

    n_segments = len([t for t in traces if t['segment'] in selected_segments])
    if n_segments > 0:
        colormap = cm.linear.YlOrRd_09.scale(1, max(1, n_segments))
        folium.GeoJson(
            geojson_data,
            name="Segments",
            style_function=lambda feature: {
                "color": colormap(feature["properties"]["segment"] % max(1, n_segments)),
                "weight": 3,
                "opacity": 0.7,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["segment", "nb_points"],
                aliases=["Segment", "Nombre de points"],
                localize=True
            )
        ).add_to(m)

    show_markers = st.session_state.get('show_markers', True)
    if show_markers and len(selected_segments) <= 30:
        for trace in traces:
            if trace['segment'] in selected_segments and trace['points']:
                folium.Marker(
                    location=trace['points'][0],
                    popup=f"Début segment {trace['segment']}",
                    tooltip=f"Début - Segment {trace['segment']}",
                    icon=folium.Icon(color='green', icon='play', prefix='fa', icon_size=(15, 15))
                ).add_to(m)

                folium.Marker(
                    location=trace['points'][-1],
                    popup=f"Fin segment {trace['segment']}",
                    tooltip=f"Fin - Segment {trace['segment']}",
                    icon=folium.Icon(color='red', icon='stop', prefix='fa', icon_size=(15, 15))
                ).add_to(m)

    folium.LayerControl().add_to(m)
    folium.plugins.MeasureControl(
        position='bottomleft',
        primary_length_unit='kilometers'
    ).add_to(m)

    return m


def generate_download_link(content, filename, link_text):
    """Génère un lien de téléchargement pour un contenu donné."""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'data:text/gpx;base64,{b64}'
    return f'<a href="{href}" download="{filename}" class="export-btn">{link_text}</a>'


def create_animation_html(traces, max_segments=10, width=800, height=600):
    """
    Crée un code HTML contenant une animation Leaflet (segment par segment).
    """
    if not traces:
        return """
        <div style="text-align:center;padding:20px;background-color:#f8f9fa;border-radius:5px;">
            <p>Aucune trace disponible pour l'animation</p>
        </div>
        """

    limited_traces = traces[:min(max_segments, len(traces))]
    animation_speed = st.session_state.get('animation_speed', 100)

    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
        #map { width: 100%; height: 100vh; }
        #controls {
            position: absolute;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            z-index: 1000;
            text-align: center;
        }
        button {
            background: #3366cc;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 15px;
            margin: 0 5px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover { background: #254e8f; }
        #progress {
            width: 100%;
            height: 10px;
            background: #eee;
            margin-top: 10px;
            border-radius: 5px;
            overflow: hidden;
        }
        #progress-bar {
            height: 100%;
            width: 0%;
            background: #3366cc;
            transition: width 0.2s;
        }
        #info {
            background: #f8f9fa;
            padding: 5px 10px;
            margin-top: 10px;
            border-radius: 5px;
            font-size: 14px;
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/leaflet.css"/>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/leaflet.js"></script>
</head>
<body>
    <div id="controls">
        <button id="play">▶️ Play</button>
        <button id="pause">⏸️ Pause</button>
        <button id="reset">🔄 Reset</button>
        <div id="progress"><div id="progress-bar"></div></div>
        <div id="info">Segment: 0 / 0 points</div>
    </div>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([48.8566, 2.3522], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        var traces = [
    """

    for trace in limited_traces:
        if trace['points']:
            html += f"""{{
                segment: {trace['segment']},
                points: {json.dumps(trace['points'])}
            }},"""

    html += """
        ];

        var animationId;
        var currentSegmentIndex = 0;
        var currentPointIndex = 0;
        var speed = """ + str(animation_speed) + """;
        var isPlaying = false;
        var colors = [];

        function generateColors(n) {
            for (var i = 0; i < n; i++) {
                var h = (i * 360 / n) % 360;
                colors.push(`hsl(${h}, 70%, 50%)`);
            }
        }

        generateColors(traces.length);

        var completedPaths = [];
        var currentPath = null;
        var progressBar = document.getElementById('progress-bar');
        var infoBox = document.getElementById('info');

        function centerMap() {
            if (traces.length === 0) return;
            
            // D'abord centrer sur le premier point avec un zoom approprié
            if (traces[0] && traces[0].points && traces[0].points.length > 0) {
                var firstPoint = traces[0].points[0];
                map.setView([firstPoint[0], firstPoint[1]], 15);
            }
            
            // Fonction existante pour calculer les limites (utilisée par le bouton "Voir tout")
            function fitAllBounds() {
                var allLats = [];
                var allLngs = [];

                traces.forEach(function(trace) {
                    trace.points.forEach(function(pt) {
                        allLats.push(pt[0]);
                        allLngs.push(pt[1]);
                    });
                });

                var minLat = Math.min(...allLats);
                var maxLat = Math.max(...allLats);
                var minLng = Math.min(...allLngs);
                var maxLng = Math.max(...allLngs);

                map.fitBounds([
                    [minLat, minLng],
                    [maxLat, maxLng]
                ]);
            }
            
            // Ajouter un bouton pour voir tous les segments
            if (!window.viewAllButtonAdded && traces.length > 1) {
                var viewAllButton = L.control({position: 'topright'});
                viewAllButton.onAdd = function() {
                    var div = L.DomUtil.create('div', 'view-all-button');
                    div.innerHTML = '<button style="background-color:#3366cc;color:white;border:none;border-radius:4px;padding:8px 12px;cursor:pointer;font-weight:bold;">Voir tout</button>';
                    div.firstChild.addEventListener('click', fitAllBounds);
                    return div;
                };
                viewAllButton.addTo(map);
                window.viewAllButtonAdded = true;
            }
        }

        function initAnimation() {
            centerMap();
            resetAnimation();
        }

        function resetAnimation() {
            if (animationId) {
                clearTimeout(animationId);
            }
            isPlaying = false;
            currentSegmentIndex = 0;
            currentPointIndex = 0;

            completedPaths.forEach(function(path) {
                map.removeLayer(path);
            });
            completedPaths = [];

            if (currentPath) {
                map.removeLayer(currentPath);
                currentPath = null;
            }

            progressBar.style.width = '0%';
            infoBox.textContent = 'Cliquez sur Play pour démarrer';
        }

        function animate() {
            if (currentSegmentIndex >= traces.length) {
                isPlaying = false;
                infoBox.textContent = 'Animation terminée';
                return;
            }

            var currentTrace = traces[currentSegmentIndex];
            var points = currentTrace.points;

            if (currentPointIndex === 0) {
                if (currentPath) {
                    completedPaths.push(currentPath);
                }
                currentPath = L.polyline([], {
                    color: colors[currentSegmentIndex % colors.length],
                    weight: 4
                }).addTo(map);
            }

            currentPath.addLatLng(points[currentPointIndex]);
            map.panTo(points[currentPointIndex]);

            var totalPoints = traces.reduce((sum, t) => sum + t.points.length, 0);
            var pointsProcessed = traces
                .slice(0, currentSegmentIndex)
                .reduce((s, t) => s + t.points.length, 0) + currentPointIndex;
            var progress = (pointsProcessed / totalPoints) * 100;
            progressBar.style.width = progress + '%';

            infoBox.textContent = `Segment: ${currentTrace.segment} - Point: ${currentPointIndex+1}/${points.length}`;

            currentPointIndex++;
            if (currentPointIndex >= points.length) {
                currentSegmentIndex++;
                currentPointIndex = 0;
            }

            if (isPlaying) {
                animationId = setTimeout(animate, speed);
            }
        }

        document.getElementById('play').addEventListener('click', function() {
            if (!isPlaying) {
                isPlaying = true;
                animate();
            }
        });

        document.getElementById('pause').addEventListener('click', function() {
            isPlaying = false;
            if (animationId) {
                clearTimeout(animationId);
            }
        });

        document.getElementById('reset').addEventListener('click', resetAnimation);

        initAnimation();
    </script>
</body>
</html>
"""
    return html


def create_segment_animation_html(trace, width=800, height=600):
    """
    Crée un code HTML contenant une animation Leaflet pour un seul segment.
    """
    if not trace or not trace.get('points') or len(trace['points']) < 2:
        return """
        <div style="text-align:center;padding:20px;background-color:#f8f9fa;border-radius:5px;">
            <p>Pas assez de points pour créer une animation</p>
        </div>
        """

    animation_speed = st.session_state.get('segment_animation_speed', 100)

    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
        #map { width: 100%; height: 100vh; }
        #controls {
            position: absolute;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            z-index: 1000;
            text-align: center;
        }
        button {
            background: #3366cc;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 15px;
            margin: 0 5px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover { background: #254e8f; }
        #progress {
            width: 100%;
            height: 10px;
            background: #eee;
            margin-top: 10px;
            border-radius: 5px;
            overflow: hidden;
        }
        #progress-bar {
            height: 100%;
            width: 0%;
            background: #3366cc;
            transition: width 0.2s;
        }
        #info {
            background: #f8f9fa;
            padding: 5px 10px;
            margin-top: 10px;
            border-radius: 5px;
            font-size: 14px;
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/leaflet.css"/>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/leaflet.js"></script>
</head>
<body>
    <div id="controls">
        <button id="play">▶️ Play</button>
        <button id="pause">⏸️ Pause</button>
        <button id="reset">🔄 Reset</button>
        <div id="progress"><div id="progress-bar"></div></div>
        <div id="info">Point: 0 / 0</div>
    </div>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([48.8566, 2.3522], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        var points = """ + json.dumps(trace['points']) + """;
        var segment = """ + str(trace['segment']) + """;

        var animationId;
        var currentPointIndex = 0;
        var speed = """ + str(animation_speed) + """;
        var isPlaying = false;
        var color = '#3366cc';

        var path = null;
        var progressBar = document.getElementById('progress-bar');
        var infoBox = document.getElementById('info');

        function centerMap() {
            if (points.length === 0) return;
            var allLats = [];
            var allLngs = [];

            points.forEach(function(pt) {
                allLats.push(pt[0]);
                allLngs.push(pt[1]);
            });

            var minLat = Math.min(...allLats);
            var maxLat = Math.max(...allLats);
            var minLng = Math.min(...allLngs);
            var maxLng = Math.max(...allLngs);

            map.fitBounds([
                [minLat, minLng],
                [maxLat, maxLng]
            ]);
        }

        function initAnimation() {
            centerMap();
            resetAnimation();
        }

        function resetAnimation() {
            if (animationId) {
                clearTimeout(animationId);
            }
            isPlaying = false;
            currentPointIndex = 0;

            if (path) {
                map.removeLayer(path);
            }
            path = L.polyline([], {
                color: color,
                weight: 5
            }).addTo(map);

            progressBar.style.width = '0%';
            infoBox.textContent = 'Prêt à démarrer';
        }

        function animate() {
            if (currentPointIndex >= points.length) {
                isPlaying = false;
                infoBox.textContent = 'Animation terminée';
                return;
            }

            path.addLatLng(points[currentPointIndex]);
            map.panTo(points[currentPointIndex]);

            var progress = (currentPointIndex / points.length) * 100;
            progressBar.style.width = progress + '%';
            infoBox.textContent = `Point: ${currentPointIndex+1}/${points.length}`;

            currentPointIndex++;

            if (isPlaying) {
                animationId = setTimeout(animate, speed);
            }
        }

        document.getElementById('play').addEventListener('click', function() {
            if (!isPlaying) {
                isPlaying = true;
                animate();
            }
        });

        document.getElementById('pause').addEventListener('click', function() {
            isPlaying = false;
            if (animationId) {
                clearTimeout(animationId);
            }
        });

        document.getElementById('reset').addEventListener('click', resetAnimation);

        initAnimation();
    </script>
</body>
</html>
"""
    return html


import urllib.parse

def generate_google_maps_link(points):
    """
    Génère un lien Google Maps pour visualiser l'itinéraire d'un tracé GPX.
    
    Args:
        points: Liste de tuples (latitude, longitude) représentant le tracé.
    
    Returns:
        str: URL Google Maps complète pour visualiser l'itinéraire.
        
    Notes:
        - Limite le nombre de points à 10 pour respecter les restrictions d'URL de Google
        - Utilise les coordonnées décimales pour l'itinéraire principal
        - Ajoute les coordonnées DMS pour le départ et l'arrivée en paramètres informatifs
    """
    if not points or len(points) < 2:
        return "https://www.google.com/maps"
    
    # ----------- 1) Échantillonnage des points si trop nombreux (limite URL) ------------
    if len(points) > 10:
        # Garder premier, dernier et points intermédiaires distribués uniformément
        step = (len(points) - 1) // 8  # Pour avoir ~10 points au total
        sampled_indices = [0] + [i for i in range(step, len(points)-1, step)][:8] + [len(points)-1]
        route_points = [points[i] for i in sampled_indices]
    else:
        route_points = points
    
    # ----------- 2) Construction de l'itinéraire en décimal ------------
    base_url = "https://www.google.com/maps/dir/"
    decimal_coords = [f"{lat:.6f},{lon:.6f}" for lat, lon in route_points]
    path = "/".join(decimal_coords)
    
    # ----------- 3) Fonction utilitaire pour convertir décimal en DMS ---
    def decimal_to_dms(coord, is_lat=True):
        """Convertit une coordonnée décimale en DMS (degrés, minutes, secondes)."""
        abs_coord = abs(coord)
        degrees = int(abs_coord)
        minutes_float = (abs_coord - degrees) * 60
        minutes = int(minutes_float)
        seconds = (minutes_float - minutes) * 60
        
        direction = "N" if is_lat and coord >= 0 else "S" if is_lat else "E" if coord >= 0 else "W"
        return f"{degrees}°{minutes}'{seconds:.1f}\"{direction}"
    
    # ----------- 4) Préparation du DMS pour le 1er et le dernier point --
    lat1, lon1 = points[0]
    latN, lonN = points[-1]
    
    start_dms = f"{decimal_to_dms(lat1, True)} {decimal_to_dms(lon1, False)}"
    end_dms = f"{decimal_to_dms(latN, True)} {decimal_to_dms(lonN, False)}"
    
    # ----------- 5) Construction des paramètres de requête -------------------
    query_params = [
        f"start={urllib.parse.quote(start_dms)}",
        f"end={urllib.parse.quote(end_dms)}",
        "data=!4m2!4m1!3e2"  # Force le mode à pied
    ]
    query_string = "&".join(query_params)
    
    # ----------- 6) Assemblage final de l'URL ----------------------------
    final_url = f"{base_url}{path}?{query_string}"
    
    # Vérifier que l'URL ne dépasse pas une taille raisonnable (2000 caractères est une limite courante)
    if len(final_url) > 2000:
        # Solution de repli: utiliser uniquement le premier et le dernier point
        minimal_path = f"{points[0][0]:.6f},{points[0][1]:.6f}/{points[-1][0]:.6f},{points[-1][1]:.6f}"
        return f"{base_url}{minimal_path}?{query_string}"
        
    return final_url

def export_to_gpx(selected_trace):
    """
    Exemple minimal de création d'un contenu GPX en chaîne de caractères.
    Adaptez si vous voulez inclure l'élévation, le temps, etc.
    """
    if not selected_trace or not selected_trace.get('points'):
        return ""

    gpx_header = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="ParisRunVisualizer" xmlns="http://www.topografix.com/GPX/1/1">
    <trk>
        <name>Segment_{}</name>
        <trkseg>
""".format(selected_trace['segment'])

    gpx_footer = """        </trkseg>
    </trk>
</gpx>
"""

    gpx_body = ""
    for lat, lon in selected_trace['points']:
        gpx_body += f"            <trkpt lat=\"{lat}\" lon=\"{lon}\"></trkpt>\n"

    return gpx_header + gpx_body + gpx_footer


# ------------------------------------------------------------------
# APPLICATION STREAMLIT
# ------------------------------------------------------------------

st.title('🏃‍♂️ Visualisation des Traces de Paris Run')

# Sélection du style de carte
map_styles = {
    "Clair (Positron)": "CartoDB positron",
    "Sombre (Dark Matter)": "CartoDB dark_matter",
    "Rues (OpenStreetMap)": "OpenStreetMap",
    "Satellite": "Stamen Terrain",
    "Minimaliste": "Stamen Toner"
}
selected_style = st.sidebar.selectbox(
    "Style de carte",
    list(map_styles.keys()),
    index=0,
    help="Changer l'apparence des cartes"
)
st.session_state['map_style'] = map_styles[selected_style]

# Dictionnaire de répertoires contenant les GPX
# Récupérer dynamiquement les dossiers commençant par "Relais_"
gpx_dirs = {}
base_dir = os.path.dirname(os.path.abspath(__file__))
for item in os.listdir(base_dir):
    if os.path.isdir(os.path.join(base_dir, item)) and item.startswith("Relais_"):
        # Utilisez le nom du dossier comme clé et comme valeur
        # Formatage pour l'affichage: remplacer les underscores par des espaces et capitaliser
        display_name = " ".join(word.capitalize() for word in item.split('_'))
        gpx_dirs[display_name] = item

# On vérifie quels dossiers existent
available_dirs = {}
for name, path in gpx_dirs.items():
    if os.path.exists(path):
        available_dirs[name] = path

if not available_dirs:
    st.error("Aucun dossier de données GPX trouvé!")
    st.stop()

selected_dir = st.sidebar.selectbox(
    "Sélectionner la source des données",
    list(available_dirs.keys())
)
gpx_directory = available_dirs[selected_dir]

# Chargement des données
with st.spinner('Chargement des données GPX...'):
    traces = load_all_gpx_files(gpx_directory)

if not traces:
    st.error(f"Aucune donnée GPX disponible dans le dossier {gpx_directory}")
    st.stop()

# Déplacer la logique de filtrage vers l'extérieur des onglets pour qu'elle soit commune
if 'filter_mode' not in st.session_state:
    st.session_state['filter_mode'] = "Tous les segments"
if 'selected_segments' not in st.session_state:
    st.session_state['selected_segments'] = []

st.sidebar.header("Filtres")
filter_mode = st.sidebar.radio(
    "Mode de sélection des segments",
    ["Tous les segments", "Plage de segments", "Segments spécifiques"],
    key="filter_mode_radio"
)
available_segments = [t['segment'] for t in traces]

if not available_segments:
    st.warning("Pas de segments disponibles dans les fichiers GPX")
    st.session_state['selected_segments'] = []
else:
    if filter_mode == "Tous les segments":
        max_display = st.sidebar.slider(
            "Nombre max de segments à afficher",
            min_value=10, max_value=len(available_segments),
            value=min(50, len(available_segments))
        )
        st.session_state['selected_segments'] = available_segments[:max_display]
    elif filter_mode == "Plage de segments":
        if len(available_segments) < 2:
            st.warning("Pas assez de segments pour définir une plage.")
            st.session_state['selected_segments'] = available_segments
        else:
            min_seg_idx, max_seg_idx = st.sidebar.slider(
                "Sélectionner une plage de segments",
                0, len(available_segments) - 1,
                (0, min(20, len(available_segments) - 1))
            )
            st.session_state['selected_segments'] = available_segments[min_seg_idx:max_seg_idx + 1]
    else:  # Segments spécifiques
        max_segments = min(30, len(available_segments))
        default_segments = available_segments[:max_segments]
        st.session_state['selected_segments'] = st.sidebar.multiselect(
            "Sélectionner des segments spécifiques",
            available_segments,
            default=default_segments
        )

selected_segments = st.session_state['selected_segments']

# Onglets
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Carte des tracés",
    "🎬 Animation des relais",
    "🔍 Détail d'un tracé",
    "📈 Statistiques",
    "⚙️ Configuration"
])

# -------------------------- TAB 1: Carte des tracés --------------------------
with tab1:
    st.header("Visualisation des tracés")

    display_options = st.sidebar.expander("Options d'affichage", expanded=False)
    with display_options:
        density = st.slider(
            "Densité des points (1 = tous les points)",
            min_value=1, max_value=10, value=3,
            help="Réduire la densité pour améliorer les performances"
        )
        show_markers = st.checkbox(
            "Afficher les marqueurs de début/fin",
            value=True,
            help="Désactiver pour améliorer les performances"
        )
    st.session_state['show_markers'] = show_markers

    st.info(f"Affichage de {len(selected_segments)} segments sur {len(available_segments)} disponibles.")

    with st.spinner("Génération de la carte..."):
        try:
            map_obj = create_optimized_map(traces, selected_segments)
            map_html = map_obj._repr_html_()
            st.session_state['map_data'] = map_html

            st.markdown('<div class="map-container">', unsafe_allow_html=True)
            st.components.v1.html(map_html, height=600, scrolling=False)
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("🔄 Rafraîchir la carte"):
                st.experimental_rerun()

        except Exception as e:
            st.error(f"Erreur lors de la création de la carte: {str(e)}")

    if st.checkbox("Afficher les statistiques des segments", value=False):
        st.subheader("Informations sur les segments")
        with st.spinner("Calcul des statistiques..."):
            stats_data = []
            for trace in traces:
                if trace['segment'] in selected_segments:
                    if not trace['points'] or len(trace['points']) < 2:
                        continue
                    distance = 0.0
                    for i in range(len(trace['points']) - 1):
                        lat1, lon1 = trace['points'][i]
                        lat2, lon2 = trace['points'][i + 1]
                        R = 6371
                        dLat = math.radians(lat2 - lat1)
                        dLon = math.radians(lon2 - lon1)
                        a = math.sin(dLat / 2) * math.sin(dLat / 2) + \
                            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
                            math.sin(dLon / 2) * math.sin(dLon / 2)
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                        dist_segment = R * c
                        distance += dist_segment
                    stats_data.append({
                        'Segment': trace['segment'],
                        'Points': len(trace['points']),
                        'Distance (km)': round(distance, 2)
                    })

            if stats_data:
                st.dataframe(pd.DataFrame(stats_data), use_container_width=True)
            else:
                st.info("Aucune statistique disponible pour les segments sélectionnés.")


# -------------------------- TAB 2: Animation --------------------------
with tab2:
    st.header("Animation des passages de relais")
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 15px;'>
    Cette animation montre l'enchaînement des segments, avec un passage de relais virtuel.
    Pour des raisons de performance, l'animation utilise un nombre réduit de points.
    Utilisez les boutons Play, Pause et Reset pour contrôler l'animation.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        animation_speed = st.slider(
            "Vitesse d'animation (ms)",
            min_value=50,
            max_value=500,
            value=st.session_state.get('animation_speed', 100),
            step=10,
            help="Contrôle la vitesse de l'animation (ms entre deux points)"
        )
        st.session_state['animation_speed'] = animation_speed
    
    # Filtrer les traces selon les segments sélectionnés
    filtered_traces = [t for t in traces if t['segment'] in selected_segments]
    
    if not filtered_traces:
        st.warning("Aucun segment sélectionné pour l'animation. Veuillez sélectionner au moins un segment dans les filtres.")
    else:
        with st.spinner("Préparation de l'animation..."):
            animation_html = create_animation_html(filtered_traces, len(filtered_traces))
            st.session_state['animation_data'] = animation_html

            st.markdown('<div class="map-container">', unsafe_allow_html=True)
            st.components.v1.html(animation_html, height=600, scrolling=False)
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("🔄 Rafraîchir l'animation"):
                st.experimental_rerun()

        st.info(f"L'animation montre {len(filtered_traces)} segments filtrés sur {len(traces)} au total.")


# -------------------------- TAB 3: Détail d'un tracé --------------------------
with tab3:
    st.header("Détail d'un tracé")
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 15px;'>
    Visualisez un tracé spécifique en détail et exportez-le vers Google Maps ou téléchargez-le au format GPX.
    </div>
    """, unsafe_allow_html=True)

    segment_to_view = st.selectbox(
        "Sélectionner un segment à visualiser",
        [t['segment'] for t in traces],
        format_func=lambda x: f"Segment {x}"
    )
    selected_trace = next((t for t in traces if t['segment'] == segment_to_view), None)

    if selected_trace:
        st.session_state['segment_animation_speed'] = st.slider(
            "Vitesse d'animation du segment (ms)",
            min_value=10,
            max_value=500,
            value=st.session_state.get('segment_animation_speed', 100),
            step=10,
            help="Contrôle la vitesse de l'animation (ms entre deux points)"
        )
        
        tabs = st.tabs(["📊 Informations", "🎬 Animation", "🗺️ Carte statique"])
        
        with tabs[0]:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader(f"Segment {selected_trace['segment']}")
                if selected_trace['points'] and len(selected_trace['points']) >= 2:
                    distance = 0.0
                    for i in range(len(selected_trace['points']) - 1):
                        lat1, lon1 = selected_trace['points'][i]
                        lat2, lon2 = selected_trace['points'][i + 1]
                        R = 6371
                        dLat = math.radians(lat2 - lat1)
                        dLon = math.radians(lon2 - lon1)
                        a = math.sin(dLat/2) * math.sin(dLat/2) + \
                            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
                            math.sin(dLon/2) * math.sin(dLon/2)
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                        dist_segment = R * c
                        distance += dist_segment

                    st.metric("Distance", f"{distance:.2f} km")
                    st.metric("Nombre de points", len(selected_trace['points']))
                    start_point = selected_trace['points'][0]
                    end_point = selected_trace['points'][-1]

                    st.markdown(f"**Point de départ:** {start_point[0]:.6f}, {start_point[1]:.6f}")
                    st.markdown(f"**Point d'arrivée:** {end_point[0]:.6f}, {end_point[1]:.6f}")

                    st.markdown("### Export")
                    gmaps_url = generate_google_maps_link(selected_trace['points'])
                    st.markdown(
                        f'<a href="{gmaps_url}" class="export-btn" target="_blank">🗺️ Ouvrir dans Google Maps</a>',
                        unsafe_allow_html=True
                    )

                    gpx_content = export_to_gpx(selected_trace)
                    if gpx_content:
                        download_link = generate_download_link(
                            gpx_content,
                            f"segment_{selected_trace['segment']}.gpx",
                            "📥 Télécharger le fichier GPX"
                        )
                        st.markdown(download_link, unsafe_allow_html=True)
                else:
                    st.warning("Ce segment ne contient pas suffisamment de points pour calculer des statistiques.")

            with col2:
                segment_map = create_single_segment_map(selected_trace)
                st.markdown('<div class="map-container">', unsafe_allow_html=True)
                folium_static(segment_map, width=600, height=500)
                st.markdown('</div>', unsafe_allow_html=True)
                
        with tabs[1]:
            st.subheader("Animation du tracé")
            if selected_trace['points'] and len(selected_trace['points']) >= 2:
                with st.spinner("Préparation de l'animation du segment..."):
                    segment_animation_html = create_segment_animation_html(selected_trace)
                    st.markdown('<div class="map-container">', unsafe_allow_html=True)
                    st.components.v1.html(segment_animation_html, height=600, scrolling=False)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.info(f"Animation basée sur les {len(selected_trace['points'])} points du segment {selected_trace['segment']}.")
                    
                    if len(selected_trace['points']) > 500:
                        st.warning(f"Ce segment contient beaucoup de points ({len(selected_trace['points'])}). L'animation peut être lente sur certains appareils.")
            else:
                st.warning("Ce segment ne contient pas suffisamment de points pour l'animation.")
                
        with tabs[2]:
            st.subheader("Carte statique")
            segment_map = create_single_segment_map(selected_trace)
            st.markdown('<div class="map-container">', unsafe_allow_html=True)
            folium_static(segment_map, width=800, height=600)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.error(f"Segment {segment_to_view} introuvable dans les traces.")


# -------------------------- TAB 4: Statistiques --------------------------
with tab4:
    st.header("📈 Statistiques détaillées")
    with st.spinner("Calcul des statistiques..."):
        total_segments = len(traces)
        total_points = sum(len(t['points']) for t in traces)
        total_distance = 0
        segment_distances = []

        for trace in traces:
            if trace['points'] and len(trace['points']) >= 2:
                distance = 0
                for i in range(len(trace['points']) - 1):
                    lat1, lon1 = trace['points'][i]
                    lat2, lon2 = trace['points'][i + 1]
                    R = 6371
                    dLat = math.radians(lat2 - lat1)
                    dLon = math.radians(lon2 - lon1)
                    a = math.sin(dLat/2) * math.sin(dLat/2) + \
                        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
                        math.sin(dLon/2) * math.sin(dLon/2)
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    dist = R * c
                    distance += dist
                segment_distances.append(distance)
                total_distance += distance

        avg_distance = total_distance / total_segments if total_segments > 0 else 0
        max_distance = max(segment_distances) if segment_distances else 0
        min_distance = min(segment_distances) if segment_distances else 0

    st.markdown("<h3 style='text-align: center;'>Statistiques globales</h3>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class='stat-card'>
                <h3>Segments</h3>
                <p>{total_segments}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"""
            <div class='stat-card'>
                <h3>Distance totale</h3>
                <p>{total_distance:.2f} km</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f"""
            <div class='stat-card'>
                <h3>Distance moyenne</h3>
                <p>{avg_distance:.2f} km</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            f"""
            <div class='stat-card'>
                <h3>Points totaux</h3>
                <p>{total_points}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.subheader("Distribution des distances par segment")
    stats_df = pd.DataFrame({
        'Segment': [t['segment'] for t in traces],
        'Points': [len(t['points']) for t in traces],
        'Distance (km)': segment_distances if segment_distances else [0]*len(traces)
    })
    st.bar_chart(stats_df.set_index('Segment')['Distance (km)'])

    st.subheader("Données détaillées par segment")
    st.dataframe(stats_df, use_container_width=True)

    csv = stats_df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'data:file/csv;base64,{b64}'
    st.markdown(
        f'<a href="{href}" download="paris_run_stats.csv" class="export-btn">📥 Télécharger les statistiques (CSV)</a>',
        unsafe_allow_html=True
    )


# -------------------------- TAB 5: Configuration --------------------------
with tab5:
    st.header("⚙️ Configuration avancée")
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 15px;'>
    Paramètres avancés pour personnaliser l'application et optimiser les performances.
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Performance")
    col1, col2 = st.columns(2)
    with col1:
        cache_ttl = st.number_input(
            "Durée de validité du cache (secondes)",
            min_value=60,
            max_value=86400,
            value=3600,
            step=300,
            help="Durée pendant laquelle les données restent en cache avant d'être rechargées"
        )
    with col2:
        max_workers = st.slider(
            "Nombre max de processus parallèles",
            min_value=1,
            max_value=16,
            value=4,
            help="Contrôle le nombre de tâches exécutées en parallèle"
        )

    st.subheader("Affichage")
    col1, col2 = st.columns(2)
    with col1:
        line_thickness = st.slider(
            "Épaisseur des lignes",
            min_value=1,
            max_value=10,
            value=3,
            help="Épaisseur des tracés sur la carte"
        )

    st.subheader("Gestion du cache")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Vider le cache complet"):
            for file in CACHE_DIR.glob("*.pkl"):
                try:
                    file.unlink()
                except Exception as e:
                    st.error(f"Erreur lors de la suppression du cache: {str(e)}")
            st.cache_data.clear()
            st.success("Cache vidé avec succès!")

    with col2:
        if st.button("🔄 Recharger toutes les données"):
            st.cache_data.clear()
            st.success("Cache Streamlit vidé, les données seront rechargées au prochain accès.")
            st.experimental_rerun()

    st.subheader("À propos")
    st.info("""
    **Paris Run Visualizer** - Version 1.1.0

    Application développée pour visualiser, analyser et optimiser les traces de course à pied sur Paris.

    Pour toute question ou suggestion d'amélioration, contactez l'administrateur.
    """)
