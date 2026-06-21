import pytest
import pandas as pd
import numpy as np
from data_loader import DataLoader
from feature_extractor import FeatureExtractor
from anomaly_detector import AnomalyDetector
from logic_validator import LogicValidator
from materiality import MaterialityEstimator

@pytest.mark.regression
def test_critical_flow_anomaly_detection(tmp_path):
    """
    Регрессионный тест: полный пайплайн на данных с известными аномалиями.
    Этот сценарий должен всегда проходить, иначе что-то сломано в ядре.
    """
    # Генерируем простой набор с одной явной аномалией (сумма > 1000)
    df_test = pd.DataFrame({
        'дебет': [100, 200, 5000],
        'кредит': [50, 100, 0],
        'сумма': [150, 300, 5000],
        'дата': ['2025-01-01', '2025-01-02', '2025-01-03'],
        'описание': ['a', 'b', 'c']
    })
    file = tmp_path / "regression_test.xlsx"
    df_test.to_excel(file, index=False)

    # Загрузка
    df, err, _ = DataLoader.load_file(str(file))
    assert err is None

    # Признаки
    features = FeatureExtractor.extract_features(df)
    assert features.shape[0] == 3

    # Детектор
    detector = AnomalyDetector()
    scores = detector.fit_predict(features)
    assert len(scores) == 3

    # Проверяем, что аномалия (третья строка) получила высокий скор
    # Ожидаем, что третий скор будет одним из самых высоких (не строго, но для регрессии важно, что он > 0.5)
    assert scores[2] > 0.5

    # Логические ошибки – их быть не должно (кроме возможных односторонних, но тут нет)
    logic_df, count = LogicValidator.validate(df)
    # Здесь мы не ожидаем ошибок, кроме, возможно, односторонней (третья строка: только дебет)
    # Это допустимо, но для простоты проверим, что нет критических ошибок (сумма <=0 и т.п.)
    assert not (logic_df['Ошибки'].str.contains('Сумма <=0').any())

    # Оценка существенности
    balance = 10000
    percent, color, _ = MaterialityEstimator.compute_materiality(scores, df, balance, threshold=0.95)
    # Сумма ошибок при пороге 0.95 – только если третий скор >= 0.95, тогда ошибка 5000 -> 50% (красный)
    # Проверим, что цвет не зелёный (т.е. ошибка существенна)
    assert color != "зеленый"