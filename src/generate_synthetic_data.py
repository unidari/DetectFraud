# -*- coding: utf-8 -*-
"""
Генератор синтетических бухгалтерских проводок для тестирования DetecredFraud.
Создаёт файл synthetic_transactions.xlsx с колонками:
    Дебет, Кредит, Дата, Описание (сумма вычисляется как max(дебет, кредит))
Включает логические ошибки и аномалии.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Настройки
NUM_ROWS = 1000                     # количество проводок
OUTPUT_FILE = "synthetic_transactions.xlsx"
SEED = 42                           # для воспроизводимости
random.seed(SEED)
np.random.seed(SEED)

# Определим типы счетов (активные/пассивные)
# Формат: номер счёта -> тип
ACCOUNT_TYPES = {
    '01': 'active',
    '10': 'active',
    '20': 'active',
    '41': 'active',
    '50': 'active',
    '51': 'active',
    '60': 'active',   # расчёты с поставщиками (активно-пассивный, упростим)
    '62': 'active',   # расчёты с покупателями (активно-пассивный)
    '68': 'passive',  # расчёты с бюджетом
    '69': 'passive',  # страховые взносы
    '70': 'passive',  # зарплата
    '80': 'passive',  # уставный капитал
    '84': 'passive',  # нераспределённая прибыль
    '90': 'passive',  # продажи
    '91': 'active',   # прочие доходы/расходы (упрощённо)
}

# Расширим список счетов с субсчетами (для реалистичности)
ACCOUNTS = []
for acc, typ in ACCOUNT_TYPES.items():
    if typ == 'active':
        # добавим субсчета
        ACCOUNTS.extend([f"{acc}.{i}" for i in range(1, 4)])
    else:
        ACCOUNTS.extend([f"{acc}.{i}" for i in range(1, 4)])
# Добавим ещё несколько без субсчетов
ACCOUNTS.extend(['01', '10', '20', '41', '50', '51', '60', '62', '68', '69', '70', '80', '84', '90', '91'])

# Убедимся, что счета уникальны
ACCOUNTS = list(set(ACCOUNTS))

# Функция для получения типа счета (активный/пассивный)
def get_account_type(acc):
    # acc может быть с субсчетом, берём основную часть до точки
    base = acc.split('.')[0]
    return ACCOUNT_TYPES.get(base, 'active')  # по умолчанию активный

# Генерация дат: последние 3 месяца
start_date = datetime.now() - timedelta(days=90)
end_date = datetime.now()

def random_date():
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)

# Генерация описаний (реалистичные)
DESCRIPTIONS = [
    "Оплата поставщику за материалы",
    "Поступление товаров от поставщика",
    "Реализация продукции покупателю",
    "Начисление заработной платы",
    "Уплата налогов в бюджет",
    "Поступление денежных средств на расчётный счёт",
    "Выдача денежных средств из кассы",
    "Списание материалов в производство",
    "Начисление амортизации основных средств",
    "Отражение прибыли от продаж",
    "Прочие расходы",
    "Прочие доходы",
    "Перечисление страховых взносов",
    "Выплата дивидендов",
    "Внесение в уставный капитал",
]

# Генерация проводок
data = []
for _ in range(NUM_ROWS):
    # Выбираем случайный дебетовый и кредитовый счёт (разные)
    debit_acc = random.choice(ACCOUNTS)
    credit_acc = random.choice(ACCOUNTS)
    while credit_acc == debit_acc:
        credit_acc = random.choice(ACCOUNTS)

    # Сумма (логарифмическое распределение, чтобы были мелкие и крупные)
    amount = np.random.lognormal(mean=6, sigma=2)  # среднее ~ 1000
    amount = round(amount, 2)

    # С вероятностью 10% делаем одностороннюю проводку (только дебет или кредит)
    if random.random() < 0.1:
        if random.random() < 0.5:
            credit_acc = None
            amount = round(np.random.lognormal(mean=6, sigma=2), 2)
        else:
            debit_acc = None
            amount = round(np.random.lognormal(mean=6, sigma=2), 2)

    # Дата
    date = random_date()
    # Описание
    desc = random.choice(DESCRIPTIONS)

    # Заполняем строку
    row = {
        'Дебет': debit_acc if debit_acc else '',
        'Кредит': credit_acc if credit_acc else '',
        'Дата': date.strftime('%Y-%m-%d'),
        'Описание': desc,
        'Сумма': amount if debit_acc and credit_acc else (amount if debit_acc else 0) # для удобства
    }
    data.append(row)

# Преобразуем в DataFrame
df = pd.DataFrame(data)

# Добавим специальные аномалии
# 1. Отрицательная сумма (редко)
anomaly_idx = random.sample(range(len(df)), 10)
for idx in anomaly_idx:
    df.loc[idx, 'Сумма'] = -abs(df.loc[idx, 'Сумма']) * 0.5

# 2. Нулевая сумма (5 записей)
zero_indices = random.sample(range(len(df)), 5)
for idx in zero_indices:
    df.loc[idx, 'Сумма'] = 0

# 3. Отсутствие описания (10 записей)
no_desc_indices = random.sample(range(len(df)), 10)
for idx in no_desc_indices:
    df.loc[idx, 'Описание'] = ''

# 4. Некорректная дата (5 записей) – поставим NaT
bad_date_indices = random.sample(range(len(df)), 5)
for idx in bad_date_indices:
    df.loc[idx, 'Дата'] = 'неверная дата'

# 5. Дебет и кредит одинаковый счёт (5 записей)
same_account_indices = random.sample(range(len(df)), 5)
for idx in same_account_indices:
    acc = random.choice(ACCOUNTS)
    df.loc[idx, 'Дебет'] = acc
    df.loc[idx, 'Кредит'] = acc

# 6. Нарушение остатков: сделаем так, чтобы по некоторым активным счетам было кредитовое сальдо
# Для этого добавим несколько проводок с большим кредитом на активном счёте
active_accounts = [acc for acc in ACCOUNTS if get_account_type(acc) == 'active']
for _ in range(5):
    acc = random.choice(active_accounts)
    # Добавим проводку, где этот счёт кредитуется на крупную сумму, а дебетуется на другую
    new_row = {
        'Дебет': random.choice([a for a in ACCOUNTS if a != acc]),
        'Кредит': acc,
        'Дата': random_date().strftime('%Y-%m-%d'),
        'Описание': 'Аномальная проводка (нарушение сальдо)',
        'Сумма': round(np.random.lognormal(mean=8, sigma=2), 2)  # крупная сумма
    }
    # Заменяем df.append() на pd.concat()
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

# Сохраняем в Excel
df.to_excel(OUTPUT_FILE, index=False)
print(f"Сгенерировано {len(df)} проводок. Файл сохранён: {OUTPUT_FILE}")
print("Колонки:", df.columns.tolist())
print("Пример первых 5 строк:")
print(df.head())