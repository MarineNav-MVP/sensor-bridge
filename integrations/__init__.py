"""
Integrations package for Sensor Bridge.

Модули интеграции с внешними системами:
- fusioncore_stub: Пример заглушки для разработчика FusionCore
- mqtt_client: Обёртка над paho-mqtt (в разработке)
"""

from .fusioncore_stub import FusionCoreStub

__all__ = ["FusionCoreStub"]
