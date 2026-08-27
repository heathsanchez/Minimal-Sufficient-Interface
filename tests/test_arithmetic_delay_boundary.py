import unittest


BASE = 10


def value_msd(digits):
    out = 0
    for d in digits:
        out = BASE * out + d
    return out


def first_sum_digit(a_digits, b_digits):
    width = len(a_digits)
    total = value_msd(a_digits) + value_msd(b_digits)
    # First digit of the fixed-width result modulo BASE^width. Any extra overflow
    # is handled separately; this position is exactly the one an MSD-first local
    # stream would try to emit first.
    return (total // (BASE ** (width - 1))) % BASE


def delayed_msd_counterexample(delay):
    """Two additions identical through delay+1 visible positions but with
    different required first output digits.

    An unseen final suffix creates a carry that propagates through a chain of
    sum-nine positions all the way back to the first output position.
    """
    width = delay + 2
    a0 = [0] + [9] * (width - 1)
    b0 = [0] * width
    a1 = list(a0)
    b1 = list(b0)
    b1[-1] = 1

    visible = delay + 1
    prefix0 = tuple(zip(a0[:visible], b0[:visible]))
    prefix1 = tuple(zip(a1[:visible], b1[:visible]))
    assert prefix0 == prefix1

    y0 = first_sum_digit(a0, b0)
    y1 = first_sum_digit(a1, b1)
    assert y0 != y1
    return {
        "delay": delay,
        "width": width,
        "visible_prefix": prefix0,
        "output_a": y0,
        "output_b": y1,
        "hidden_suffix_a": (a0[-1], b0[-1]),
        "hidden_suffix_b": (a1[-1], b1[-1]),
    }


class ArithmeticDelayBoundary(unittest.TestCase):
    def test_no_fixed_msd_output_delay_is_uniformly_sufficient(self):
        witnesses = []
        for delay in range(0, 33):
            w = delayed_msd_counterexample(delay)
            self.assertEqual(w["width"], delay + 2)
            self.assertNotEqual(w["output_a"], w["output_b"])
            witnesses.append(w)

        print(
            "arithmetic no-fixed-delay boundary: "
            f"tested_delays=0..32; first={witnesses[0]}; last={witnesses[-1]}"
        )


if __name__ == "__main__":
    unittest.main()
