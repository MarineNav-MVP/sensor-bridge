class AppException(Exception):
    """Базовое исключение приложения"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class FileValidationError(AppException):
    """Ошибка валидации файла"""
    pass

class FileSizeError(AppException):
    """Файл превышает допустимый размер"""
    pass

class ModelNotLoadedError(AppException):
    """Попытка использования незагруженной модели"""
    pass

class PredictionError(AppException):
    """Ошибка во время выполнения предсказания"""
    pass