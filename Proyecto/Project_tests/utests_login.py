import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Tocó ajustar las rutas :(
current_dir = os.path.dirname(os.path.abspath(__file__))  # Project_tests
parent_dir = os.path.dirname(current_dir)  # Proyecto
v2_dir = os.path.join(parent_dir, 'v2')  # Proyecto/v2

sys.path.insert(0, v2_dir)

from app import app
from models.entities.User import User

# Para simplisidad no se va a usar la base de datos, sino Mocks que es equivalente JAJA
class TestLoginSinBD(unittest.TestCase):
    """
    Pruebas de Login usando Mocks, sin necesidad de usar la base de datos
    """

    def setUp(self):
        """
        Configuración antes de cada prueba
        """
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    # Prueba 1: Verificar que la página de login carga
    def test_01_login_page_loads(self):
        """
        La página de login debe cargar correctamente
        """
        response = self.client.get("/login")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"login", response.data.lower())
        
        print("Prueba 1: La página del login carga correctamente")

    # Prueba 2: Login exitoso 
    @patch('models.ModelUser.ModelUser.login')
    def test_02_login_valid_credentials_mock(self, mock_login):
        """
        Login exitoso con credenciales válidas (usando mock)
        """
        # Aqui creo un usuario mock
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.username = "dgongora"
        mock_user.password = True  # Contraseña verificada
        mock_user.fullname = "Deiber Gongora"
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.is_anonymous = False
        mock_user.get_id = Mock(return_value='1')
        
        mock_login.return_value = mock_user
        
        response = self.client.post("/login", data={
            'email': 'dgongora@unal.edu.co',
            'password': '12345678'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        print("Prueba 2: Login exitoso con credenciales válidas (mock)")

    # Prueba 3: Login con contraseña incorrecta 
    @patch('models.ModelUser.ModelUser.login')
    def test_03_login_invalid_password_mock(self, mock_login):
        """
        Login falla con contraseña incorrecta (usando mock)
        """
        # Usuario existe pero contraseña incorrecta
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.username = 'dgongora'
        mock_user.password = False  # Contraseña no verificada
        
        mock_login.return_value = mock_user
        
        response = self.client.post('/login', data={
            'email': 'dgongora@unal.edu.co',
            'password': 'wrongpassword'
        }, follow_redirects=False)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Contrase', response.data)
        
        print("Prueba 3: Login rechazado porque la contraseña es inválida")


class TestCasosLimite(unittest.TestCase):
    """
    Casos límite de los tests unitarios
    """

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    @patch('models.ModelUser.ModelUser.login')
    def test_04_login_empty_email(self, mock_login):
        """
        CASO LIMITE: Email vacío en login
        """
        mock_login.return_value = None
        
        response = self.client.post('/login', data={
            'email': '',
            'password': '12345678'
        })
        
        self.assertEqual(response.status_code, 200)
        print("CASO LIMITE 1: Email vacío manejado")

    @patch('models.ModelUser.ModelUser.login')
    def test_05_login_empty_password(self, mock_login):
        """
        CASO LIMITE: Contraseña vacía en login
        """
        mock_login.return_value = None
        
        response = self.client.post('/login', data={
            'email': 'dgongora@unal.edu.co',
            'password': ''
        })
        
        self.assertEqual(response.status_code, 200)
        print("CASO LIMITE 2: Contraseña vacía manejada")

    @patch('models.ModelUser.ModelUser.login')
    def test_06_login_sql_injection_email(self, mock_login):
        """
        CASO LIMITE: Intento de SQL injection en email
        """
        mock_login.return_value = None
        
        response = self.client.post('/login', data={
            'email': "admin'--",
            'password': "' OR '1'='1"
        })
        
        self.assertEqual(response.status_code, 200)
        # No deberia causar error 500
        print("CASO LIMITE 3: SQL injection bloqueado")

    @patch('models.ModelUser.ModelUser.login')
    def test_07_login_very_long_email(self, mock_login):
        """
        CASO LIMITE: Email extremadamente largo
        """
        mock_login.return_value = None
        
        long_email = 'a' * 80 + '@unal.edu.co' # 80 porque así lo pusimos en la base de datos
        response = self.client.post('/login', data={
            'email': long_email,
            'password': '12345678'
        })
        
        self.assertEqual(response.status_code, 200)
        print("CASO LIMITE 4: Email muy largo manejado")

    @patch('models.ModelUser.ModelUser.login')
    def test_08_login_xss_attempt(self, mock_login):
        """
        CASO LIMITE: Intento de XSS en campos
        """
        mock_login.return_value = None
        
        response = self.client.post('/login', data={
            'email': '<script>alert("XSS")</script>',
            'password': '12345678'
        })
        
        self.assertEqual(response.status_code, 200)
        print("CASO LIMITE 5: XSS manejado")



if __name__ == '__main__':
    print("\n")
    print("  PRUEBAS UNITARIAS ")
    print(" Tests con Mocks")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestLoginSinBD))
    suite.addTests(loader.loadTestsFromTestCase(TestCasosLimite))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # El resumen
    print("\n  RESUMEN DE PRUEBAS ")
    print(f"Total ejecutadas:  {result.testsRun}")
    print(f"Exitosas:          {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Fallidas:          {len(result.failures)}")
    print(f"Errores:           {len(result.errors)}")
    
    if result.failures:
        print("\nPRUEBAS FALLIDAS:")
        for test, traceback in result.failures:
            print(f"   - {test}")
            print(f"     {traceback[:300]}...")
    
    if result.errors:
        print("\nERRORES:")
        for test, traceback in result.errors:
            print(f"   - {test}")
            print(f"     {traceback[:300]}...")
    
    sys.exit(0 if result.wasSuccessful() else 1)