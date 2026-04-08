// control.js - MQTT Control and UI Management

// MQTT Configuration
const MQTT_HOST = 'localhost';
const MQTT_PORT = 9001; // WebSocket port for MQTT
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
    
    // Update target list for camera tracking
    if (window.CameraWidget) {
        window.CameraWidget.updateTargetList(data);
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
    
    // Update camera widget visualization
    if (window.CameraWidget) {
        window.CameraWidget.update(data);
    }
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
 * Send PTZ camera command
 */
function sendPTZCommand(pan, tilt, zoom, speed = 50, mode = 'absolute') {
    if (!mqttClient || !isConnected) {
        console.error('❌ Not connected to MQTT');
        alert('Not connected to MQTT broker');
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
 * Setup event listeners for camera
 */
function setupCameraEventListeners() {
    // Selection target
    const targetSelect = document.getElementById('targetSelect');
    if (targetSelect) {
        targetSelect.addEventListener('change', (e) => {
            if (e.target.value) {
                sendTargetSelection(e.target.value);
            }
        });
    }
    
    // Update sliders in real-time
    const panSlider = document.getElementById('cameraPanSlider');
    const tiltSlider = document.getElementById('cameraTiltSlider');
    
    if (panSlider) {
        panSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            const valueEl = document.getElementById('cameraPanSliderValue');
            if (valueEl) valueEl.textContent = `${value}°`;
        });
    }
    
    if (tiltSlider) {
        tiltSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            const valueEl = document.getElementById('cameraTiltSliderValue');
            if (valueEl) valueEl.textContent = `${value}°`;
        });
    }
}

/**
 * Send target selection command (for FusionCore)
 */
function sendTargetSelection(targetId) {
    if (!mqttClient || !isConnected) {
        console.error('❌ Not connected to MQTT');
        return;
    }
    
    // Command for FusionCore - select target for tracking
    const command = {
        action: 'select_target',
        target_id: targetId
    };
    
    // Publish to special topic (FusionCore should subscribe)
    const message = new Paho.MQTT.Message(JSON.stringify(command));
    message.destinationName = 'control/fusioncore/command';
    
    console.log('🎯 Target selection:', command);
    mqttClient.send(message);
}

/**
 * Setup event listeners for simulation controls
 */
function setupSimulationEventListeners() {
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
    
    // Camera move button
    const btnCameraMove = document.getElementById('btnCameraMove');
    if (btnCameraMove) {
        btnCameraMove.addEventListener('click', () => {
            const pan = parseFloat(document.getElementById('cameraPanSlider').value);
            const tilt = parseFloat(document.getElementById('cameraTiltSlider').value);
            const zoom = parseInt(document.getElementById('cameraZoomSelect').value);
            sendPTZCommand(pan, tilt, zoom);
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
    
    // Initialize camera widget
    if (window.CameraWidget) {
        window.CameraWidget.init();
    }
    
    // Setup event listeners for camera
    if (window.CameraWidget && window.CameraWidget.setupEventListeners) {
        window.CameraWidget.setupEventListeners();
    } else {
        setupCameraEventListeners();
    }
    
    // Initialize MQTT
    initMQTT();
    
    // Setup simulation event listeners
    setupSimulationEventListeners();
    
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
