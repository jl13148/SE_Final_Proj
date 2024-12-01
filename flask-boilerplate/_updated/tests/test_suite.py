import unittest
import coverage
import sys
import os

def run_tests_with_coverage():
    """Run tests with coverage reporting"""
    # Start coverage
    cov = coverage.Coverage(
        branch=True,
        include=['app/*'],
        omit=['tests/*', 'app/templates/*']
    )
    cov.start()

    # Create test suite
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern='test_*.py')

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Stop coverage
    cov.stop()
    cov.save()

    # Print coverage report
    print('\nCoverage Summary:')
    cov.report()

    # Generate XML report for CI
    cov.xml_report()

    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests_with_coverage()
    sys.exit(not success)