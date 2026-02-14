"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add src directory to path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to a clean state before each test"""
    from app import activities
    
    # Save original state
    original_activities = {
        name: {
            "description": act["description"],
            "schedule": act["schedule"],
            "max_participants": act["max_participants"],
            "participants": act["participants"].copy()
        }
        for name, act in activities.items()
    }
    
    yield
    
    # Restore original state
    for name, act in activities.items():
        act["participants"] = original_activities[name]["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Basketball" in data
        assert "Soccer" in data
    
    def test_activity_has_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity
            assert isinstance(activity["participants"], list)


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_activity_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball/signup",
            params={"email": "newemail@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newemail@mergington.edu" in data["message"]
        assert "Basketball" in data["message"]
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newemail@mergington.edu" in activities_data["Basketball"]["participants"]
    
    def test_signup_duplicate_email_fails(self, client, reset_activities):
        """Test that signing up with duplicate email fails"""
        # First signup succeeds
        response1 = client.post(
            "/activities/Basketball/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        assert response1.status_code == 200
        
        # Second signup with same email fails
        response2 = client.post(
            "/activities/Basketball/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for non-existent activity fails"""
        response = client.post(
            "/activities/NonExistentActivity/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_signup_multiple_activities(self, client, reset_activities):
        """Test that a student can sign up for multiple activities"""
        email = "multisport@mergington.edu"
        
        # Sign up for Basketball
        response1 = client.post(
            "/activities/Basketball/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for Soccer
        response2 = client.post(
            "/activities/Soccer/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify both signups worked
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Basketball"]["participants"]
        assert email in activities_data["Soccer"]["participants"]


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        # First sign up
        client.post(
            "/activities/Basketball/signup",
            params={"email": "removeme@mergington.edu"}
        )
        
        # Then unregister
        response = client.delete(
            "/activities/Basketball/unregister",
            params={"email": "removeme@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert "removeme@mergington.edu" in data["message"]
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "removeme@mergington.edu" not in activities_data["Basketball"]["participants"]
    
    def test_unregister_not_signed_up_fails(self, client):
        """Test that unregistering someone not signed up fails"""
        response = client.delete(
            "/activities/Basketball/unregister",
            params={"email": "notsignedup@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]
    
    def test_unregister_nonexistent_activity_fails(self, client):
        """Test that unregistering from non-existent activity fails"""
        response = client.delete(
            "/activities/NonExistentActivity/unregister",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregistering an existing participant"""
        # Get the current Basketball participants
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        original_participants = activities_data["Basketball"]["participants"].copy()
        
        if original_participants:
            email_to_remove = original_participants[0]
            
            # Unregister the participant
            response = client.delete(
                "/activities/Basketball/unregister",
                params={"email": email_to_remove}
            )
            assert response.status_code == 200
            
            # Verify removal
            activities_response = client.get("/activities")
            activities_data = activities_response.json()
            assert email_to_remove not in activities_data["Basketball"]["participants"]


class TestRootRedirect:
    """Tests for GET / endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that the root path redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]
