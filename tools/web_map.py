# tools/web_map.py - Веб-карта с траекторией и радаром (ИСПРАВЛЕННАЯ)

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template_string
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
import threading

# === НАСТРОЙКИ ===
MQTT_HOST = "localhost"
MQTT_PORT = 1883
TOPIC_GPS = "sensors/nmea/raw"
TOPIC_RADAR = "sensors/radar/targets"
MAP_CENTER = [59.95, 30.05]
MAP_ZOOM = 9
RADAR_RANGE_NM = 12.0

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sensor-bridge-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

ship_data = {
    "own_ship": None,
    "targets": {},
    "all_traffic": {},
    "trajectory": []
}

# === HTML ШАБЛОН (упрощённый и исправленный) ===
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SensorBridge - Live Map</title>
    <meta charset="utf-8">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
        #map { height: 100vh; width: 100%; }
        #info {
            position: absolute; top: 10px; right: 10px;
            background: white; padding: 15px; border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2); z-index: 1000;
            min-width: 250px; max-height: 90vh; overflow-y: auto;
        }
        .stat { margin: 5px 0; font-size: 14px; }
        .stat-label { color: #666; }
        .stat-value { font-weight: bold; color: #007bff; }
        .target-list { margin-top: 10px; }
        .target-item { padding: 5px; border-bottom: 1px solid #eee; font-size: 13px; }
        .mode-switch {
            position: absolute; top: 10px; left: 10px;
            background: white; padding: 10px; border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2); z-index: 1000;
        }
        .mode-btn {
            padding: 8px 12px; margin: 5px 0; border: none;
            border-radius: 4px; cursor: pointer; font-size: 13px; width: 100%;
        }
        .mode-btn.active { background: #007bff; color: white; }
        .legend {
            position: absolute; bottom: 30px; left: 10px;
            background: white; padding: 10px; border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2); z-index: 1000; font-size: 13px;
        }
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div class="mode-switch">
        <h4 style="margin: 0 0 10px 0;">👁 Режим</h4>
        <button class="mode-btn active" id="btnShip" onclick="setMode('ship')">🚢 С судна</button>
        <button class="mode-btn" id="btnObserver" onclick="setMode('observer')">🛰 Наблюдатель</button>
    </div>
    
    <div id="info">
        <h3>🚢 SensorBridge</h3>
        <div class="stat"><span class="stat-label">Широта:</span><span class="stat-value" id="lat">-</span></div>
        <div class="stat"><span class="stat-label">Долгота:</span><span class="stat-value" id="lon">-</span></div>
        <div class="stat"><span class="stat-label">Курс:</span><span class="stat-value" id="course">-</span></div>
        <div class="stat"><span class="stat-label">Скорость:</span><span class="stat-value" id="speed">-</span></div>
        <div class="stat"><span class="stat-label">Целей:</span><span class="stat-value" id="targets">0</span></div>
        <div class="target-list" id="targetList"></div>
    </div>
    
    <div class="legend">
        <div>🚢 Наше судно</div>
        <div>⚓ Цель (радар)</div>
        <div>🔵 Судно (наблюдатель)</div>
        <div>🏭 Порт</div>
        <div>🟢→🔴 Маршрут</div>
        <div>⭕ Радар {{ radar_range }}миль</div>
    </div>
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    
    <script>
        // === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (ОБЪЯВЛЕНЫ СРАЗУ!) ===
        var currentMode = 'ship';
        var ownShipMarker = null;
        var radarCircle = null;
        var trajectoryLine = null;
        var targetMarkers = {};
        var trafficMarkers = {};
        
        var RADAR_RANGE_NM = {{ radar_range }};
        var NM_TO_KM = 1.852;
        
        // === КАРТА ===
        var map = L.map('map').setView([{{ map_center[0] }}, {{ map_center[1] }}], {{ map_zoom }});
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        
        // === ПОРТЫ ===
        var ports = [
            { name: "Кронштадт", lat: 59.9933, lon: 29.7658 },
            { name: "СПб", lat: 59.9343, lon: 30.3351 }
        ];
        ports.forEach(function(p) {
            L.marker([p.lat, p.lon]).addTo(map).bindPopup("🏭 " + p.name);
        });
        
        // === МАРШРУТ ===
        var routeStart = [{{ route_start.lat }}, {{ route_start.lon }}];
        var routeEnd = [{{ route_end.lat }}, {{ route_end.lon }}];
        
        L.marker(routeStart, {icon: L.divIcon({html: '🟢', className: '', iconSize: [25,25]})})
            .addTo(map).bindPopup("🟢 Старт");
        L.marker(routeEnd, {icon: L.divIcon({html: '🔴', className: '', iconSize: [25,25]})})
            .addTo(map).bindPopup("🔴 Финиш");
        L.polyline([routeStart, routeEnd], {color: 'purple', dashArray: '10, 10'})
            .addTo(map).bindPopup("📍 Маршрут");
        
        // === РЕЖИМЫ ===
        function setMode(mode) {
            currentMode = mode;
            document.getElementById('btnShip').classList.toggle('active', mode === 'ship');
            document.getElementById('btnObserver').classList.toggle('active', mode === 'observer');
            updateDisplay();
        }
        
        function updateDisplay() {
            for (var id in trafficMarkers) {
                if (currentMode === 'observer') {
                    if (!map.hasLayer(trafficMarkers[id])) {
                        trafficMarkers[id].addTo(map);
                    }
                } else {
                    if (map.hasLayer(trafficMarkers[id])) {
                        map.removeLayer(trafficMarkers[id]);
                    }
                }
            }
        }
        
        // === WEBSOCKET ===
        var socket = io();
        
        socket.on('update_data', function(data) {
            // Наше судно
            if (data.own_ship) {
                var pos = [data.own_ship.lat, data.own_ship.lon];
                
                if (ownShipMarker) {
                    ownShipMarker.setLatLng(pos);
                } else {
                    ownShipMarker = L.marker(pos, {
                        icon: L.divIcon({html: '🚢', className: '', iconSize: [30,30]})
                    }).addTo(map);
                    map.setView(pos, 12);
                }
                
                // Круг радара
                if (radarCircle) {
                    radarCircle.setLatLng(pos);
                } else {
                    radarCircle = L.circle(pos, {
                        radius: RADAR_RANGE_NM * NM_TO_KM * 1000,
                        color: '#28a745', fillOpacity: 0.1, weight: 2
                    }).addTo(map);
                }
                
                // Траектория
                if (data.trajectory && data.trajectory.length > 1) {
                    if (trajectoryLine) {
                        trajectoryLine.setLatLngs(data.trajectory);
                    } else {
                        trajectoryLine = L.polyline(data.trajectory, {color: 'blue', weight: 2}).addTo(map);
                    }
                }
                
                // Статистика
                document.getElementById('lat').textContent = data.own_ship.lat.toFixed(6);
                document.getElementById('lon').textContent = data.own_ship.lon.toFixed(6);
                document.getElementById('course').textContent = Math.round(data.own_ship.course) + '°';
                document.getElementById('speed').textContent = data.own_ship.speed.toFixed(1) + ' уз';
            }
            
            // Цели
            document.getElementById('targets').textContent = Object.keys(data.targets || {}).length;
            var targetList = document.getElementById('targetList');
            targetList.innerHTML = '';
            
            // Удаляем старые цели
            for (var id in targetMarkers) {
                if (!data.targets || !data.targets[id]) {
                    map.removeLayer(targetMarkers[id]);
                    delete targetMarkers[id];
                }
            }
            
            // Добавляем цели радара
            if (data.targets) {
                for (var id in data.targets) {
                    var t = data.targets[id];
                    var pos = [t.lat, t.lon];
                    
                    if (targetMarkers[id]) {
                        targetMarkers[id].setLatLng(pos);
                    } else {
                        targetMarkers[id] = L.marker(pos, {
                            icon: L.divIcon({html: '⚓', className: '', iconSize: [25,25]})
                        }).addTo(map).bindPopup("⚓ " + id);
                    }
                    
                    var item = document.createElement('div');
                    item.className = 'target-item';
                    item.innerHTML = "<b>" + id + "</b>: " + t.speed + " уз, " + Math.round(t.course) + "°";
                    targetList.appendChild(item);
                }
            }
            
            // Все суда (наблюдатель)
            if (data.all_traffic) {
                for (var id in data.all_traffic) {
                    if (!data.targets || !data.targets[id]) {
                        var s = data.all_traffic[id];
                        var pos = [s.lat, s.lon];
                        
                        if (trafficMarkers[id]) {
                            trafficMarkers[id].setLatLng(pos);
                        } else {
                            trafficMarkers[id] = L.marker(pos, {
                                icon: L.divIcon({html: '🔵', className: '', iconSize: [25,25]})
                            }).addTo(map);
                            if (currentMode === 'ship') {
                                map.removeLayer(trafficMarkers[id]);
                            }
                        }
                    }
                }
            }
            
            updateDisplay();
        });
    </script>
</body>
</html>
"""


# === MQTT ===
def on_connect(client, userdata, flags, rc):
    print("✅ MQTT подключён")
    client.subscribe(TOPIC_GPS)
    client.subscribe(TOPIC_RADAR)

def on_message(client, userdata, msg):
    try:
        if msg.topic == TOPIC_GPS:
            data = json.loads(msg.payload.decode())
            ship_data["own_ship"] = {
                "lat": data["lat"],
                "lon": data["lon"],
                "course": data.get("course", 0),
                "speed": data.get("speed", 0)
            }
            ship_data["trajectory"].append([data["lat"], data["lon"]])
            if len(ship_data["trajectory"]) > 100:
                ship_data["trajectory"].pop(0)
        
        elif msg.topic == TOPIC_RADAR:
            data = json.loads(msg.payload.decode())
            ship_data["targets"] = {}
            for t in data:
                if "absolute_position" in t:
                    ship_data["targets"][t["id"]] = {
                        "lat": t["absolute_position"]["lat"],
                        "lon": t["absolute_position"]["lon"],
                        "course": t.get("course", 0),
                        "speed": t.get("speed", 0)
                    }
                    ship_data["all_traffic"][t["id"]] = ship_data["targets"][t["id"]]
        
        socketio.emit('update_data', ship_data)
    except Exception as e:
        print(f"❌ Ошибка обработки: {e}")

def mqtt_thread():
    client = mqtt.Client(client_id="web-map", callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_forever()

@app.route('/')
def index():
    return render_template_string(
        HTML_TEMPLATE,
        map_center=MAP_CENTER,
        map_zoom=MAP_ZOOM,
        radar_range=RADAR_RANGE_NM,
        route_start={"lat": 59.9933, "lon": 29.7658, "name": "Кронштадт"},
        route_end={"lat": 59.9343, "lon": 30.3351, "name": "Санкт-Петербург"}
    )

if __name__ == "__main__":
    threading.Thread(target=mqtt_thread, daemon=True).start()
    print("🗺 Карта запущена: http://localhost:5000")
    print("✅ Исправлены: route_start, currentMode, упрощён JS")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)