# -*- coding: utf-8 -*-

class MaterialityEstimator:
    @staticmethod
    def compute_materiality(anomaly_scores, df, balance_currency, threshold=0.95):
        if balance_currency is None or balance_currency <= 0:
            return None, "серый", "Валюта баланса не задана"
        mask = anomaly_scores >= threshold
        error_sum = df.loc[mask, 'сумма'].sum()
        percent = (error_sum / balance_currency) * 100
        if percent < 5:
            color = "зеленый"
        elif percent < 10:
            color = "желтый"
        else:
            color = "красный"
        detail = f"{percent:.2f}% (сумма ошибок {error_sum:,.2f} от валюты {balance_currency:,.2f})"
        return percent, color, detail