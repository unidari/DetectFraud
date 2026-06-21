# tests/conftest.py
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication


# Добавляем корневую папку проекта (где лежат src/ и tests/)
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Добавляем папку src/, чтобы импорты вида 'from data_loader import ...' работали
sys.path.insert(0, str(root_dir / "src"))

# ------------------------------------------------------------
# Фикстуры для данных
# ------------------------------------------------------------

@pytest.fixture
def sample_df():
    """
    Возвращает небольшой DataFrame с корректными колонками
    для использования в тестах модулей.
    """
    df = pd.DataFrame({
        'дебет': [100, 200, 0, 500],
        'кредит': [50, 0, 150, 100],
        'сумма': [150, 200, 150, 600],
        'дата': pd.to_datetime(['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04']),
        'описание': ['test1', 'test2', 'test3', 'test4']
    })
    return df

@pytest.fixture
def sample_df_with_errors():
    """
    DataFrame с явными логическими ошибками для тестирования валидатора.
    """
    df = pd.DataFrame({
        'дебет': [100, 0, 200, 0],
        'кредит': [50, 0, 100, 150],
        'сумма': [150, 0, 300, 150],
        'дата': pd.to_datetime(['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04']),
        'описание': ['a', '', 'c', 'd']
    })
    return df

@pytest.fixture
def sample_file_path(tmp_path, sample_df):
    """
    Создаёт временный Excel-файл с sample_df и возвращает его путь.
    """
    file_path = tmp_path / "sample.xlsx"
    sample_df.to_excel(file_path, index=False)
    return str(file_path)

@pytest.fixture
def sample_file_with_errors(tmp_path, sample_df_with_errors):
    """
    Создаёт временный Excel-файл с ошибками для тестов валидации.
    """
    file_path = tmp_path / "sample_errors.xlsx"
    sample_df_with_errors.to_excel(file_path, index=False)
    return str(file_path)

# ------------------------------------------------------------
# Фикстуры для баланса и порога
# ------------------------------------------------------------

@pytest.fixture
def balance_currency():
    """Тестовая валюта баланса."""
    return 1000000.0

@pytest.fixture
def threshold():
    """Порог аномальности по умолчанию для тестов."""
    return 0.95

# ------------------------------------------------------------
# Фикстуры для Qt (системные тесты GUI)
# ------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    """
    Создаёт экземпляр QApplication для всех GUI-тестов (один раз на сессию).
    Это предотвращает создание нескольких экземпляров QApplication.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    # В тестах отключаем отображение окон, чтобы они не мелькали
    app.setAttribute(Qt.AA_DontShowIconsInMenus, True)
    return app

# ------------------------------------------------------------
# Хуки pytest для настройки маркеров и игнорирования предупреждений
# ------------------------------------------------------------

def pytest_configure(config):
    """
    Хук, который выполняется при старте pytest.
    Добавляем кастомные маркеры (они уже объявлены в pytest.ini, но дублируем для надёжности).
    """
    config.addinivalue_line(
        "markers", "unit: Модульные тесты"
    )
    config.addinivalue_line(
        "markers", "integration: Интеграционные тесты"
    )
    config.addinivalue_line(
        "markers", "system: Системные тесты (GUI)"
    )
    config.addinivalue_line(
        "markers", "performance: Нагрузочные тесты"
    )
    config.addinivalue_line(
        "markers", "regression: Регрессионные тесты"
    )
    config.addinivalue_line(
        "markers", "acceptance: Приёмочные тесты"
    )
    config.addinivalue_line(
        "markers", "validation: Валидационные тесты"
    )

# ------------------------------------------------------------
# Опционально: переопределение опций командной строки
# ------------------------------------------------------------

def pytest_addoption(parser):
    """
    Добавляем кастомные опции командной строки, чтобы можно было,
    например, задать порог аномальности при запуске тестов.
    """
    parser.addoption(
        "--threshold",
        action="store",
        default="0.95",
        help="Установить порог аномальности (по умолчанию 0.95)"
    )

@pytest.fixture
def threshold_from_cli(request):
    """
    Фикстура, которая возвращает значение порога из командной строки.
    Использование: def test_something(threshold_from_cli):
    """
    return float(request.config.getoption("--threshold"))

# ------------------------------------------------------------
# Настройка логирования (опционально)
# ------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_logging():
    """
    Автоматическая настройка логирования для всех тестов.
    Если нужно отключить логи, можно закомментировать.
    """
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Возвращаем None, т.к. фикстура используется только для побочного эффекта