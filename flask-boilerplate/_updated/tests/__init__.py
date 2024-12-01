import unittest
from tests.unit.services.test_medication_service import TestMedicationService
from tests.integration.test_medication_routes import TestMedicationRoutes

def create_test_suite():
    """Create the test suite that includes all tests"""
    suite = unittest.TestSuite()
    
    # Add test suites for each test class
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMedicationService))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMedicationRoutes))
    
    return suite

if __name__ == '__main__':
    # Run all tests
    runner = unittest.TextTestRunner(verbosity=2)
    test_suite = create_test_suite()
    runner.run(test_suite)