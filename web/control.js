// control.js - MQTT Control and UI Management

// MQTT Configuration
const MQTT_HOST = 'localhost';
const MQTT_PORT = 8081; // WebSocket port for MQTT
const MQTT_CLIENT_ID = 'web-dashboard-' + Math.random().toString(16).substr(2, 8);

// MQTT Topics
const TOPICS = {
    NMEA_RAW: 'sensors/nmea/raw',
    RADAR_TARGETS: 'sensors/radar/targets',
    WORLD_STATE: 'sensors/world_state',
    CAMERA_STATUS: 'camera/status',
    PTZ_COMMAND: 'control/ptz/command',
    SIMULATION_COMMAND: 'control/simulation/command'
};

// Global state
let mqttClient = null;
let isConnected = false;
let cameraState = {
    pan: 0,
    tilt: 0,
    zoom: 1,
    moving: false
};

// Circular slider state
let isDraggingSlider = false;
let currentPanAngle = 0;

// Debounce timer for PTZ commands
let ptzDebounceTimer = null;
const PTZ_DEBOUNCE_DELAY = 150; // ms

/**
 * Initialize MQTT client
 */
function initMQTT() {
    mqttClient = new Paho.MQTT.Client(MQTT_HOST, MQTT_PORT, MQTT_CLIENT_ID);
    
    mqttClient.onConnectionLost = onConnectionLost;
    mqttClient.onMessageArrived = onMessageArrived;
    
    console.log('📡 MQTT client initialized');
}

/**
 * Connect to MQTT broker
 */
function connectMQTT() {
    if (!mqttClient) {
        initMQTT();
    }
    
    const options = {
        timeout: 10,
        onSuccess: onConnectSuccess,
        onFailure: onConnectFailure,
        useSSL: false,
        cleanSession: true
    };
    
    console.log(`🔌 Connecting to ${MQTT_HOST}:${MQTT_PORT}...`);
    mqttClient.connect(options);
}

/**
 * Disconnect from MQTT broker
 */
function disconnectMQTT() {
    if (mqttClient && isConnected) {
        mqttClient.disconnect();
        console.log('🔌 Disconnected from MQTT');
    }
}

/**
 * Connection success callback
 */
function onConnectSuccess() {
    isConnected = true;
    console.log('✅ Connected to MQTT broker');
    
    // Subscribe to topics
    mqttClient.subscribe(TOPICS.NMEA_RAW);
    mqttClient.subscribe(TOPICS.RADAR_TARGETS);
    mqttClient.subscribe(TOPICS.WORLD_STATE);
    mqttClient.subscribe(TOPICS.CAMERA_STATUS);
    
    console.log('📡 Subscribed to topics');
    
    updateConnectionStatus(true);
}

/**
 * Connection failure callback
 */
function onConnectFailure(error) {
    isConnected = false;
    console.error('❌ MQTT connection failed:', error.errorMessage);
    updateConnectionStatus(false);
}

/**
 * Connection lost callback
 */
function onConnectionLost(responseObject) {
    isConnected = false;
    console.warn('⚠️ MQTT connection lost:', responseObject.errorMessage);
    updateConnectionStatus(false);
    
    // Try to reconnect after 5 seconds
    setTimeout(() => {
        if (!isConnected) {
            console.log('🔄 Attempting to reconnect...');
            connectMQTT();
        }
    }, 5000);
}

/**
 * Message arrived callback
 */
function onMessageArrived(message) {
    const topic = message.destinationName;
    const payload = message.payloadString;
    
    try {
        const data = JSON.parse(payload);
        
        switch (topic) {
            case TOPICS.NMEA_RAW:
                handleNMEARaw(data);
                break;
            case TOPICS.RADAR_TARGETS:
                handleRadarTargets(data);
                break;
            case TOPICS.WORLD_STATE:
                handleWorldState(data);
                break;
            case TOPICS.CAMERA_STATUS:
                handleCameraStatus(data);
                break;
        }
    } catch (error) {
        console.error(`❌ Error parsing message from ${topic}:`, error);
    }
}

/**
 * Handle NMEA raw message (GPS data)
 */
function handleNMEARaw(data) {
    // Update own ship on map
    if (window.MapManager) {
        window.MapManager.updateOwnShip(data);
    }
    
    // Update statistics
    updateStatistics(data);
}

/**
 * Handle radar targets message
 */
function handleRadarTargets(data) {
    if (!Array.isArray(data)) {
        console.warn('⚠️ Radar targets is not an array:', data);
        return;
    }
    
    // Update targets on map
    if (window.MapManager) {
        window.MapManager.updateTargets(data);
    }
    
    // Update target count in statistics
    const targetCountEl = document.getElementById('statTargets');
    if (targetCountEl) {
        targetCountEl.textContent = data.length;
    }
}

/**
 * Handle world state message (all ships for debugging)
 */
function handleWorldState(data) {
    console.log('🌍 World state received:', data);
    
    // Update own ship if available
    if (data.own_ship && window.MapManager) {
        window.MapManager.updateOwnShip(data.own_ship);
    }
    
    // Update all targets
    if (data.all_targets && Array.isArray(data.all_targets) && window.MapManager) {
        window.MapManager.updateTargets(data.all_targets);
    }
}

/**
 * Handle camera status message
 */
function handleCameraStatus(data) {
    cameraState = {
        pan: data.pan || 0,
        tilt: data.tilt || 0,
        zoom: data.zoom || 1,
        moving: data.moving || false
    };
    
    // Update camera display
    updateCameraDisplay();
    
    // Update slider positions to match received state
    const panSlider = document.getElementById('cameraPanSlider');
    const tiltSlider = document.getElementById('cameraTiltSlider');
    const zoomSlider = document.getElementById('cameraZoomSlider');
    
    if (panSlider) {
        panSlider.value = cameraState.pan;
        document.getElementById('panValue').textContent = `${cameraState.pan}°`;
    }
    if (tiltSlider) {
        tiltSlider.value = cameraState.tilt;
        document.getElementById('tiltValue').textContent = `${cameraState.tilt}°`;
    }
    if (zoomSlider) {
        zoomSlider.value = cameraState.zoom;
        document.getElementById('zoomValue').textContent = `${cameraState.zoom}x`;
    }
    
    // Update circular slider visual
    updateCircularSlider(cameraState.pan);
    
    // Update visualization on map
    updateCameraVisualization();
}

/**
 * Send simulation command
 */
function sendSimulationCommand(action, scenario = null, timescale = null) {
    if (!mqttClient || !isConnected) {
        console.error('❌ Not connected to MQTT');
        alert('Not connected to MQTT broker');
        return;
    }
    
    let command;
    
    if (action === 'start') {
        command = {
            action: 'start',
            scenario: scenario || 'crossing_starboard',
            timescale: timescale || 1.0
        };
    } else if (action === 'stop') {
        command = { action: 'stop' };
    } else if (action === 'timescale') {
        command = {
            action: 'timescale',
            value: timescale
        };
    } else if (action === 'restart') {
        command = {
            action: 'stop'
        };
        // Send stop first, then start after delay
        mqttClient.send(new Paho.MQTT.Message(JSON.stringify(command)), TOPICS.SIMULATION_COMMAND);
        setTimeout(() => {
            const startCommand = {
                action: 'start',
                scenario: scenario || 'crossing_starboard',
                timescale: timescale || 1.0
            };
            mqttClient.send(new Paho.MQTT.Message(JSON.stringify(startCommand)), TOPICS.SIMULATION_COMMAND);
        }, 500);
        return;
    }
    
    const message = new Paho.MQTT.Message(JSON.stringify(command));
    message.destinationName = TOPICS.SIMULATION_COMMAND;
    
    console.log('📤 Sending simulation command:', command);
    mqttClient.send(message);
}

/**
 * Send PTZ camera command with debouncing
 */
function sendPTZCommand(pan, tilt, zoom, speed = 50, mode = 'absolute') {
    if (!mqttClient || !isConnected) {
        console.error('❌ Not connected to MQTT');
        // Still update local state even if not connected
        cameraState = { pan, tilt, zoom, moving: false };
        updateCameraDisplay();
        return;
    }
    
    const command = {
        pan: parseFloat(pan),
        tilt: parseFloat(tilt),
        zoom: parseInt(zoom),
        speed: parseInt(speed),
        mode: mode
    };
    
    const message = new Paho.MQTT.Message(JSON.stringify(command));
    message.destinationName = TOPICS.PTZ_COMMAND;
    
    console.log('📤 Sending PTZ command:', command);
    mqttClient.send(message);
}

/**
 * Send PTZ command with debouncing (for slider input)
 */
function sendPTZCommandDebounced(pan, tilt, zoom) {
    // Clear existing timer
    if (ptzDebounceTimer) {
        clearTimeout(ptzDebounceTimer);
    }
    
    // Update local state immediately for responsive UI
    cameraState = { pan, tilt, zoom, moving: false };
    updateCameraDisplay();
    updateCameraVisualization();
    
    // Send MQTT command after debounce delay
    ptzDebounceTimer = setTimeout(() => {
        sendPTZCommand(pan, tilt, zoom);
    }, PTZ_DEBOUNCE_DELAY);
}

/**
 * Update connection status UI
 */
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connectionStatus');
    const statusTextEl = statusEl.querySelector('.status-text');
    
    if (connected) {
        statusEl.classList.add('connected');
        statusEl.classList.remove('disconnected');
        statusTextEl.textContent = 'Connected';
    } else {
        statusEl.classList.remove('connected');
        statusEl.classList.add('disconnected');
        statusTextEl.textContent = 'Disconnected';
    }
}

/**
 * Update statistics display
 */
function updateStatistics(gpsData) {
    const speedEl = document.getElementById('statSpeed');
    const courseEl = document.getElementById('statCourse');
    const latEl = document.getElementById('statLat');
    const lonEl = document.getElementById('statLon');
    
    if (speedEl && gpsData.speed !== undefined) {
        speedEl.textContent = `${parseFloat(gpsData.speed).toFixed(1)} kn`;
    }
    
    if (courseEl && gpsData.course !== undefined) {
        courseEl.textContent = `${parseFloat(gpsData.course).toFixed(1)}°`;
    }
    
    if (latEl && gpsData.lat !== undefined) {
        latEl.textContent = parseFloat(gpsData.lat).toFixed(6);
    }
    
    if (lonEl && gpsData.lon !== undefined) {
        lonEl.textContent = parseFloat(gpsData.lon).toFixed(6);
    }
}

/**
 * Update camera display
 */
function updateCameraDisplay() {
    const panEl = document.getElementById('cameraPan');
    const tiltEl = document.getElementById('cameraTilt');
    const zoomEl = document.getElementById('cameraZoom');
    const movingEl = document.getElementById('cameraMoving');
    
    if (panEl) panEl.textContent = `${cameraState.pan.toFixed(1)}°`;
    if (tiltEl) tiltEl.textContent = `${cameraState.tilt.toFixed(1)}°`;
    if (zoomEl) zoomEl.textContent = `${cameraState.zoom}x`;
    if (movingEl) movingEl.textContent = cameraState.moving ? 'Moving' : 'Idle';
}

/**
 * Update circular slider visual
 */
function updateCircularSlider(pan) {
    const indicator = document.querySelector('.slider-indicator');
    const activeArc = document.querySelector('.slider-active');
    
    if (indicator) {
        // Rotate indicator: 0° = up (N), positive = clockwise
        indicator.setAttribute('transform', `rotate(${pan}, 100, 100)`);
    }
    
    if (activeArc) {
        // Calculate arc length to show from -180 to current pan
        // Circumference = 2 * PI * 80 ≈ 502.65
        const circumference = 502.65;
        // Map pan (-180 to 180) to arc portion (0 to full circle)
        const panNormalized = pan + 180; // 0 to 360
        const arcLength = (panNormalized / 360) * circumference;
        const offset = circumference - arcLength;
        activeArc.setAttribute('stroke-dashoffset', offset);
    }
}

/**
 * Convert mouse/touch position to angle
 */
function getPositionAngle(event, svgElement) {
    const rect = svgElement.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    let clientX, clientY;
    if (event.touches && event.touches.length > 0) {
        clientX = event.touches[0].clientX;
        clientY = event.touches[0].clientY;
    } else {
        clientX = event.clientX;
        clientY = event.clientY;
    }
    
    const dx = clientX - centerX;
    const dy = clientY - centerY;
    
    // Calculate angle in degrees (0° = up/North, positive = clockwise)
    let angle = Math.atan2(dx, -dy) * (180 / Math.PI);
    
    return angle;
}

/**
 * Initialize circular slider interactions
 */
function initCircularSlider() {
    const slider = document.getElementById('panCircularSlider');
    const hiddenSlider = document.getElementById('cameraPanSlider');
    
    if (!slider || !hiddenSlider) return;
    
    // Mouse down / touch start
    const startDrag = (e) => {
        e.preventDefault();
        isDraggingSlider = true;
        slider.style.cursor = 'grabbing';
        
        const pan = getPositionAngle(e, slider);
        updatePanFromCircular(pan);
    };
    
    // Mouse move / touch move
    const doDrag = (e) => {
        if (!isDraggingSlider) return;
        e.preventDefault();
        
        const pan = getPositionAngle(e, slider);
        updatePanFromCircular(pan);
    };
    
    // Mouse up / touch end
    const stopDrag = (e) => {
        if (!isDraggingSlider) return;
        isDraggingSlider = false;
        slider.style.cursor = 'pointer';
    };
    
    // Event listeners for mouse
    slider.addEventListener('mousedown', startDrag);
    document.addEventListener('mousemove', doDrag);
    document.addEventListener('mouseup', stopDrag);
    
    // Event listeners for touch
    slider.addEventListener('touchstart', startDrag, { passive: false });
    document.addEventListener('touchmove', doDrag, { passive: false });
    document.addEventListener('touchend', stopDrag);
}

/**
 * Update pan value from circular slider interaction
 */
function updatePanFromCircular(pan) {
    // Round to nearest degree
    pan = Math.round(pan);
    
    // Normalize to -180...180
    while (pan > 180) pan -= 360;
    while (pan < -180) pan += 360;
    
    currentPanAngle = pan;
    
    // Update hidden slider value
    const hiddenSlider = document.getElementById('cameraPanSlider');
    if (hiddenSlider) {
        hiddenSlider.value = pan;
    }
    
    // Update display
    document.getElementById('panValue').textContent = `${pan}°`;
    
    // Update visual
    updateCircularSlider(pan);
    
    // Send command with debouncing
    sendPTZCommandDebounced(pan, cameraState.tilt, cameraState.zoom);
}

/**
 * Update camera visualization on map (ship marker)
 */
function updateCameraVisualization() {
    if (window.MapManager && typeof window.MapManager.updateCameraDirection === 'function') {
        window.MapManager.updateCameraDirection(cameraState.pan);
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Start button
    const btnStart = document.getElementById('btnStart');
    if (btnStart) {
        btnStart.addEventListener('click', () => {
            const scenario = document.getElementById('scenarioSelect').value;
            const timescale = parseFloat(document.getElementById('timeScaleSlider').value);
            sendSimulationCommand('start', scenario, timescale);
        });
    }
    
    // Stop button
    const btnStop = document.getElementById('btnStop');
    if (btnStop) {
        btnStop.addEventListener('click', () => {
            sendSimulationCommand('stop');
        });
    }
    
    // Restart button
    const btnRestart = document.getElementById('btnRestart');
    if (btnRestart) {
        btnRestart.addEventListener('click', () => {
            const scenario = document.getElementById('scenarioSelect').value;
            const timescale = parseFloat(document.getElementById('timeScaleSlider').value);
            sendSimulationCommand('restart', scenario, timescale);
        });
    }
    
    // Time scale slider
    const timeScaleSlider = document.getElementById('timeScaleSlider');
    const timeScaleValue = document.getElementById('timeScaleValue');
    if (timeScaleSlider && timeScaleValue) {
        timeScaleSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            timeScaleValue.textContent = `${value}x`;
            sendSimulationCommand('timescale', null, value);
        });
    }
    
    // Initialize circular slider for pan control
    initCircularSlider();
    
    // Camera PTZ sliders - instant response with debouncing
    // Note: Pan slider is hidden, controlled by circular slider
    const cameraTiltSlider = document.getElementById('cameraTiltSlider');
    if (cameraTiltSlider) {
        cameraTiltSlider.addEventListener('input', (e) => {
            const tilt = parseFloat(e.target.value);
            document.getElementById('tiltValue').textContent = `${tilt}°`;
            sendPTZCommandDebounced(cameraState.pan, tilt, cameraState.zoom);
        });
    }
    
    const cameraZoomSlider = document.getElementById('cameraZoomSlider');
    if (cameraZoomSlider) {
        cameraZoomSlider.addEventListener('input', (e) => {
            const zoom = parseInt(e.target.value);
            document.getElementById('zoomValue').textContent = `${zoom}x`;
            sendPTZCommandDebounced(cameraState.pan, cameraState.tilt, zoom);
        });
    }
}

/**
 * Initialize the dashboard
 */
function initDashboard() {
    console.log('🚀 Initializing MarineNav Dashboard...');
    
    // Initialize map
    if (window.MapManager) {
        window.MapManager.initMap();
    }
    
    // Initialize circular slider
    initCircularSlider();
    
    // Initialize MQTT
    initMQTT();
    
    // Setup event listeners
    setupEventListeners();
    
    // Auto-connect to MQTT
    setTimeout(() => {
        connectMQTT();
    }, 1000);
    
    console.log('✅ Dashboard initialized');
}

// Start dashboard when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}
