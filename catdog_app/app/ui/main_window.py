import flet as ft
from typing import Optional

from app.model.classifier import CatDogClassifier
from app.services.prediction_service import PredictionService
from app.utils.logger import get_logger

logger = get_logger(__name__)

class MainWindow(ft.Column):
    """Главный экран приложения для классификации кот/собака"""
    
    def __init__(self, classifier: CatDogClassifier, page: ft.Page):
        super().__init__()
        self.classifier = classifier
        self.prediction_service = PredictionService(classifier)
        self.page = page
        
        # Состояние
        self.selected_image_path: Optional[str] = None
        
        # UI компоненты (инициализируются в build)
        self.picker: Optional[ft.FilePicker] = None
        self.image_preview: Optional[ft.Image] = None
        self.result_text: Optional[ft.Text] = None
        self.classify_button: Optional[ft.ElevatedButton] = None
        self.progress_ring: Optional[ft.ProgressRing] = None
        
        # Строим интерфейс
        self._build_ui()
    
    def _show_snackbar(self, message: str, is_error: bool = True):
        """Показывает всплывающее уведомление"""
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.colors.RED if is_error else ft.colors.GREEN,
                behavior=ft.SnackBarBehavior.FLOATING,
            )
        )
    
    def _on_file_pick_result(self, e: ft.FilePickerResultEvent):
        """Обработчик выбора файла"""
        if e.files:
            file_path = e.files[0].path
            self.selected_image_path = file_path
            
            # Обновляем превью
            self.image_preview.src = file_path
            self.image_preview.visible = True
            
            # Сбрасываем предыдущий результат
            self.result_text.value = ""
            self.result_text.visible = False
            
            self._show_snackbar(f"📁 Выбран: {e.files[0].name}", is_error=False)
            self.update()
    
    def _on_classify_click(self, e: ft.ControlEvent):
        """Обработчик кнопки классификации"""
        if not self.selected_image_path:
            self._show_snackbar("❌ Сначала выберите изображение")
            return
        
        # UI: состояние загрузки
        self.classify_button.disabled = True
        self.progress_ring.visible = True
        self.result_text.visible = False
        self.update()
        
        # Выполнение в фоновом потоке (чтобы не блокировать UI)
        def run_prediction():
            result = self.prediction_service.classify_image(self.selected_image_path)
            
            # Возврат в главный поток для обновления UI
            def update_ui():
                if result["success"]:
                    data = result["data"]
                    emoji = "🐱" if data["class"] == "cat" else "🐶"
                    self.result_text.value = (
                        f"{emoji} Результат: {data['class'].capitalize()}\n"
                        f"📊 Уверенность: {data['confidence_percent']}%"
                    )
                    self.result_text.color = ft.colors.GREEN
                else:
                    self.result_text.value = f"⚠️ {result['error']}"
                    self.result_text.color = ft.colors.ORANGE
                    self._show_snackbar(result["error"])
                
                self.result_text.visible = True
                self.classify_button.disabled = False
                self.progress_ring.visible = False
                self.update()
            
            self.page.run_task(update_ui)
        
        # Запускаем в отдельном потоке
        import threading
        thread = threading.Thread(target=run_prediction, daemon=True)
        thread.start()
    
    def _build_ui(self):
        """Сборка UI-компонентов"""
        
        # FilePicker для выбора файлов
        self.picker = ft.FilePicker(
            on_result=self._on_file_pick_result,
            allowed_extensions=["jpg", "jpeg", "png"]
        )
        self.page.overlay.append(self.picker)
        
        # Компоненты интерфейса
        self.image_preview = ft.Image(
            src="", width=300, height=300, 
            fit=ft.ImageFit.CONTAIN, visible=False
        )
        
        self.result_text = ft.Text(
            size=16, weight=ft.FontWeight.BOLD, visible=False
        )
        
        self.progress_ring = ft.ProgressRing(visible=False, width=30, height=30)
        
        self.classify_button = ft.ElevatedButton(
            "🔍 Классифицировать",
            on_click=self._on_classify_click,
            icon=ft.icons.AUTO_FIX_HIGH,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.BLUE,
                color=ft.colors.WHITE,
            )
        )
        
        # Основная компоновка
        self.controls = [
            ft.Text("🐱 vs 🐶 Классификатор изображений", size=20, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            
            # Блок выбора файла
            ft.Row([
                ft.ElevatedButton(
                    "📂 Выбрать изображение",
                    on_click=lambda _: self.picker.pick_files(
                        allow_multiple=False,
                        allowed_extensions=["jpg", "jpeg", "png"]
                    ),
                    icon=ft.icons.FOLDER_OPEN
                ),
                self.progress_ring,
            ], alignment=ft.MainAxisAlignment.CENTER),
            
            # Превью изображения
            ft.Container(
                content=self.image_preview,
                padding=10,
                border=ft.border.all(1, ft.colors.GREY_400),
                border_radius=8,
                alignment=ft.alignment.center
            ),
            
            # Кнопка классификации
            ft.Row([self.classify_button], alignment=ft.MainAxisAlignment.CENTER),
            
            # Результат
            ft.Container(
                content=self.result_text,
                padding=15,
                bgcolor=ft.colors.GREY_100,
                border_radius=8,
                visible=False
            ),
        ]
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.spacing = 15
