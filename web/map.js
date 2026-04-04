// map.js - Leaflet Map Management

// Global map state
let map = null;
let ownShipMarker = null;
let targetMarkers = {};
let ownShipPosition = null;

// Ship icons (custom SVG markers)
const ownShipIcon = L.divIcon({
    className: 'ship-marker own-ship-icon',
    html: `
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M20 5L25 15L20 20L15 15L20 5Z" fill="#e94560"/>
            <circle cx="20" cy="20" r="15" stroke="#e94560" stroke-width="2" fill="rgba(233,69,96,0.2)"/>
        </svg>
    `,
    iconSize: [40, 40],
    iconAnchor: [20, 20]
});

const targetShipIcon = L.divIcon({
    className: 'ship-marker target-ship-icon',
    html: `
        <svg width="30" height="30" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="15" cy="15" r="8" fill="#4ade80"/>
            <circle cx="15" cy="15" r="12" stroke="#4ade80" stroke-width="1.5" fill="rgba(74,222,128,0.2)"/>
        </svg>
    `,
    iconSize: [30, 30],
    iconAnchor: [15, 15]
});

/**
 * Initialize the map
 */
function initMap(centerLat = 55.751244, centerLon = 37.618423, zoom = 12) {
    // Create map centered on default position (Moscow area for testing)
    map = L.map('map').setView([centerLat, centerLon], zoom);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18
    }).addTo(map);
    
    console.log('🗺️ Map initialized');
}

/**
 * Update own ship position on map
 * @param {Object} data - GPS data from MQTT
 */
function updateOwnShip(data) {
    if (!map) return;
    
    const lat = parseFloat(data.lat);
    const lon = parseFloat(data.lon);
    const course = parseFloat(data.course) || 0;
    const speed = parseFloat(data.speed) || 0;
    
    ownShipPosition = { lat, lon, course, speed };
    
    if (ownShipMarker) {
        // Update existing marker position
        ownShipMarker.setLatLng([lat, lon]);
        
        // Rotate icon based on course
        const rotatedIcon = L.divIcon({
            className: 'ship-marker own-ship-icon',
            html: `
                <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" style="transform: rotate(${course}deg)">
                    <path d="M20 5L25 15L20 20L15 15L20 5Z" fill="#e94560"/>
                    <circle cx="20" cy="20" r="15" stroke="#e94560" stroke-width="2" fill="rgba(233,69,96,0.2)"/>
                </svg>
            `,
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        });
        ownShipMarker.setIcon(rotatedIcon);
        
        // Update popup
        ownShipMarker.setPopupContent(`
            <strong>🚢 Own Ship</strong><br>
            Course: ${course.toFixed(1)}°<br>
            Speed: ${speed.toFixed(1)} kn<br>
            Lat: ${lat.toFixed(6)}<br>
            Lon: ${lon.toFixed(6)}
        `);
    } else {
        // Create new marker
        ownShipMarker = L.marker([lat, lon], { icon: ownShipIcon }).addTo(map);
        ownShipMarker.bindPopup(`
            <strong>🚢 Own Ship</strong><br>
            Course: ${course.toFixed(1)}°<br>
            Speed: ${speed.toFixed(1)} kn
        `);
        
        // Center map on own ship
        map.setView([lat, lon], 12);
    }
    
    console.log(`📍 Own ship updated: ${lat.toFixed(6)}, ${lon.toFixed(6)}`);
}

/**
 * Update target ships on map
 * @param {Array} targets - Array of target data from MQTT
 */
function updateTargets(targets) {
    if (!map) return;
    
    // Track which targets we've seen this update
    const seenTargets = new Set();
    
    targets.forEach(target => {
        const id = target.id;
        seenTargets.add(id);
        
        // Get absolute position if available, otherwise calculate from bearing/distance
        let lat, lon;
        
        if (target.absolute_position && ownShipPosition) {
            lat = target.absolute_position.lat;
            lon = target.absolute_position.lon;
        } else if (ownShipPosition) {
            // Calculate position from bearing and distance
            const bearing = parseFloat(target.bearing) || 0;
            const distance = parseFloat(target.distance) || 0; // in nautical miles
            
            // Convert to approximate lat/lon offset
            const latOffset = (distance * Math.cos(toRadians(bearing))) / 60;
            const lonOffset = (distance * Math.sin(toRadians(bearing))) / (60 * Math.cos(toRadians(ownShipPosition.lat)));
            
            lat = ownShipPosition.lat + latOffset;
            lon = ownShipPosition.lon + lonOffset;
        } else {
            return; // Can't place target without own ship position
        }
        
        if (targetMarkers[id]) {
            // Update existing marker
            targetMarkers[id].setLatLng([lat, lon]);
            
            // Update popup
            targetMarkers[id].setPopupContent(`
                <strong>🎯 Target: ${id}</strong><br>
                Course: ${(target.course || 0).toFixed(1)}°<br>
                Speed: ${(target.speed || 0).toFixed(1)} kn<br>
                Bearing: ${(target.bearing || 0).toFixed(1)}°<br>
                Distance: ${(target.distance || 0).toFixed(2)} NM
            `);
        } else {
            // Create new marker
            targetMarkers[id] = L.marker([lat, lon], { icon: targetShipIcon }).addTo(map);
            targetMarkers[id].bindPopup(`
                <strong>🎯 Target: ${id}</strong><br>
                Course: ${(target.course || 0).toFixed(1)}°<br>
                Speed: ${(target.speed || 0).toFixed(1)} kn
            `);
        }
    });
    
    // Remove targets that are no longer present
    Object.keys(targetMarkers).forEach(id => {
        if (!seenTargets.has(id)) {
            map.removeLayer(targetMarkers[id]);
            delete targetMarkers[id];
            console.log(`🗑️ Target ${id} removed`);
        }
    });
    
    console.log(`🎯 Targets updated: ${targets.length} visible`);
}

/**
 * Clear all target markers
 */
function clearTargets() {
    Object.values(targetMarkers).forEach(marker => {
        if (map.hasLayer(marker)) {
            map.removeLayer(marker);
        }
    });
    targetMarkers = {};
    console.log('🧹 All targets cleared');
}

/**
 * Helper function to convert degrees to radians
 */
function toRadians(degrees) {
    return degrees * Math.PI / 180;
}

/**
 * Fit map bounds to show all ships
 */
function fitMapToShips() {
    if (!map) return;
    
    const latlngs = [];
    
    if (ownShipPosition) {
        latlngs.push([ownShipPosition.lat, ownShipPosition.lon]);
    }
    
    Object.values(targetMarkers).forEach(marker => {
        latlngs.push(marker.getLatLng());
    });
    
    if (latlngs.length > 0) {
        const group = L.featureGroup(latlngs);
        map.fitBounds(group.getBounds(), { padding: [50, 50] });
    }
}

// Export functions for use in control.js
window.MapManager = {
    initMap,
    updateOwnShip,
    updateTargets,
    clearTargets,
    fitMapToShips
};
