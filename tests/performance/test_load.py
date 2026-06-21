import pytest
import pandas as pd
import numpy as np
from data_loader import DataLoader
from feature_extractor import FeatureExtractor
from anomaly_detector import AnomalyDetector

@pytest.mark.performance
def test_large_dataset(benchmark, tmp_path):
    # Генерируем 50 000 записей
    n = 50000
    df_large = pd.DataFrame({
        'дебет': np.random.randint(1, 1000, n),
        'кредит': np.random.randint(1, 1000, n),
        'сумма': np.random.randint(1, 10000, n),
        'дата': pd.date_range('2025-01-01', periods=n),
        'описание': ['test'] * n
    })
    file = tmp_path / "large.xlsx"
    df_large.to_excel(file, index=False)

    def load_and_analyze():
        df, err, _ = DataLoader.load_file(str(file))
        assert err is None
        features = FeatureExtractor.extract_features(df)
        detector = AnomalyDetector()
        scores = detector.fit_predict(features)
        return scores

    result = benchmark(load_and_analyze)
    assert len(result) == n