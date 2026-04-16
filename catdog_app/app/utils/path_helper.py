import sys
from pathlib import Path

def get_resource_path(relative_path: str) -> Path:
    """
    Возвращает абсолютный путь к ресурсу.
    Корректно работает как в режиме разработки, так и в PyInstaller-сборке.
    """
    if hasattr(sys, '_MEIPASS'):
        # Режим PyInstaller
        return Path(sys._MEIPASS) / relative_path
    else:
        # Режим разработки
        return Path(__file__).parent.parent.parent / relative_path