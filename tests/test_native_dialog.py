import unittest

from backend.native_dialog import _is_valid_pin, _pin_icon_path


class NativeDialogTests(unittest.TestCase):
    def test_pin_dialog_uses_the_official_favicon(self):
        icon_path = _pin_icon_path()

        self.assertEqual(icon_path.name, "favicon.ico")
        self.assertEqual(icon_path.parent.name, "frontend")
        self.assertTrue(icon_path.is_file())

    def test_accepts_a_pin_with_allowed_length_and_digits(self):
        self.assertTrue(_is_valid_pin("1" * 4))
        self.assertTrue(_is_valid_pin("1" * 6))

    def test_rejects_malformed_pin_values(self):
        self.assertFalse(_is_valid_pin(None))
        self.assertFalse(_is_valid_pin(""))
        self.assertFalse(_is_valid_pin("1" * 3))
        self.assertFalse(_is_valid_pin("1" * 7))
        self.assertFalse(_is_valid_pin("abcd"))


if __name__ == "__main__":
    unittest.main()
