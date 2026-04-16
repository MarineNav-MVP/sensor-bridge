from pathlib import Path
from PIL import Image
import os

from app.model.config import config
from app.services.exceptions import FileValidationError, FileSizeError

class FileService:
    """Сервис для валидации и обработки файлов изображений"""
    
    @staticmethod
    def validate_file(file_path: str) -> bool:
        """
        Комплексная валидация файла изображения
        
        Raises:
            FileValidationError: Если файл невалиден
            FileSizeError: Если файл слишком большой
        """
        path = Path(file_path)
        
        # Проверка существования
        if not path.exists():
            raise FileValidationError(f"File not found: {file_path}")
        
        # Проверка расширения
        if not config.is_valid_format(path.name):
            raise FileValidationError(
                f"Unsupported format: {path.suffix}. Allowed: {config.allowed_extensions}"
            )
        
        # Проверка размера
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > config.max_file_size_mb:
            raise FileSizeError(
                f"File too large: {file_size_mb:.2f} MB (max: {config.max_file_size_mb} MB)"
            )
        
        # Проверка целостности (попытка открыть через PIL)
        try:
            with Image.open(path) as img:
                img.verify()  # Проверяем, что файл не повреждён
        except Exception as e:
            raise FileValidationError(f"Corrupted image file: {e}")
        
        return True
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """Возвращает информацию о файле для отображения в UI"""
        path = Path(file_path)
        with Image.open(path) as img:
            return {
                "name": path.name,
                "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
                "format": img.format,
                "dimensions": img.size,  # (width, height)
                "mode": img.mode
            }