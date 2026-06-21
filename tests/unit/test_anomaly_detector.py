import pytest
import numpy as np
from anomaly_detector import AnomalyDetector

@pytest.mark.unit
class TestAnomalyDetector:
    def test_fit_predict_shape(self):
        X = np.random.randn(100, 5)
        detector = AnomalyDetector()
        scores = detector.fit_predict(X)
        assert len(scores) == 100
        assert scores.min() >= 0
        assert scores.max() <= 1

    def test_fit_predict_with_single_sample(self):
        X = np.random.randn(1, 5)
        detector = AnomalyDetector()
        scores = detector.fit_predict(X)
        assert len(scores) == 1
        assert scores[0] == 1.0  # одна точка – аномалия? фактически всегда 1