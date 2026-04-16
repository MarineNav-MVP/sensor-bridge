from pathlib import Path
from pydantic import BaseModel

class ModelConfig(BaseModel):
    """Конфигурация модели классификации"""
    
    # Пути
    model_path: str = "assets/models/cat_dog_model.h5"
    
    # Параметры предобработки
    input_size: tuple = (224, 224)  # (height, width)
    normalize: bool = True
    scale_factor: float = 255.0
    
    # Поддерживаемые форматы
    allowed_extensions: set = {".jpg", ".jpeg", ".png"}
    max_file_size_mb: int = 10
    
    # Параметры предсказания
    threshold: float = 0.5  # Порог для бинарной классификации
    
    @property
    def model_path_obj(self) -> Path:
        return Path(self.model_path)
    
    def is_valid_format(self, filename: str) -> bool:
        return Path(filename).suffix.lower() in self.allowed_extensions

# Глобальный экземпляр конфигурации
config = ModelConfig()