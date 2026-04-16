import logging
import sys
from pathlib import Path

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Создаёт настроенный логгер с консольным и файловым хендлерами"""
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Избегаем дублирования хендлеров при повторных вызовах
    if logger.handlers:
        return logger
    
    # Формат сообщений
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный хендлер
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)
    
    # Файловый хендлер (опционально)
    log_file = Path("logs/app.log")
    log_file.parent.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    return logger