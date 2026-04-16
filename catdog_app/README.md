# 🐱🐶 CatDog Classifier Desktop App

Десктопное приложение для бинарной классификации изображений (коты/собаки).

## 🚀 Быстрый старт

```bash
# 1. Клонирование и установка
cd catdog_app
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Подготовка модели
# Поместите вашу обученную модель в: assets/models/cat_dog_model.h5

# 3. Запуск
python -m app.main
```

## 📁 Структура проекта
```
catdog_app/
├── app/
│   ├── main.py              # Точка входа
│   ├── ui/                  # Графический интерфейс (Flet)
│   │   └── main_window.py
│   ├── model/               # Модель классификации
│   │   ├── classifier.py
│   │   └── config.py
│   ├── services/            # Бизнес-логика
│   │   ├── prediction_service.py
│   │   ├── file_service.py
│   │   └── exceptions.py
│   └── utils/               # Вспомогательные утилиты
│       ├── logger.py
│       └── path_helper.py
├── assets/
│   ├── models/              # Файлы моделей
│   ├── test_images/         # Тестовые изображения
│   └── icons/               # Иконки приложения
├── tests/                   # Модульные тесты
├── requirements.txt
└── README.md
```

## ⚙️ Конфигурация
Параметры модели настраиваются в `app/model/config.py`:
- `input_size`: размер входа модели (по умолчанию 224×224)
- `threshold`: порог классификации (по умолчанию 0.5)
- `allowed_extensions`: поддерживаемые форматы (.jpg, .jpeg, .png)
- `max_file_size_mb`: максимальный размер файла (по умолчанию 10 MB)

## 🧪 Тестирование
```bash
pytest tests/ -v
```

## 📦 Сборка в EXE
```bash
pip install pyinstaller
pyi-makespec --onefile --windowed --name="CatDogClassifier" \
  --add-data "assets;assets" \
  --hidden-import="PIL._imaging" \
  --hidden-import="tensorflow" \
  app/main.py
pyinstaller CatDogClassifier.spec
```

## 🐛 Устранение неполадок
- **Модель не загружается**: проверьте путь в `config.py` и формат файла (.h5 для TF)
- **Ошибки импорта в сборке**: добавьте модуль в `--hidden-import` при сборке
- **Пути к ресурсам**: используйте `get_resource_path()` из `utils.path_helper`

## 📄 Лицензия
Учебный проект для лабораторной работы №7.