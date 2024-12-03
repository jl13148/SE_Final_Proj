# tests/test_suite.py
import unittest
import coverage
import sys
import os
import webbrowser

def run_tests_with_coverage():
    """Run tests with coverage reporting"""
    # Initialize coverage without exclude_lines
    cov = coverage.Coverage(
        branch=True,
        source=['app'],  # Use source instead of include
        omit=[
            'tests/*',
            'app/forms.py',
            'app/extensions.py',
            'app/templates/*',
            'app/static/*',
            '*/__pycache__/*',
            '*.pyc',
            '*/__init__.py',  # Ignore all __init__.py files
            '**/__init__.py'  # Alternative pattern to catch nested __init__.py files
        ]
    )
    
    # Set exclude_lines programmatically
    cov.set_option("report:exclude_lines", [
        'pragma: no cover',
        'def __repr__',
        'if self\\.debug',
        'raise AssertionError',
        # 'raise NotImplementedError',
        r'^import .*$',
        r'^from .* import .*$',
        # r'^class .*\(.*\):$',
        # r'@.*',
        # r'if TYPE_CHECKING:',
        # r'^[a-zA-Z_][a-zA-Z0-9_]* *: *[a-zA-Z_][a-zA-Z0-9_]* *$',
    ])

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

    # Print coverage report with more detail
    print('\nCoverage Summary:')
    cov.report(show_missing=True)  # Show which lines are missing

    # Generate HTML report
    html_report_dir = os.path.join(start_dir, 'htmlcov')
    cov.html_report(directory=html_report_dir)
    print(f'\nHTML coverage report generated in: {html_report_dir}')

    # Try to open the report in browser
    try:
        index_path = os.path.join(html_report_dir, 'index.html')
        webbrowser.open('file://' + os.path.abspath(index_path))
    except Exception as e:
        print("Could not automatically open the report in browser.")
        print(f"Please open {index_path} in your browser to view the detailed report.")
        print(f"Error: {e}")

    # Generate XML report for CI
    cov.xml_report()

    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests_with_coverage()
    sys.exit(not success)
