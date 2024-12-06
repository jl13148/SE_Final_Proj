from unittest.mock import patch, MagicMock
from tests.base import BaseTestCase

class TestCompanionRoutes(BaseTestCase):
    def test_companion_setup_get(self):
        """Test GET request to companion setup page"""
        self.test_user.user_type = 'COMPANION'
        
        with patch('app.render_template') as mock_render:
            mock_render.return_value = 'companion setup page'
            response = self.client.get('/companion/setup')
            
            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_with('pages/companion_setup.html', form=ANY)
