import unittest
import coverage
import sys
import os

def run_tests_with_coverage():
    """Run tests with coverage reporting"""
    # Start coverage
    cov = coverage.Coverage(
        branch=True,
        include=[
            'app/*',
            'app/controllers/*',
            'app/services/*',
            'app/models/*'
        ],
        omit=[
            'tests/*', 
            'app/templates/*',
            'app/static/*'
        ]
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

    # Generate HTML report
    html_report_dir = os.path.join(start_dir, 'htmlcov')
    cov.html_report(directory=html_report_dir)
    print(f'\nHTML coverage report generated in: {html_report_dir}')
    
    # Try to open the report in browser
    try:
        index_path = os.path.join(html_report_dir, 'index.html')
        webbrowser.open('file://' + os.path.abspath(index_path))
    except:
        print("Could not automatically open the report in browser.")
        print(f"Please open {index_path} in your browser to view the detailed report.")

    # Generate XML report for CI
    cov.xml_report()

    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests_with_coverage()
    sys.exit(not success)