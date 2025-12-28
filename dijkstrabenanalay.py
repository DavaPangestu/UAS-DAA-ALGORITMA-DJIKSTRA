import csv
import folium
import heapq
import os
import webbrowser
import math
import time
from folium import Element

# ==========================================
# 1. KONFIGURASI & UTILITAS
# ==========================================
def haversine(lat1, lon1, lat2, lon2):
    """Menghitung jarak meter antar koordinat"""
    R = 6371000 
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def get_data_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(os.path.dirname(base_dir), 'data', 'lokasi_200.csv')
    return data_path

def load_locations(csv_path):
    locations = []
    if not os.path.exists(csv_path):
        return []
    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                locations.append({
                    "id": i,
                    "name": row.get("name", f"Posko_{i}"),
                    "lat": float(row["lat"]),
                    "lng": float(row["lng"])
                })
        return locations
    except:
        return []

# ==========================================
# 2. LOGIKA JARIGAN (RADIUS 5KM - ESTAFET)
# ==========================================
def build_network(locations, radius_km=5):
    graph = {loc["id"]: [] for loc in locations}
    n = len(locations)
    limit = radius_km * 1000
    edges = []
    
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine(locations[i]["lat"], locations[i]["lng"],
                          locations[j]["lat"], locations[j]["lng"])
            if d <= limit:
                graph[i].append((j, d))
                graph[j].append((i, d))
                edges.append((i, j))
    return graph, edges

def dijkstra_solver(graph, start):
    dists = {node: float('inf') for node in graph}
    parents = {node: None for node in graph}
    dists[start] = 0.0
    pq = [(0.0, start)]
    
    while pq:
        d, u = heapq.heappop(pq)
        if d > dists[u]: continue
        for v, w in graph[u]:
            if dists[u] + w < dists[v]:
                dists[v] = dists[u] + w
                parents[v] = u
                heapq.heappush(pq, (dists[v], v))
    return dists, parents

def get_route(parents, target):
    path = []
    curr = target
    while curr is not None:
        path.append(curr)
        curr = parents[curr]
    return path[::-1]

# ==========================================
# 3. VISUALISASI TERANG + RADIUS (YANG KAMU SUKA)
# ==========================================
def create_light_map(locations, all_edges, target_path, dist_km, output_name="peta_terang_radius.html"):
    if not locations: return

    posko = locations[0]
    
    # GANTI BACKGROUND JADI TERANG (CartoDB Positron)
    m = folium.Map(location=[posko["lat"], posko["lng"]], 
                   zoom_start=12, tiles="CartoDB positron") 

    # --- A. LAYER JARING (JARINGAN) ---
    # Warnanya Abu-abu agak gelap biar kelihatan di background putih
    for u, v in all_edges:
        p1 = [locations[u]["lat"], locations[u]["lng"]]
        p2 = [locations[v]["lat"], locations[v]["lng"]]
        folium.PolyLine(
            [p1, p2], color="#bdc3c7", weight=1, opacity=0.4
        ).add_to(m)

    # --- B. LAYER RUTE & RADIUS (INI YANG PENTING) ---
    if target_path:
        route_coords = [[locations[i]["lat"], locations[i]["lng"]] for i in target_path]
        
        # 1. GAMBAR LINGKARAN RADIUS (COVERAGE)
        # Warna Kuning/Oranye Transparan di setiap titik jalur
        for node_idx in target_path:
            loc = locations[node_idx]
            folium.Circle(
                location=[loc["lat"], loc["lng"]],
                radius=5000, # 5 KM Radius Real
                color="#f39c12",       # Garis Oranye
                weight=1,
                fill=True,
                fill_color="#f1c40f",  # Isi Kuning
                fill_opacity=0.1,      # Transparan cantik
                popup="Coverage Area: 5 KM"
            ).add_to(m)

        # 2. GAMBAR JALUR UTAMA
        folium.PolyLine(
            route_coords, color="#e67e22", weight=4, opacity=1
        ).add_to(m)

    # --- C. MARKER ---
    target_id = target_path[-1] if target_path else -1
    
    for loc in locations:
        loc_id = loc["id"]
        
        # Start (Merah)
        if loc_id == 0:
            folium.CircleMarker(
                [loc["lat"], loc["lng"]], radius=8, color="#c0392b", fill=True, fill_opacity=1,
                popup="<b>START</b>"
            ).add_to(m)
        # Target (Hijau)
        elif loc_id == target_id:
            folium.CircleMarker(
                [loc["lat"], loc["lng"]], radius=8, color="#27ae60", fill=True, fill_opacity=1,
                popup="<b>TARGET</b>"
            ).add_to(m)
        # Transit (Putih dgn Garis Oranye)
        elif loc_id in target_path:
            folium.CircleMarker(
                [loc["lat"], loc["lng"]], radius=5, color="#d35400", fill=True, fill_color="white", fill_opacity=1,
                popup=f"Transit: {loc['name']}"
            ).add_to(m)
        # Titik Lain (Biru Kalem)
        else:
            folium.CircleMarker(
                [loc["lat"], loc["lng"]], radius=3, color="#2980b9", fill=True, fill_opacity=0.5,
                popup=loc['name']
            ).add_to(m)

    # --- D. DASHBOARD INFO (GAYA BERSIH) ---
    transit_count = len(target_path) - 2 if len(target_path) > 2 else 0
    
    dashboard_html = f"""
    <div style="
        position: fixed; 
        bottom: 30px; left: 30px; width: 280px; 
        background-color: white; 
        border: 2px solid #e67e22; 
        z-index:9999; border-radius: 10px; padding: 15px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        font-family: 'Segoe UI', sans-serif;">
        
        <h4 style="margin:0 0 10px 0; color:#d35400; border-bottom:1px solid #eee; padding-bottom:5px;">
            📍 INFORMASI RUTE
        </h4>
        <div style="font-size: 13px; line-height: 1.6; color:#2c3e50;">
            <b>Status:</b> <span style="background:#2ecc71; color:white; padding:2px 6px; border-radius:4px;">AMAN</span><br>
            <b>Tujuan:</b> {locations[target_id]['name']}<br>
            <b>Total Jarak:</b> {dist_km:.2f} KM<br>
            <b>Posko Transit:</b> {transit_count} Titik<br>
            <i style="color:#7f8c8d; font-size:11px;">*Visualisasi Radius 5KM aktif</i>
        </div>
    </div>
    """
    m.get_root().html.add_child(Element(dashboard_html))

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_name)
    m.save(output_path)
    print(f"✅ Peta Versi Terang + Radius Berhasil: {output_path}")
    webbrowser.open("file://" + output_path)

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("\n=== DIJKSTRA LIGHT MODE + RADIUS ===")
    
    csv_file = get_data_path()
    locs = load_locations(csv_file)
    
    if locs:
        # 1. Build (Radius 5KM - Estafet)
        print("⚙️ Membangun Jaringan...")
        graph, edges = build_network(locs, radius_km=5)
        
        # 2. Target Jauh (Index 55)
        start, target = 0, 55
        if target >= len(locs): target = len(locs) - 1
        
        # 3. Hitung
        print("🚀 Menghitung Rute...")
        dists, parents = dijkstra_solver(graph, start)
        
        if dists[target] != float('inf'):
            path = get_route(parents, target)
            km = dists[target]/1000
            print(f"✅ Rute Ketemu: {km:.2f} km")
            
            # 4. Visualisasi
            create_light_map(locs, edges, path, km)
        else:
            print("❌ Terisolasi.")
