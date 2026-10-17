"""Waiting for the provider usage limit must back off instead of retrying every minute."""
from LuanAppTools.service.controller import usage_retry_delay


def test_delay_doubles_each_consecutive_wait_and_is_capped():
    assert [usage_retry_delay(60, n) for n in range(1, 9)] == [60, 120, 240, 480, 960, 1800, 1800, 1800]


def test_short_test_intervals_are_kept_short():
    assert usage_retry_delay(0.1, 1) == 0.1
    assert usage_retry_delay(0.1, 3) == 0.4
    assert usage_retry_delay(0.1, 500) <= 1800
