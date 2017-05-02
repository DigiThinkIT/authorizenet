import unittest
import os

def run(verbosity=3):
	suite = unittest.TestSuite()
	import_path = os.path.dirname(__file__)
	for all_test_suite in unittest.defaultTestLoader.discover(import_path, pattern='test_*.py'):
		for test_suite in all_test_suite:
			suite.addTests(test_suite)

	runner = unittest.TextTestRunner(verbosity = verbosity)
	runner.run(suite)
