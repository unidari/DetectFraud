import pytest
import pandas as pd
from data_loader import DataLoader
from feature_extractor import FeatureExtractor
from anomaly_detector import AnomalyDetector
from logic_validator import LogicValidator

@pytest.mark.integration
def test_full_pipeline(tmp_path):
    # Создаём тестовый Excel
    df_test = pd.DataFrame({
        'дебет': [100, 200, 0],
        'кредит': [50, 0, 150],
        'сумма': [150, 200, 150],
        'дата': ['2025-01-01', '2025-01-02', '2025-01-03'],
        'описание': ['a', 'b', 'c']
    })
    file = tmp_path / "test.xlsx"
    df_test.to_excel(file, index=False)

    # 1. Загрузка
    df, err, _ = DataLoader.load_file(str(file))
    assert err is None

    # 2. Признаки
    features = FeatureExtractor.extract_features(df)
    assert features.shape[0] == len(df)

    # 3. Детектор
    detector = AnomalyDetector()
    scores = detector.fit_predict(features)
    assert len(scores) == len(df)

    # 4. Логическая проверка
    logic_df, count = LogicValidator.validate(df)
    assert logic_df is not None