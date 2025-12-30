"""
Tests for centralized authorization module.
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from unittest.mock import Mock, MagicMock
from fastapi import HTTPException

from app.authorization import (
    verify_client_access,
    verify_membership,
    get_user_clients,
    check_client_access
)
from app.models import Client, Membership, User


class TestVerifyClientAccess:
    """Tests for verify_client_access function."""
    
    def test_verify_client_access_with_active_membership(self):
        """User with active membership should have access."""
        # Setup mocks
        client_id = uuid4()
        user_id = uuid4()
        
        mock_client = Mock(spec=Client)
        mock_client.id = client_id
        mock_client.name = "Test Client"
        
        mock_membership = Mock(spec=Membership)
        mock_membership.user_id = user_id
        mock_membership.client_id = client_id
        mock_membership.status = 'active'
        
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.is_founder = False
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_client,  # First call returns client
            mock_membership  # Second call returns membership
        ]
        
        # Execute
        result = verify_client_access(client_id, mock_user, mock_db)
        
        # Assert
        assert result == mock_client
    
    def test_verify_client_access_founder_created_client(self):
        """Founder who created the client should have access."""
        client_id = uuid4()
        founder_id = uuid4()
        
        mock_client = Mock(spec=Client)
        mock_client.id = client_id
        mock_client.name = "Test Client"
        mock_client.founder_user_id = founder_id
        
        mock_user = Mock(spec=User)
        mock_user.id = founder_id
        mock_user.is_founder = True
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_client,  # First call returns client
            None  # Second call returns no membership
        ]
        
        # Execute
        result = verify_client_access(client_id, mock_user, mock_db)
        
        # Assert
        assert result == mock_client
    
    def test_verify_client_access_client_not_found(self):
        """Should raise 404 when client doesn't exist."""
        client_id = uuid4()
        user_id = uuid4()
        
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Execute and assert
        with pytest.raises(HTTPException) as exc_info:
            verify_client_access(client_id, mock_user, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()
    
    def test_verify_client_access_no_access(self):
        """Should raise 403 when user has no access."""
        client_id = uuid4()
        user_id = uuid4()
        other_founder_id = uuid4()
        
        mock_client = Mock(spec=Client)
        mock_client.id = client_id
        mock_client.founder_user_id = other_founder_id  # Different founder
        
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.is_founder = False
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_client,  # First call returns client
            None  # Second call returns no membership
        ]
        
        # Execute and assert
        with pytest.raises(HTTPException) as exc_info:
            verify_client_access(client_id, mock_user, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "do not have access" in exc_info.value.detail.lower()


class TestVerifyMembership:
    """Tests for verify_membership function."""
    
    def test_verify_membership_with_active_membership(self):
        """Should return membership when active."""
        user_id = uuid4()
        client_id = uuid4()
        
        mock_membership = Mock(spec=Membership)
        mock_membership.user_id = user_id
        mock_membership.client_id = client_id
        mock_membership.status = 'active'
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_membership
        
        # Execute
        result = verify_membership(user_id, client_id, mock_db)
        
        # Assert
        assert result == mock_membership
    
    def test_verify_membership_no_membership(self):
        """Should raise 403 when no membership exists."""
        user_id = uuid4()
        client_id = uuid4()
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Execute and assert
        with pytest.raises(HTTPException) as exc_info:
            verify_membership(user_id, client_id, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "no active membership" in exc_info.value.detail.lower()


class TestGetUserClients:
    """Tests for get_user_clients function."""
    
    def test_get_user_clients_via_memberships(self):
        """Should return clients from active memberships."""
        user_id = uuid4()
        
        mock_client1 = Mock(spec=Client)
        mock_client1.id = uuid4()
        mock_client1.name = "Client 1"
        
        mock_client2 = Mock(spec=Client)
        mock_client2.id = uuid4()
        mock_client2.name = "Client 2"
        
        mock_membership1 = Mock(spec=Membership)
        mock_membership1.client = mock_client1
        
        mock_membership2 = Mock(spec=Membership)
        mock_membership2.client = mock_client2
        
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.is_founder = False
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.options.return_value.all.return_value = [
            mock_membership1,
            mock_membership2
        ]
        
        # Execute
        result = get_user_clients(mock_user, mock_db)
        
        # Assert
        assert len(result) == 2
        assert mock_client1 in result
        assert mock_client2 in result
    
    def test_get_user_clients_founder_includes_founded(self):
        """Founder should get clients from memberships AND founded clients."""
        founder_id = uuid4()
        
        mock_client1 = Mock(spec=Client)
        mock_client1.id = uuid4()
        mock_client1.name = "Client 1"
        
        mock_client2 = Mock(spec=Client)
        mock_client2.id = uuid4()
        mock_client2.name = "Client 2"
        
        mock_membership = Mock(spec=Membership)
        mock_membership.client = mock_client1
        
        mock_user = Mock(spec=User)
        mock_user.id = founder_id
        mock_user.is_founder = True
        
        mock_db = MagicMock()
        # First query returns membership
        # Second query returns founded client
        mock_db.query.return_value.filter.return_value.options.return_value.all.return_value = [
            mock_membership
        ]
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_client2
        ]
        
        # Execute
        result = get_user_clients(mock_user, mock_db)
        
        # Assert
        assert len(result) == 2
        assert mock_client1 in result
        assert mock_client2 in result
    
    def test_get_user_clients_no_access(self):
        """Should return empty list when user has no clients."""
        user_id = uuid4()
        
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.is_founder = False
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.options.return_value.all.return_value = []
        
        # Execute
        result = get_user_clients(mock_user, mock_db)
        
        # Assert
        assert len(result) == 0


class TestCheckClientAccess:
    """Tests for check_client_access function."""
    
    def test_check_client_access_with_membership_returns_true(self):
        """Should return True when user has active membership."""
        user_id = uuid4()
        client_id = uuid4()
        
        mock_membership = Mock(spec=Membership)
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_membership,  # Membership query returns result
        ]
        
        # Execute
        result = check_client_access(client_id, user_id, mock_db)
        
        # Assert
        assert result is True
    
    def test_check_client_access_founder_returns_true(self):
        """Should return True when user is founder of client."""
        founder_id = uuid4()
        client_id = uuid4()
        
        mock_client = Mock(spec=Client)
        mock_client.id = client_id
        mock_client.founder_user_id = founder_id
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # No membership
            mock_client  # Is founder of client
        ]
        
        # Execute
        result = check_client_access(client_id, founder_id, mock_db)
        
        # Assert
        assert result is True
    
    def test_check_client_access_no_access_returns_false(self):
        """Should return False when user has no access."""
        user_id = uuid4()
        client_id = uuid4()
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # No membership
            None  # Not founder
        ]
        
        # Execute
        result = check_client_access(client_id, user_id, mock_db)
        
        # Assert
        assert result is False

