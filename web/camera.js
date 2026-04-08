/**
 * camera.js - Визуализация камеры PTZ
 * 
 * Отображает направление камеры на схеме:
 * - Сектор обзора камеры
 * - Индикаторы pan/tilt/zoom
 * - Список целей для трекинга (заглушка для FusionCore)
 */

// Глобальное состояние камеры
let cameraVisualState = {
    pan: 0,
    tilt: 0,
    zoom: 1,
    moving: false,
    fov: 60  // Поле обзора (градусы)
};

// Ссылка на canvas
let canvas = null;
let ctx = null;

/**
 * Инициализация визуализации камеры
 */
function initCameraWidget() {
    console.log('📹 Initializing camera widget...');
    
    // Создаём canvas для схемы камеры
    const cameraContainer = document.querySelector('.camera-visualization');
    if (!cameraContainer) {
        console.warn('⚠️ Camera visualization container not found');
        return;
    }
    
    canvas = document.createElement('canvas');
    canvas.width = 300;
    canvas.height = 200;
    canvas.style.cssText = 'background-color: #0f3460; border-radius: 8px; width: 100%; margin-bottom: 15px;';
    
    cameraContainer.appendChild(canvas);
    ctx = canvas.getContext('2d');
    
    // Отрисовка начального состояния
    drawCameraView();
    
    console.log('✅ Camera widget initialized');
}

/**
 * Отрисовка вида камеры
 */
function drawCameraView() {
    if (!ctx || !canvas) return;
    
    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    
    // Очистка
    ctx.clearRect(0, 0, width, height);
    
    // Фон (тёмно-синий - море)
    ctx.fillStyle = '#0a0a1a';
    ctx.fillRect(0, 0, width, height);
    
    // Сохраняем контекст для трансформаций
    ctx.save();
    
    // Перемещаем начало координат в центр
    ctx.translate(centerX, centerY);
    
    // Поворачиваем на угол pan (инвертируем для визуализации)
    ctx.rotate(-cameraVisualState.pan * Math.PI / 180);
    
    // Рисуем сектор обзора камеры
    const fovRad = cameraVisualState.fov * Math.PI / 180;
    const range = Math.min(width, height) * 0.8;
    
    // Градиент для сектора обзора
    const gradient = ctx.createConicGradient(fovRad, -fovRad / 2, 0);
    gradient.addColorStop(0, 'rgba(74, 222, 128, 0)');
    gradient.addColorStop(0.5, 'rgba(74, 222, 128, 0.3)');
    gradient.addColorStop(1, 'rgba(74, 222, 128, 0)');
    
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, range, -fovRad / 2, fovRad / 2);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();
    
    // Границы сектора
    ctx.strokeStyle = '#4ade80';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(Math.cos(-fovRad / 2) * range, Math.sin(-fovRad / 2) * range);
    ctx.moveTo(0, 0);
    ctx.lineTo(Math.cos(fovRad / 2) * range, Math.sin(fovRad / 2) * range);
    ctx.stroke();
    
    // Дуга на краю сектора
    ctx.beginPath();
    ctx.arc(0, 0, range, -fovRad / 2, fovRad / 2);
    ctx.strokeStyle = 'rgba(74, 222, 128, 0.5)';
    ctx.stroke();
    
    // Восстанавливаем контекст
    ctx.restore();
    
    // Рисуем компас (север вверху)
    drawCompass(width - 30, 30);
    
    // Индикатор движения
    if (cameraVisualState.moving) {
        ctx.fillStyle = '#e94560';
        ctx.font = 'bold 14px sans-serif';
        ctx.fillText('MOVING', 10, height - 10);
    }
}

/**
 * Отрисовка компаса
 */
function drawCompass(x, y) {
    const radius = 20;
    
    ctx.save();
    ctx.translate(x, y);
    
    // Круг компаса
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, 2 * Math.PI);
    ctx.fillStyle = '#16213e';
    ctx.fill();
    ctx.strokeStyle = '#4ade80';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // Стрелка севера
    ctx.rotate(-cameraVisualState.pan * Math.PI / 180);
    
    ctx.beginPath();
    ctx.moveTo(0, -radius + 5);
    ctx.lineTo(5, radius - 5);
    ctx.lineTo(0, radius - 2);
    ctx.lineTo(-5, radius - 5);
    ctx.closePath();
    ctx.fillStyle = '#e94560';
    ctx.fill();
    
    // Буква N
    ctx.rotate(cameraVisualState.pan * Math.PI / 180);
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('N', 0, -radius - 5);
    
    ctx.restore();
}

/**
 * Обновление состояния камеры из MQTT
 */
function updateCameraFromMQTT(data) {
    cameraVisualState.pan = data.pan || 0;
    cameraVisualState.tilt = data.tilt || 0;
    cameraVisualState.zoom = data.zoom || 1;
    cameraVisualState.moving = data.moving || false;
    
    // Перерисовка
    drawCameraView();
    
    // Обновление текстовых индикаторов
    updateCameraIndicators();
}

/**
 * Обновление текстовых индикаторов камеры
 */
function updateCameraIndicators() {
    const panEl = document.getElementById('cameraPan');
    const tiltEl = document.getElementById('cameraTilt');
    const zoomEl = document.getElementById('cameraZoom');
    const movingEl = document.getElementById('cameraMoving');
    
    if (panEl) panEl.textContent = `${cameraVisualState.pan.toFixed(1)}°`;
    if (tiltEl) tiltEl.textContent = `${cameraVisualState.tilt.toFixed(1)}°`;
    if (zoomEl) zoomEl.textContent = `${cameraVisualState.zoom}x`;
    if (movingEl) {
        movingEl.textContent = cameraVisualState.moving ? 'Moving' : 'Idle';
        movingEl.style.color = cameraVisualState.moving ? '#e94560' : '#4ade80';
    }
    
    // Синхронизация слайдеров
    const panSlider = document.getElementById('cameraPanSlider');
    const tiltSlider = document.getElementById('cameraTiltSlider');
    const zoomSelect = document.getElementById('cameraZoomSelect');
    
    if (panSlider && Math.abs(parseFloat(panSlider.value) - cameraVisualState.pan) > 1) {
        panSlider.value = cameraVisualState.pan;
    }
    if (tiltSlider && Math.abs(parseFloat(tiltSlider.value) - cameraVisualState.tilt) > 1) {
        tiltSlider.value = cameraVisualState.tilt;
    }
    if (zoomSelect && parseInt(zoomSelect.value) !== cameraVisualState.zoom) {
        zoomSelect.value = cameraVisualState.zoom;
    }
}

/**
 * Получить список целей (для dropdown)
 * Заглушка - данные будут приходить из sensors/radar/targets
 */
let availableTargets = [];

function updateTargetList(targets) {
    availableTargets = targets || [];
    
    const targetSelect = document.getElementById('targetSelect');
    if (!targetSelect) return;
    
    // Сохраняем текущее значение
    const currentValue = targetSelect.value;
    
    // Очищаем список
    targetSelect.innerHTML = '<option value="">-- Select Target --</option>';
    
    // Добавляем цели
    availableTargets.forEach(target => {
        const option = document.createElement('option');
        option.value = target.id;
        option.textContent = `${target.id} - ${target.bearing}° @ ${target.distance} NM`;
        targetSelect.appendChild(option);
    });
    
    // Восстанавливаем выбор если возможно
    if (currentValue && availableTargets.find(t => t.id === currentValue)) {
        targetSelect.value = currentValue;
    }
}

/**
 * Отправить команду выбора цели (для FusionCore)
 */
function sendTargetSelection(targetId) {
    if (!mqttClient || !isConnected) {
        console.error('❌ Not connected to MQTT');
        return;
    }
    
    // Это команда для FusionCore - выбрать цель для трекинга
    const command = {
        action: 'select_target',
        target_id: targetId
    };
    
    // Публикуем в специальный топик (FusionCore должен подписаться)
    const message = new Paho.MQTT.Message(JSON.stringify(command));
    message.destinationName = 'control/fusioncore/command';
    
    console.log('🎯 Target selection:', command);
    mqttClient.send(message);
}

/**
 * Setup event listeners для камеры
 */
function setupCameraEventListeners() {
    // Выбор цели
    const targetSelect = document.getElementById('targetSelect');
    if (targetSelect) {
        targetSelect.addEventListener('change', (e) => {
            if (e.target.value) {
                sendTargetSelection(e.target.value);
            }
        });
    }
    
    // Обновление слайдеров в реальном времени
    const panSlider = document.getElementById('cameraPanSlider');
    const tiltSlider = document.getElementById('cameraTiltSlider');
    
    if (panSlider) {
        panSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            document.getElementById('cameraPanSliderValue').textContent = `${value}°`;
        });
    }
    
    if (tiltSlider) {
        tiltSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            document.getElementById('cameraTiltSliderValue').textContent = `${value}°`;
        });
    }
}

// Экспорт функций для использования в control.js
window.CameraWidget = {
    init: initCameraWidget,
    update: updateCameraFromMQTT,
    updateTargetList: updateTargetList,
    draw: drawCameraView
};
