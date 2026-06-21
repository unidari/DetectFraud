import pytest
import pandas as pd
import numpy as np
from feature_extractor import FeatureExtractor
from utils import get_account_type  # используется внутри

@pytest.mark.unit
class TestFeatureExtractor:
    def test_extract_features_basic(self):
        df = pd.DataFrame({
            'дебет': [100, 200, 0],
            'кредит': [0, 50, 150],
            'сумма': [100, 250, 150],
            'дата': pd.to_datetime(['2025-01-01 10:00', '2025-01-02 14:30', '2025-01-03 09:15']),
            'описание': ['a', 'b', 'c']
        })
        # Ожидаем, что функция добавит служебные колонки
        features = FeatureExtractor.extract_features(df)
        assert features.shape[0] == 3
        expected_cols = ['log_sum', 'hour', 'dayofweek', 'round_sum', 'pair_frequency',
                         'is_debit_only', 'is_credit_only', 'abnormal_balance_debit', 'abnormal_balance_credit']
        for col in expected_cols:
            assert col in features.columns
        # Проверка масштабирования – значения не должны быть все нулевые
        assert not np.allclose(features['log_sum'], 0)

    def test_extract_features_with_missing_date(self):
        df = pd.DataFrame({
            'дебет': [100],
            'кредит': [50],
            'сумма': [150],
            'дата': [pd.NaT],
            'описание': ['a']
        })
        features = FeatureExtractor.extract_features(df)
        # Вместо assert features.loc[0, 'hour'] == 12
        assert features.loc[0, 'hour'] == pytest.approx(0.0)
        assert features.loc[0, 'dayofweek'] == 0

    def test_pair_frequency(self):
        df = pd.DataFrame({
            'дебет': [100, 100, 200],
            'кредит': [50, 50, 100],
            'сумма': [150, 150, 300],
            'дата': pd.to_datetime(['2025-01-01', '2025-01-01', '2025-01-02']),
            'описание': ['a', 'a', 'b']
        })
        features = FeatureExtractor.extract_features(df)
        # После масштабирования среднее значение признака должно быть ≈0
        assert features['pair_frequency'].mean() == pytest.approx(0.0, abs=1e-6)