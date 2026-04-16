from typing import Dict, Optional
import logging

from app.model.classifier import CatDogClassifier
from app.services.file_service import FileService
from app.services.exceptions import (
    AppException, FileValidationError, 
    ModelNotLoadedError, PredictionError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

class PredictionService:
    """
    Оркестратор бизнес-логики:
    валидация → препроцессинг → инференс → форматирование результата
    """
    
    def __init__(self, classifier: CatDogClassifier):
        self.classifier = classifier
        self.file_service = FileService()
    
    def classify_image(self, image_path: str) -> Dict[str, any]:
        """
        Публичный метод для классификации изображения
        
        Returns:
            dict: {
                "success": bool,
                "data": dict|None,  # {"class": str, "confidence": float}
                "error": str|None,
                "file_info": dict|None
            }
        """
        result = {
            "success": False,
            "data": None,
            "error": None,
            "file_info": None
        }
        
        try:
            # 1. Валидация файла
            self.file_service.validate_file(image_path)
            result["file_info"] = self.file_service.get_file_info(image_path)
            
            # 2. Проверка загрузки модели
            if not self.classifier.is_loaded:
                raise ModelNotLoadedError("Classifier model is not loaded")
            
            # 3. Выполнение предсказания
            prediction = self.classifier.predict(image_path)
            
            # 4. Форматирование успешного результата
            result["success"] = True
            result["data"] = {
                "class": prediction["class"],
                "confidence": prediction["confidence"],
                "confidence_percent": round(prediction["confidence"] * 100, 2)
            }
            logger.info(f"Successfully classified: {image_path} → {result['data']}")
            
        except (FileValidationError, FileSizeError) as e:
            result["error"] = f"Ошибка файла: {e.message}"
            logger.warning(f"File validation failed: {e.message}")
            
        except ModelNotLoadedError as e:
            result["error"] = f"Ошибка модели: {e.message}"
            logger.error(f"Model not ready: {e.message}")
            
        except Exception as e:
            result["error"] = f"Неожиданная ошибка: {type(e).__name__}: {str(e)}"
            logger.exception(f"Prediction failed for {image_path}")
        
        return result