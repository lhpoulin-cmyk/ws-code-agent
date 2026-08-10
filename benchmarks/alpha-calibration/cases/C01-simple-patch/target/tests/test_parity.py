import unittest

from src.parity import is_even


class ParityTests(unittest.TestCase):
    def test_two_is_even(self) -> None:
        self.assertTrue(is_even(2))

    def test_three_is_not_even(self) -> None:
        self.assertFalse(is_even(3))


if __name__ == "__main__":
    unittest.main()
