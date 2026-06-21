import pytest
from utils import get_account_type, is_round_sum

@pytest.mark.unit
class TestUtils:
    @pytest.mark.parametrize("account,expected", [
        ("01.2", "active"),
        ("51.1", "active"),
        ("70.3", "passive"),
        ("80", "passive"),
        ("99", None),
        ("", None),
        (None, None),
    ])
    def test_get_account_type(self, account, expected):
        assert get_account_type(account) == expected

    @pytest.mark.parametrize("amount,base,expected", [
        (1000, 1000, True),
        (2000, 1000, True),
        (1500, 1000, False),
        (0, 1000, True),
        ("1000", 1000, True),
        ("abc", 1000, False),
        (None, 1000, False),
    ])
    def test_is_round_sum(self, amount, base, expected):
        assert is_round_sum(amount, base) == expected