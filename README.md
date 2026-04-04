# 📡 SensorBridge Module

Модуль для работы с аппаратным обеспечением: GPS, радар, PTZ-камера.

## 🎯 Задача
- Парсинг NMEA 0183 (GPS, компас)
- Чтение данных радара ($TTM или API)
- Управление PTZ-камерой (ONVIF/VISCA)
- Публикация данных в MQTT

## 📋 Текущая задача
Смотри в Issue #1: [Реализовать парсер NMEA и эмулятор радара](../../issues/1)

## 🚀 Быстрый старт

### Требования
- Python 3.8+
- Docker (для MQTT брокера)
- Библиотеки: `paho-mqtt`, `pynmea2`

## Контракты
https://github.com/dlameros/project-config/blob/main/CONTRACTS.md


