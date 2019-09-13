import main
import unittest


class TestCase01(unittest.TestCase):
    def setUp(self):
        pass

    def check_01(self):
        pass


def allTests():
    runner = unittest.TextTestRunner(descriptions=0, verbosity=2)
    runner.run(unittest.TestSuite((unittest.makeSuite(TestCase01, 'check'),)))


if __name__ == '__main__':
    allTests()