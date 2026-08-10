import unittest

from src.greeting import greeting


class GreetingTests(unittest.TestCase):
    def test_greeting_uses_hello(self) -> None:
        self.assertEqual(greeting("Ada"), "Hello, Ada!")


if __name__ == "__main__":
    unittest.main()
