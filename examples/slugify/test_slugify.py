import unittest
from slugify import slugify


class SlugifyTest(unittest.TestCase):
    def test_examples(self):
        for source, expected in [("", ""), ("  Hello, world!  ", "hello-world"),
                                 ("Привет, мир!", "привет-мир"), ("ＡＢＣ １２", "abc-12"),
                                 ("Straße_name", "strasse-name"), ("---", "")]:
            with self.subTest(source=source):
                self.assertEqual(slugify(source), expected)


if __name__ == "__main__":
    unittest.main()
