# tests/__init__.py
import unittest

# Integration Tests
from tests.integration.test_medication_routes import TestMedicationRoutes
from tests.integration.test_health_routes import TestHealthRoutes
from tests.integration.test_companion_routes import TestCompanionRoutes
from tests.integration.test_connection_routes import TestConnectionRoutes

# Service Tests
from tests.unit.services.test_medication_service import TestMedicationService
from tests.unit.services.test_health_service import TestHealthService
from tests.unit.services.test_medication_manager import TestMedicationManager
from tests.unit.services.test_auth_service import TestAuthService
# from tests.unit.services.test_companion_service import TestCompanionService
# from tests.unit.services.test_connection_service import TestConnectionService

# Model Tests
from tests.unit.models.test_models import TestUserModel, TestNotificationModel
from tests.unit.models.test_medication import TestMedicationModel
from tests.unit.models.test_health import TestHealthModel
# from tests.unit.models.test_companion import TestCompanionModel
# from tests.unit.models.test_connection import TestConnectionModel

# Controller Test
from tests.unit.controllers.test_report_controller import TestReportController

def create_test_suite():
    suite = unittest.TestSuite()
    
    # Add Integration Tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMedicationRoutes))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHealthRoutes))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCompanionRoutes))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConnectionRoutes))
    
    # Add Service Tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMedicationService))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMedicationManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHealthService))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAuthService))
    # suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCompanionService))
    # suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConnectionService))
    
    # Add Model Tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestUserModel))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestNotificationModel))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMedicationModel))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHealthModel))
    # suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCompanionModel))
    # suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConnectionModel))

    # Add Controller Tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestReportController))
    
    return suite

if __name__ == '__main__':
    # Run all tests
    runner = unittest.TextTestRunner(verbosity=2)
    test_suite = create_test_suite()
    runner.run(test_suite)