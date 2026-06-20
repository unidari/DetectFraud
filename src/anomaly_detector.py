# -*- coding: utf-8 -*-
from sklearn.ensemble import IsolationForest

class AnomalyDetector:
    def __init__(self, contamination='auto', random_state=42,
                 n_estimators=100, max_samples='auto'):
        """
        Параметры Isolation Forest можно менять при создании объекта,
        но в данном проекте они не вынесены в интерфейс.
        """
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1,
            n_estimators=n_estimators,
            max_samples=max_samples
        )

    def fit_predict(self, features):
        """Обучает и возвращает аномальный score [0..1] для каждой строки."""
        self.model.fit(features)
        scores = self.model.score_samples(features)
        anomaly_score = 1 - (scores - scores.min()) / (scores.max() - scores.min() + 1e-10)
        return anomaly_score