import pytest
import pandas as pd
from data_loader import DataLoader
from logic_validator import LogicValidator
from materiality import MaterialityEstimator
import numpy as np

@pytest.mark.integration
def test_pipeline_data_validation_materiality(tmp_path):
    """
    Интеграционный тест: загрузка → логическая валидация → оценка существенности.
    Проверяем, что логические ошибки корректно подсчитываются и влияют на материальность.
    """
    # Создаём тестовый DataFrame с явными ошибками
    df_test = pd.DataFrame({
        'дебет': [100, 0, 200, 0],
        'кредит': [50, 0, 100, 150],
        'сумма': [150, 0, 300, 150],  # вторая строка – нулевая сумма
        'дата': ['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04'],
        'описание': ['a', '', 'c', 'd']  # вторая строка – пустое описание
    })
    file = tmp_path / "test_with_errors.xlsx"
    df_test.to_excel(file, index=False)

    # 1. Загрузка
    df, err, _ = DataLoader.load_file(str(file))
    assert err is None

    # 2. Логическая валидация
    logic_errors, count = LogicValidator.validate(df)
    assert count >= 2  # ожидаем как минимум два типа ошибок (нулевая сумма и пустое описание)

    # 3. Оценка существенности (с искусственными аномалиями)
    # Создаём фиктивные аномальные скоры: пусть первая и третья строки аномальны
    scores = np.array([0.96, 0.5, 0.97, 0.4])
    balance = 10000
    percent, color, detail = MaterialityEstimator.compute_materiality(scores, df, balance, threshold=0.95)
    # Сумма ошибок = только строки с score >= 0.95 → строки 0 и 2 → 150 + 300 = 450
    assert percent == pytest.approx(4.5)  # 450 / 10000 * 100 = 4.5%
    assert color == "зеленый"