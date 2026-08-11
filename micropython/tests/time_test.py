from time import secs_until_next_interval

_PASS = 0
_FAIL = 0


def assert_eq(dt, interval_min, expected):
    global _PASS, _FAIL
    result = secs_until_next_interval(dt, interval_min)
    if result == expected:
        _PASS += 1
    else:
        _FAIL += 1
        print("FAIL secs_until_next_interval({}, {}) => {} (expected {})".format(
            dt, interval_min, result, expected))


def test_secs_until_next_interval():
    # 17:01:32 — just past a boundary
    assert_eq((2026, 4, 6, 17, 1, 32, 0, 0),  5,  60*3+28)
    assert_eq((2026, 4, 6, 17, 1, 32, 0, 0), 10, 60*8+28)
    assert_eq((2026, 4, 6, 17, 1, 32, 0, 0), 15, 60*13+28)
    assert_eq((2026, 4, 6, 17, 1, 32, 0, 0), 20, 60*18+28)
    assert_eq((2026, 4, 6, 17, 1, 32, 0, 0), 30, 60*28+28)
    assert_eq((2026, 4, 6, 17, 1, 32, 0, 0), 60, 60*58+28)

    # 17:53:32 — near the end of the hour
    assert_eq((2026, 4, 6, 17, 53, 32, 0, 0),  5, 60*1+28)
    assert_eq((2026, 4, 6, 17, 53, 32, 0, 0), 10, 60*6+28)
    assert_eq((2026, 4, 6, 17, 53, 32, 0, 0), 15, 60*6+28)
    assert_eq((2026, 4, 6, 17, 53, 32, 0, 0), 20, 60*6+28)
    assert_eq((2026, 4, 6, 17, 53, 32, 0, 0), 30, 60*6+28)
    assert_eq((2026, 4, 6, 17, 53, 32, 0, 0), 60, 60*6+28)

    # 17:55:00 — exactly on a boundary
    assert_eq((2026, 4, 6, 17, 55, 0, 0, 0),  5, 60*5)
    assert_eq((2026, 4, 6, 17, 55, 0, 0, 0), 10, 60*5)
    assert_eq((2026, 4, 6, 17, 55, 0, 0, 0), 15, 60*5)
    assert_eq((2026, 4, 6, 17, 55, 0, 0, 0), 20, 60*5)
    assert_eq((2026, 4, 6, 17, 55, 0, 0, 0), 30, 60*5)
    assert_eq((2026, 4, 6, 17, 55, 0, 0, 0), 60, 60*5)


test_secs_until_next_interval()

if _FAIL:
    raise ValueError("{} test(s) failed ({} passed)".format(_FAIL, _PASS))
else:
    print("All {} tests passed".format(_PASS))