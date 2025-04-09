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
)

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
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# CACHE ET OPTIMISATION
# ----------------------------------------------------------

# Répertoire de cache
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# Clé de session pour garantir la persistance entre les rechargements
if 'session_id' not in st.session_state:
    st.session_state['session_id'] = str(time.time())
    
# Stockage en session pour les cartes et animations
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

# ----------------------------------------------------------
# FONCTIONS UTILES
# ----------------------------------------------------------

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
    
    # Vérifier si le répertoire existe
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
    
    # Utilisation de ThreadPoolExecutor pour paralléliser le chargement
    def process_gpx_file(gpx_file):
        try:
            with open(gpx_file, 'r') as f:
                gpx = gpxpy.parse(f)
                track_points = []
                for track in gpx.tracks:
                    for segment in track.segments:
                        # Optimisation: échantillonner les points si trop nombreux
                        points = segment.points
                        if len(points) > 500:  # Si plus de 500 points, échantillonner
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
    
    # Traitement parallèle
    with concurrent.futures.ThreadPoolExecutor() as executor:
        all_traces = list(executor.map(process_gpx_file, gpx_files))
    
    # Trier par numéro de segment
    all_traces = [t for t in all_traces if t is not None]
    all_traces.sort(key=lambda x: x['segment'])
    
    # Mettre en cache
    save_to_cache(all_traces, cache_key)
    
    return all_traces

# Fonction pour charger tous les points originaux d'un fichier GPX (non échantillonnés)
def load_gpx_file_full(file_path):
    try:
        with open(file_path, 'r') as f:
            gpx = gpxpy.parse(f)
            track_points = []
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        track_points.append((point.latitude, point.longitude, 
                                            point.elevation, point.time))
            
            return track_points
    except Exception as e:
        st.error(f"Erreur lors du chargement de {file_path}: {str(e)}")
        return []

def generate_color_palette(n):
    """
    Génère une palette de n couleurs distinctes.
    """
    if n <= 0:
        return []
    color_list = list(plt.cm.rainbow(np.linspace(0, 1, max(1, n))))
    return [mcolors.rgb2hex(color) for color in color_list]

@st.cache_data(ttl=3600)
def convert_to_geojson(traces, selected_segments=None):
    """Convertit les traces en GeoJSON pour un rendu plus efficace"""
    if not traces:
        return {"type": "FeatureCollection", "features": []}
        
    if selected_segments is None or len(selected_segments) == 0:
        selected_segments = [trace['segment'] for trace in traces]
    
    features = []
    
    for trace in traces:
        if trace['segment'] in selected_segments:
            if not trace['points'] or len(trace['points']) < 2:
                continue
                
            # Créer un LineString à partir des points (longitude, latitude)
            coords = [(p[1], p[0]) for p in trace['points']]  # Inverser lat/lon pour GeoJSON
            
            try:
                line = LineString(coords)
                
                # Créer une feature GeoJSON directement sans passer par __geo_interface__
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
                st.error(f"Erreur lors de la création du GeoJSON pour le segment {trace['segment']}: {str(e)}")
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return geojson

def create_single_segment_map(trace, with_markers=True):
    """
    Crée une carte pour un segment spécifique
    """
    if not trace or not trace.get('points'):
        return folium.Map(location=[48.8566, 2.3522], zoom_start=12)
    
    points = trace['points']
    center_lat = sum(p[0] for p in points) / len(points)
    center_lon = sum(p[1] for p in points) / len(points)
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, 
                  tiles="CartoDB positron")
    
    # Ajouter la ligne du tracé
    folium.PolyLine(
        points,
        color='blue',
        weight=5,
        opacity=0.8,
        tooltip=f"Segment {trace['segment']}"
    ).add_to(m)
    
    if with_markers and points:
        # Ajouter des marqueurs pour le début et la fin
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
    
    # Ajouter un contrôle de mesure de distance
    folium.plugins.MeasureControl(position='bottomleft', primary_length_unit='kilometers').add_to(m)
    
    return m

def create_optimized_map(traces, selected_segments=None):
    """
    Crée une carte Folium optimisée pour de grandes quantités de données
    en utilisant le rendu côté client via GeoJSON et des techniques de cluster.
    """
    if not traces:
        # Carte par défaut centrée sur Paris si pas de traces
        m = folium.Map(location=[48.8566, 2.3522], zoom_start=12, 
                     tiles="CartoDB positron")
        return m
        
    if selected_segments is None or len(selected_segments) == 0:
        selected_segments = [trace['segment'] for trace in traces]
    
    # Calculer le centre de la carte
    all_points = []
    for trace in traces:
        if trace['segment'] in selected_segments and trace['points']:
            # Prendre seulement quelques points pour le calcul du centre
            sample_points = trace['points'][:1] + trace['points'][-1:]
            all_points.extend(sample_points)
    
    if not all_points:
        center_lat, center_lon = 48.8566, 2.3522  # Paris par défaut
    else:
        center_lat = sum(p[0] for p in all_points) / len(all_points)
        center_lon = sum(p[1] for p in all_points) / len(all_points)
    
    # Créer la carte avec folium standard au lieu de leafmap
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, 
                 tiles="CartoDB positron")
    
    # Convertir les traces en GeoJSON
    geojson_data = convert_to_geojson(traces, selected_segments)
    
    if not geojson_data["features"]:
        st.warning("Aucune trace à afficher pour les segments sélectionnés.")
        return m
    
    # Créer une palette de couleurs
    n_segments = len([t for t in traces if t['segment'] in selected_segments])
    if n_segments > 0:
        colormap = cm.linear.YlOrRd_09.scale(1, max(1, n_segments))
        
        # Ajouter le GeoJSON à la carte avec des options de style
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
    
    # Ajouter des marqueurs pour les débuts et fins de segments importants
    show_markers = st.session_state.get('show_markers', True)
    if show_markers and len(selected_segments) <= 30:  # Limiter le nombre de marqueurs pour la performance
        for trace in traces:
            if trace['segment'] in selected_segments and trace['points']:
                # Début du segment
                folium.Marker(
                    location=trace['points'][0],
                    popup=f"Début segment {trace['segment']}",
                    tooltip=f"Début - Segment {trace['segment']}",
                    icon=folium.Icon(color='green', icon='play', prefix='fa', icon_size=(15, 15))
                ).add_to(m)
                
                # Fin du segment
                folium.Marker(
                    location=trace['points'][-1],
                    popup=f"Fin segment {trace['segment']}",
                    tooltip=f"Fin - Segment {trace['segment']}",
                    icon=folium.Icon(color='red', icon='stop', prefix='fa', icon_size=(15, 15))
                ).add_to(m)
    
    # Ajouter contrôle de couches et échelle
    folium.LayerControl().add_to(m)
    folium.plugins.MeasureControl(position='bottomleft', primary_length_unit='kilometers').add_to(m)
    
    return m

# Fonction pour générer un lien Google Maps à partir des points GPS
def generate_google_maps_link(points):
    if not points:
        return "#"
    
    # Prendre un échantillon de points pour ne pas dépasser la limite d'URL
    max_points = 100
    if len(points) > max_points:
        step = len(points) // max_points + 1
        points = points[::step]
    
    # Construire l'URL
    coords_str = "|".join(f"{p[0]},{p[1]}" for p in points)
    base_url = "https://www.google.com/maps/dir/?api=1&origin={},{}&destination={},{}&waypoints={}&travelmode=walking"
    
    start = points[0]
    end = points[-1]
    
    # Les waypoints sont tous les points sauf le début et la fin
    waypoints = []
    if len(points) > 2:
        waypoints = points[1:-1]
    
    waypoints_str = ""
    if waypoints:
        waypoints_str = "|".join(f"{p[0]},{p[1]}" for p in waypoints)
    
    url = base_url.format(
        start[0], start[1],  # origin
        end[0], end[1],      # destination
        waypoints_str         # waypoints
    )
    
    return url

def export_to_gpx(trace):
    """Exporte les données d'un segment au format GPX"""
    if not trace or not trace.get('points'):
        return None
    
    # Créer un nouveau fichier GPX
    gpx = gpxpy.gpx.GPX()
    
    # Créer un nouveau segment
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    
    # Créer un nouveau segment dans la trace
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    
    # Ajouter tous les points au segment
    for point in trace['points']:
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(point[0], point[1]))
    
    return gpx.to_xml()

def generate_download_link(content, filename, link_text):
    """Génère un lien de téléchargement pour un contenu donné"""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'data:text/gpx;base64,{b64}'
    return f'<a href="{href}" download="{filename}" class="export-btn">{link_text}</a>'

def create_animation_html(traces, max_segments=10, width=800, height=600):
    """
    Crée une animation directement visible dans l'interface
    """
    if not traces:
        return """
        <div style="text-align:center;padding:20px;background-color:#f8f9fa;border-radius:5px;">
            <p>Aucune trace disponible pour l'animation</p>
        </div>
        """
    
    limited_traces = traces[:min(max_segments, len(traces))]
    
    # Générer un HTML avec les contrôles d'animation
    html = """
    <!DOCTYPE html>
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
            // Initialiser la carte
            var map = L.map('map').setView([48.8566, 2.3522], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);
            
            // Définir les traces
            var traces = [
    """
    
    # Ajouter les données des traces au format JSON
    for trace in limited_traces:
        if trace['points']:
            html += f"""
                {{
                    segment: {trace['segment']},
                    points: {json.dumps(trace['points'])}
                }},
            """
    
    html += """
            ];
            
            // Variables de contrôle de l'animation
            var animationId;
            var currentSegmentIndex = 0;
            var currentPointIndex = 0;
            var speed = 100; // ms entre chaque point
            var isPlaying = false;
            
            // Créer une palette de couleurs
            function generateColors(n) {
                var colors = [];
                for (var i = 0; i < n; i++) {
                    var h = (i * 360 / n) % 360;
                    colors.push(`hsl(${h}, 70%, 50%)`);
                }
                return colors;
            }
            
            var colors = generateColors(traces.length);
            var completedPaths = [];
            var currentPath = null;
            
            // Éléments HTML
            var progressBar = document.getElementById('progress-bar');
            var infoBox = document.getElementById('info');
            
            // Centrer la carte sur l'ensemble des points
            function centerMap() {
                if (traces.length === 0) return;
                
                var allLats = [];
                var allLngs = [];
                
                traces.forEach(function(trace) {
                    trace.points.forEach(function(point) {
                        allLats.push(point[0]);
                        allLngs.push(point[1]);
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
            
            // Initialiser l'animation
            function initAnimation() {
                centerMap();
                resetAnimation();
            }
            
            // Réinitialiser l'animation
            function resetAnimation() {
                if (animationId) {
                    clearTimeout(animationId);
                }
                
                isPlaying = false;
                currentSegmentIndex = 0;
                currentPointIndex = 0;
                
                // Effacer tous les tracés
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
            
            // Fonction d'animation
            function animate() {
                if (currentSegmentIndex >= traces.length) {
                    isPlaying = false;
                    infoBox.textContent = 'Animation terminée';
                    return;
                }
                
                var currentTrace = traces[currentSegmentIndex];
                var points = currentTrace.points;
                
                if (currentPointIndex === 0) {
                    // Début d'un nouveau segment
                    if (currentPath) {
                        // Sauvegarder le tracé précédent
                        completedPaths.push(currentPath);
                    }
                    
                    currentPath = L.polyline([], {
                        color: colors[currentSegmentIndex % colors.length],
                        weight: 4
                    }).addTo(map);
                }
                
                // Ajouter le point actuel au tracé
                currentPath.addLatLng(points[currentPointIndex]);
                
                // Centrer la carte sur le point actuel
                map.panTo(points[currentPointIndex]);
                
                // Mettre à jour la barre de progression
                var totalPoints = traces.reduce((sum, t) => sum + t.points.length, 0);
                var pointsProcessed = traces.slice(0, currentSegmentIndex).reduce((sum, t) => sum + t.points.length, 0) + currentPointIndex;
                var progress = (pointsProcessed / totalPoints) * 100;
                progressBar.style.width = progress + '%';
                
                // Mettre à jour l'info
                infoBox.textContent = `Segment: ${currentTrace.segment} - Point: ${currentPointIndex+1}/${points.length}`;
                
                // Passer au point suivant
                currentPointIndex++;
                
                // Si on a terminé ce segment, passer au suivant
                if (currentPointIndex >= points.length) {
                    currentSegmentIndex++;
                    currentPointIndex = 0;
                }
                
                // Continue l'animation si on est en mode lecture
                if (isPlaying) {
                    animationId = setTimeout(animate, speed);
                }
            }
            
            // Événements des boutons
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
            
            // Initialisation
            initAnimation();
        </script>
    </body>
    </html>
    """
    
    return html

# Titre principal
st.title('🏃‍♂️ Visualisation des Traces de Paris Run')

# Charger les fichiers GPX
gpx_dirs = {
    "Relais GPX par défaut": "Relais_gpx_dp",
    "Relais GPX glouton": "Relais_gpx_greedy", 
    "Relais GPX optimisés": "Relais_gpx_optimized",
    "Relais GPX original": "Relais_gpx"
}

# Vérifier quels dossiers existent réellement
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

# Afficher un message pendant le chargement des données
with st.spinner('Chargement des données GPX...'):
    traces = load_all_gpx_files(gpx_directory)

if not traces:
    st.error(f"Aucune donnée GPX disponible dans le dossier {gpx_directory}")
    st.stop()

# Création d'onglets
tab1, tab2, tab3 = st.tabs(["📊 Carte des tracés", "🎬 Animation des relais", "🔍 Détail d'un tracé"])

with tab1:
    st.header("Visualisation des tracés")
    
    # Options d'affichage
    display_options = st.sidebar.expander("Options d'affichage", expanded=False)
    with display_options:
        density = st.slider("Densité des points (1 = tous les points)", 
                         min_value=1, max_value=10, value=3, 
                         help="Réduire la densité pour améliorer les performances")
        
        show_markers = st.checkbox("Afficher les marqueurs de début/fin", value=True,
                               help="Désactiver pour améliorer les performances")
        # Stocker dans session state
        st.session_state['show_markers'] = show_markers
    
    # Sidebar pour sélectionner les segments
    st.sidebar.header("Filtres")
    filter_mode = st.sidebar.radio("Mode de sélection des segments", 
                                  ["Tous les segments", "Plage de segments", "Segments spécifiques"])
    
    # Liste des numéros de segments disponibles (pour éviter les problèmes de segments manquants)
    available_segments = [t['segment'] for t in traces]
    
    if not available_segments:
        st.warning("Pas de segments disponibles dans les fichiers GPX")
        selected_segments = []
    else:
        if filter_mode == "Tous les segments":
            # Limiter le nombre total pour les performances
            max_display = st.sidebar.slider("Nombre max de segments à afficher", 
                                        min_value=10, max_value=len(available_segments), 
                                        value=min(50, len(available_segments)))
            selected_segments = available_segments[:max_display]
        elif filter_mode == "Plage de segments":
            min_seg_idx = 0
            max_seg_idx = min(20, len(available_segments) - 1)
            
            min_seg_idx, max_seg_idx = st.sidebar.slider(
                "Sélectionner une plage de segments", 
                0, len(available_segments) - 1, 
                (min_seg_idx, max_seg_idx),
                format="%d"
            )
            
            selected_segments = available_segments[min_seg_idx:max_seg_idx + 1]
        else:  # Segments spécifiques
            # Option pour sélectionner des segments spécifiques
            max_segments = min(30, len(available_segments))
            default_segments = available_segments[:max_segments]
            selected_segments = st.sidebar.multiselect(
                "Sélectionner des segments spécifiques", 
                available_segments,
                default=default_segments
            )
    
    st.info(f"Affichage de {len(selected_segments)} segments sur {len(available_segments)} segments disponibles.")
    
    # Créer la carte optimisée
    with st.spinner("Génération de la carte..."):
        try:
            map_obj = create_optimized_map(traces, selected_segments)
            # Sauvegarder le HTML de la carte
            map_html = map_obj._repr_html_()
            st.session_state['map_data'] = map_html
            
            # Afficher la carte avec div encapsulante pour styling
            st.markdown('<div class="map-container">', unsafe_allow_html=True)
            st.components.v1.html(map_html, height=600, scrolling=False)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Bouton pour rafraîchir la carte
            if st.button("🔄 Rafraîchir la carte"):
                st.experimental_rerun()
                
        except Exception as e:
            st.error(f"Erreur lors de la création de la carte: {str(e)}")

    # Infos additionnelles
    if st.checkbox("Afficher les statistiques des segments", value=False):
        st.subheader("Informations sur les segments")
        
        with st.spinner("Calcul des statistiques..."):
            stats_data = []
            for trace in traces:
                if trace['segment'] in selected_segments:
                    if not trace['points'] or len(trace['points']) < 2:
                        continue
                        
                    distance = 0.0
                    for i in range(len(trace['points'])-1):
                        lat1, lon1 = trace['points'][i]
                        lat2, lon2 = trace['points'][i+1]
                        # Formule de Haversine pour une meilleure précision
                        R = 6371  # Rayon de la Terre en km
                        dLat = math.radians(lat2 - lat1)
                        dLon = math.radians(lon2 - lon1)
                        a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) \
                            * math.cos(math.radians(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
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

with tab2:
    st.header("Animation des passages de relais")
    
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 15px;'>
    Cette animation montre l'enchaînement des segments, avec un passage de relais virtuel.
    Pour des raisons de performance, l'animation utilise un nombre réduit de points.
    Utilisez les boutons Play, Pause et Reset pour contrôler l'animation.
    </div>
    """, unsafe_allow_html=True)
    
    # Options pour l'animation
    col1, col2 = st.columns(2)
    with col1:
        available_anim_segments = min(len(traces), 30)  # Limiter pour la performance
        max_anim_segments = st.slider(
            "Nombre de segments à animer", 
            min_value=2, 
            max_value=available_anim_segments, 
            value=min(10, available_anim_segments),
            key="anim_segments_slider"
        )
    
    with st.spinner("Préparation de l'animation..."):
        # Créer l'animation interactive avec contrôles
        animation_html = create_animation_html(traces, max_anim_segments)
        st.session_state['animation_data'] = animation_html
        
        # Afficher l'animation
        st.markdown('<div class="map-container">', unsafe_allow_html=True)
        st.components.v1.html(animation_html, height=600, scrolling=False)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Bouton pour rafraîchir l'animation
        if st.button("🔄 Rafraîchir l'animation"):
            st.experimental_rerun()
    
    st.info(f"L'animation montre {max_anim_segments} segments sur {len(traces)} au total.")

with tab3:
    st.header("Détail d'un tracé")
    
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 15px;'>
    Visualisez un tracé spécifique en détail et exportez-le vers Google Maps ou téléchargez-le au format GPX.
    </div>
    """, unsafe_allow_html=True)
    
    # Sélection du segment à afficher
    segment_to_view = st.selectbox(
        "Sélectionner un segment à visualiser",
        available_segments,
        format_func=lambda x: f"Segment {x}"
    )
    
    # Trouver la trace correspondante
    selected_trace = next((t for t in traces if t['segment'] == segment_to_view), None)
    
    if selected_trace:
        # Afficher les informations sur le segment
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(f"Segment {selected_trace['segment']}")
            
            # Calculer les statistiques du segment
            if selected_trace['points'] and len(selected_trace['points']) >= 2:
                # Distance totale du segment
                distance = 0.0
                for i in range(len(selected_trace['points'])-1):
                    lat1, lon1 = selected_trace['points'][i]
                    lat2, lon2 = selected_trace['points'][i+1]
                    # Formule de Haversine
                    R = 6371  # Rayon de la Terre en km
                    dLat = math.radians(lat2 - lat1)
                    dLon = math.radians(lon2 - lon1)
                    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) \
                        * math.cos(math.radians(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    dist_segment = R * c
                    distance += dist_segment
                
                st.metric("Distance", f"{distance:.2f} km")
                st.metric("Nombre de points", len(selected_trace['points']))
                
                # Coordonnées de départ et d'arrivée
                start_point = selected_trace['points'][0]
                end_point = selected_trace['points'][-1]
                
                st.markdown(f"**Point de départ:** {start_point[0]:.6f}, {start_point[1]:.6f}")
                st.markdown(f"**Point d'arrivée:** {end_point[0]:.6f}, {end_point[1]:.6f}")
                
                # Boutons d'export
                st.markdown("### Export")
                
                # Générer le lien Google Maps
                gmaps_url = generate_google_maps_link(selected_trace['points'])
                st.markdown(f'<a href="{gmaps_url}" class="export-btn" target="_blank">🗺️ Ouvrir dans Google Maps</a>', unsafe_allow_html=True)
                
                # Générer le lien de téléchargement GPX
                gpx_content = export_to_gpx(selected_trace)
                if gpx_content:
                    download_link = generate_download_link(gpx_content, f"segment_{selected_trace['segment']}.gpx", "📥 Télécharger le fichier GPX")
                    st.markdown(download_link, unsafe_allow_html=True)
            else:
                st.warning("Ce segment ne contient pas suffisamment de points pour calculer des statistiques.")
                
        with col2:
            # Afficher la carte du segment
            segment_map = create_single_segment_map(selected_trace)
            st.markdown('<div class="map-container">', unsafe_allow_html=True)
            folium_static(segment_map, width=600, height=500)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.error(f"Segment {segment_to_view} introuvable dans les traces.")

# Ajouter des informations sur l'optimisation
st.sidebar.markdown("---")
st.sidebar.markdown("""
### Informations sur les performances
- Utilisation du cache pour accélérer le chargement
- Les tracés sont échantillonnés pour améliorer la fluidité
- L'interface utilise GeoJSON pour un rendu plus rapide
""")

# Bouton pour vider le cache
if st.sidebar.button("Vider le cache"):
    for file in CACHE_DIR.glob("*.pkl"):
        try:
            file.unlink()
        except Exception as e:
            st.sidebar.error(f"Erreur lors de la suppression du cache: {str(e)}")
    
    # Vider aussi le cache streamlit
    st.cache_data.clear()
    st.sidebar.success("Cache vidé avec succès!")
