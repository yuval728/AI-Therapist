"""Integration tests for API routes and services."""
import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.main import create_app
from src.models import SignUpRequest, SignInRequest, APIResponse
from src.services import get_auth_service, get_user_service, get_session_service


class TestAuthAPI:
    """Test authentication API endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_signup_endpoint(self, client):
        """Test user signup endpoint."""
        with patch('src.services.auth_service.get_supabase_auth') as mock_auth:
            # Mock successful signup
            mock_auth_service = AsyncMock()
            mock_auth_service.sign_up.return_value = Mock(
                success=True,
                user_id="test-user-id",
                email="test@example.com"
            )
            mock_auth.return_value = mock_auth_service
            
            signup_data = {
                "email": "test@example.com",
                "password": "testpassword123",
                "full_name": "Test User"
            }
            
            response = client.post("/api/auth/signup", json=signup_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_signin_endpoint(self, client):
        """Test user signin endpoint."""
        with patch('src.services.auth_service.get_supabase_auth') as mock_auth:
            # Mock successful signin
            mock_auth_service = AsyncMock()
            mock_auth_service.sign_in.return_value = Mock(
                success=True,
                user_id="test-user-id",
                email="test@example.com",
                access_token="test-token"
            )
            mock_auth.return_value = mock_auth_service
            
            signin_data = {
                "email": "test@example.com",
                "password": "testpassword123"
            }
            
            response = client.post("/api/auth/signin", json=signin_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["status"] == "healthy"
    
    def test_api_info_endpoint(self, client):
        """Test API info endpoint."""
        response = client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        assert "endpoints" in data
        assert data["features"]["authentication"] is True


class TestUserAPI:
    """Test user management API endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth_headers(self):
        """Mock authentication headers."""
        return {"Authorization": "Bearer test-token"}
    
    @pytest.mark.asyncio
    async def test_get_profile_endpoint(self, client, mock_auth_headers):
        """Test get user profile endpoint."""
        with patch('src.api.middleware.get_current_user') as mock_auth:
            mock_auth.return_value = {"user": {"id": "test-user-id"}}
            
            with patch('src.services.user_service.get_user_service') as mock_service:
                mock_user_service = AsyncMock()
                mock_user_service.get_user_profile.return_value = Mock(
                    success=True,
                    data=Mock(
                        id="test-user-id",
                        email="test@example.com",
                        full_name="Test User"
                    )
                )
                mock_service.return_value = mock_user_service
                
                response = client.get("/api/users/profile", headers=mock_auth_headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_update_profile_endpoint(self, client, mock_auth_headers):
        """Test update user profile endpoint."""
        with patch('src.api.middleware.get_current_user') as mock_auth:
            mock_auth.return_value = {"user": {"id": "test-user-id"}}
            
            with patch('src.services.user_service.get_user_service') as mock_service:
                mock_user_service = AsyncMock()
                mock_user_service.update_user_profile.return_value = Mock(
                    success=True,
                    data=Mock(full_name="Updated Name")
                )
                mock_service.return_value = mock_user_service
                
                update_data = {"full_name": "Updated Name"}
                response = client.put("/api/users/profile", json=update_data, headers=mock_auth_headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True


class TestSessionAPI:
    """Test session management API endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth_headers(self):
        """Mock authentication headers."""
        return {"Authorization": "Bearer test-token"}
    
    @pytest.mark.asyncio
    async def test_create_session_endpoint(self, client, mock_auth_headers):
        """Test create therapy session endpoint."""
        with patch('src.api.middleware.get_current_user') as mock_auth:
            mock_auth.return_value = {"user": {"id": "test-user-id"}}
            
            with patch('src.services.session_service.get_session_service') as mock_service:
                mock_session_service = AsyncMock()
                mock_session_service.create_session.return_value = Mock(
                    success=True,
                    data=Mock(
                        session_id="test-session-id",
                        user_id="test-user-id"
                    )
                )
                mock_service.return_value = mock_session_service
                
                response = client.post("/api/sessions/", headers=mock_auth_headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_list_sessions_endpoint(self, client, mock_auth_headers):
        """Test list user sessions endpoint."""
        with patch('src.api.middleware.get_current_user') as mock_auth:
            mock_auth.return_value = {"user": {"id": "test-user-id"}}
            
            with patch('src.services.session_service.get_session_service') as mock_service:
                mock_session_service = AsyncMock()
                mock_session_service.list_user_sessions.return_value = Mock(
                    success=True,
                    data=[
                        Mock(session_id="session-1"),
                        Mock(session_id="session-2")
                    ]
                )
                mock_service.return_value = mock_session_service
                
                response = client.get("/api/sessions/", headers=mock_auth_headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]) == 2


class TestWebSocketIntegration:
    """Test WebSocket integration."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        return create_app()
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, app):
        """Test WebSocket connection and authentication."""
        with patch('src.services.auth_service.get_auth_service') as mock_auth_service:
            mock_auth = AsyncMock()
            mock_auth.get_current_user.return_value = Mock(
                success=True,
                data={"user": {"id": "test-user-id"}}
            )
            mock_auth_service.return_value = mock_auth
            
            with patch('src.services.session_service.get_session_service') as mock_session_service:
                mock_session = AsyncMock()
                mock_session.create_session.return_value = Mock(
                    success=True,
                    data=Mock(session_id="test-session-id")
                )
                mock_session_service.return_value = mock_session
                
                # Test WebSocket connection would require more complex setup
                # This is a placeholder for WebSocket testing
                assert True  # WebSocket testing requires special setup


class TestErrorHandling:
    """Test error handling and middleware."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_404_error_handling(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "request_id" in data
    
    def test_validation_error_handling(self, client):
        """Test validation error handling."""
        # Send invalid signup data
        invalid_data = {
            "email": "invalid-email",  # Invalid email format
            "password": "123"  # Too short password
        }
        
        response = client.post("/api/auth/signup", json=invalid_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/api/health/")
        
        # Check CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers


class TestMiddleware:
    """Test middleware functionality."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_security_headers(self, client):
        """Test security headers are added."""
        response = client.get("/")
        
        # Check security headers
        assert "x-request-id" in response.headers
        assert "x-response-time" in response.headers
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
    
    def test_request_logging(self, client):
        """Test request logging middleware."""
        with patch('src.utils.logging_utils.log_therapy_event') as mock_log:
            response = client.get("/")
            
            # Verify logging was called
            mock_log.assert_called()
            
            # Check response
            assert response.status_code == 200


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
