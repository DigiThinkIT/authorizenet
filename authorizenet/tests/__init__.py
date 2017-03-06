import unittest
import os

def run(verbosity=3):
    suite = unittest.TestSuite()
    for all_test_suite in unittest.defaultTestLoader.discover(os.path.dirname(__file__), pattern='test_*.py'):
        for test_suite in all_test_suite:
            print(test_suite)
            suite.addTests(test_suite)

    runner = unittest.TextTestRunner(verbosity = verbosity)
    runner.run(suite)
