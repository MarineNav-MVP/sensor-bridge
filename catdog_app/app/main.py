import flet as ft
import sys
from pathlib import Path

# Добавляем корень проекта в PATH для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.model.classifier import CatDogClassifier
from app.ui.main_window import MainWindow
from app.utils.logger import get_logger

logger = get_logger(__name__)

def main(page: ft.Page):
    """Точка входа приложения Flet"""
    
    # Настройка страницы
    page.title = "🐱🐶 CatDog Classifier"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    # Индикатор загрузки
    loading_text = ft.Text("⏳ Загрузка модели...", size=16)
    page.add(loading_text)
    
    # Загрузка модели (синхронно при старте)
    classifier = CatDogClassifier()
    
    if not classifier.load():
        page.snack_bar = ft.SnackBar(
            content=ft.Text("❌ Не удалось загрузить модель! Проверьте путь к файлу."),
            bgcolor=ft.colors.RED,
        )
        page.snack_bar.open = True
        loading_text.value = "❌ Ошибка загрузки модели"
        loading_text.color = ft.colors.RED
        page.update()
        return
    
    # Убираем индикатор, добавляем основной интерфейс
    page.controls.clear()
    page.add(MainWindow(classifier, page))
    page.update()
    
    logger.info("Application started successfully")

# Запуск приложения
if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")