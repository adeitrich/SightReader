import unittest

from sightreader.instruments import program_for_instrument


class InstrumentTests(unittest.TestCase):
    def test_known_instruments(self):
        self.assertEqual(program_for_instrument("piano"), 0)
        self.assertEqual(program_for_instrument("tenor sax"), 66)
        self.assertEqual(program_for_instrument("tuba"), 58)

    def test_unknown_instrument_raises(self):
        with self.assertRaises(ValueError):
            program_for_instrument("kazoo")


if __name__ == "__main__":
    unittest.main()
