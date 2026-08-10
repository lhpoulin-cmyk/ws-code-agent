import unittest

from src.parity import is_even


class ParityOracle(unittest.TestCase):
    def test_zero_and_negative_even_values(self) -> None:
        self.assertTrue(is_even(0))
        self.assertTrue(is_even(-4))


if __name__ == "__main__":
    unittest.main()
