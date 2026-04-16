import pytest
from pathlib import Path
from app.model.classifier import CatDogClassifier
from app.services.exceptions import ModelNotLoadedError

@pytest.fixture
def classifier():
    """Фикстура с загруженной моделью (мокируйте для реальных тестов)"""
    clf = CatDogClassifier("assets/models/cat_dog_model.h5")
    clf.load()
    yield clf
    clf.unload()

def test_predict_returns_valid_structure(classifier):
    result = classifier.predict("assets/test_images/sample_cat.jpg")
    assert "class" in result
    assert "confidence" in result
    assert result["class"] in ["cat", "dog"]
    assert 0.0 <= result["confidence"] <= 1.0

def test_predict_raises_if_not_loaded():
    clf = CatDogClassifier()
    with pytest.raises(RuntimeError, match="not loaded"):
        clf.predict("any.jpg")

def test_preprocess_invalid_image():
    clf = CatDogClassifier()
    clf.load()
    with pytest.raises(ValueError):
        clf.predict("nonexistent.jpg")