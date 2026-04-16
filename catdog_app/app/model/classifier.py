import numpy as np
from PIL import Image
from typing import Dict, Optional
import logging

# Импорт в зависимости от вашего фреймворка
try:
    import tensorflow as tf
    FRAMEWORK = "tensorflow"
except ImportError:
    import torch
    FRAMEWORK = "pytorch"

from app.model.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)

class CatDogClassifier:
    """Инкапсуляция логики работы с моделью классификации кот/собака"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.model_path = model_path or config.model_path
        self.is_loaded = False
        
    def load(self) -> bool:
        """Загрузка модели в память. Вызывать один раз при старте приложения."""
        try:
            if FRAMEWORK == "tensorflow":
                self.model = tf.keras.models.load_model(self.model_path)
            else:  # pytorch
                import torch
                self.model = torch.load(self.model_path, map_location='cpu')
                self.model.eval()
            
            self.is_loaded = True
            logger.info(f"Model loaded successfully from {self.model_path}")
            return True
            
        except FileNotFoundError:
            logger.error(f"Model file not found: {self.model_path}")
            return False
        except Exception as e:
            logger.error(f"Failed to load model: {type(e).__name__}: {e}")
            return False
    
    def _preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Препроцессинг изображения под требования модели
        Возвращает tensor формы (1, H, W, C) для TF или (1, C, H, W) для PyTorch
        """
        img = Image.open(image_path).convert('RGB')
        img = img.resize(config.input_size)
        
        img_array = np.array(img)
        
        if config.normalize:
            img_array = img_array / config.scale_factor
        
        if FRAMEWORK == "tensorflow":
            # TF ожидает (batch, height, width, channels)
            return np.expand_dims(img_array, axis=0)
        else:
            # PyTorch ожидает (batch, channels, height, width)
            img_array = np.transpose(img_array, (2, 0, 1))  # HWC -> CHW
            return np.expand_dims(img_array, axis=0)
    
    def predict(self, image_path: str) -> Dict[str, any]:
        """
        Выполняет предсказание для изображения
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            dict: {"class": "cat"|"dog", "confidence": float, "raw_probability": float}
            
        Raises:
            RuntimeError: Если модель не загружена
            ValueError: Если изображение невалидно
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        
        # Препроцессинг
        try:
            input_tensor = self._preprocess_image(image_path)
        except Exception as e:
            raise ValueError(f"Failed to preprocess image: {e}")
        
        # Инференс
        if FRAMEWORK == "tensorflow":
            predictions = self.model.predict(input_tensor, verbose=0)
            probability = float(predictions[0][0])  # sigmoid output
        else:  # pytorch
            import torch
            with torch.no_grad():
                input_tensor = torch.FloatTensor(input_tensor)
                output = self.model(input_tensor)
                probability = float(torch.sigmoid(output[0]).item())
        
        # Постобработка: бинарная классификация
        label = "dog" if probability >= config.threshold else "cat"
        confidence = probability if label == "dog" else 1 - probability
        
        logger.debug(f"Prediction: {label} (confidence: {confidence:.4f}, raw: {probability:.4f})")
        
        return {
            "class": label,
            "confidence": round(confidence, 4),
            "raw_probability": round(probability, 4)
        }
    
    def unload(self):
        """Освобождение ресурсов модели (опционально)"""
        self.model = None
        self.is_loaded = False
        logger.info("Model unloaded")