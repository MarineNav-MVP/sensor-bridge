# 🚢 Sensor Bridge

Эмулятор морских сенсоров для тестирования FusionCore (CV) и NavLogic (МППСС).

## 📦 Быстрый старт

```bash
# 1. MQTT брокер
docker run -d -p 1883:1883 eclipse-mosquitto

# 2. Зависимости
pip install -r requirements.txt

# 3. Запуск
python main.py

# 4. Веб-панель
cd web && python -m http.server 8000
# Открыть: http://localhost:8000
