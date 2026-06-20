# -*- coding: utf-8 -*-
"""
Вспомогательные функции: типы счетов, проверка круглых сумм.
"""

ACTIVE_ACCOUNT_PREFIXES = ('01', '03', '04', '08', '10', '19', '20', '23', '25', '26', '29', '41', '43', '44', '45', '50', '51', '52', '58')
PASSIVE_ACCOUNT_PREFIXES = ('02', '42', '66', '67', '68', '69', '70', '80', '82', '83', '86', '96', '98')

def get_account_type(account):
    """Возвращает 'active', 'passive' или None."""
    if not account or not isinstance(account, str):
        return None
    acc_str = str(account).split('.')[0]
    if acc_str.startswith(ACTIVE_ACCOUNT_PREFIXES):
        return 'active'
    if acc_str.startswith(PASSIVE_ACCOUNT_PREFIXES):
        return 'passive'
    return None

def is_round_sum(amount, base=1000):
    """Проверяет, является ли сумма 'круглой' (кратной base)."""
    try:
        return float(amount) % base == 0
    except:
        return False