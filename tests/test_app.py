import pytest
from fastapi.testclient import TestClient
from src.app import app, activities

# Store original activities data for resetting between tests
ORIGINAL_ACTIVITIES = {}
for key, value in activities.items():
    ORIGINAL_ACTIVITIES[key] = value.copy()
    ORIGINAL_ACTIVITIES[key]["participants"] = value["participants"].copy()


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset the activities data before each test to ensure isolation"""
    activities.clear()
    for key, value in ORIGINAL_ACTIVITIES.items():
        activities[key] = value.copy()
        activities[key]["participants"] = value["participants"].copy()


def test_root_redirect(client):
    """Test that root endpoint redirects to static index"""
    response = client.get("/")
    assert response.status_code == 307


def test_get_activities(client):
    """Test retrieving all activities"""
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    
    # Check that we have activities
    assert len(data) > 0
    assert "Chess Club" in data
    
    # Check structure of an activity
    chess_club = data["Chess Club"]
    assert "description" in chess_club
    assert "schedule" in chess_club
    assert "max_participants" in chess_club
    assert "participants" in chess_club
    assert isinstance(chess_club["participants"], list)


def test_signup_success(client):
    """Test successful signup for an activity"""
    email = "test_signup@mergington.edu"
    activity = "Chess Club"
    
    response = client.post(f"/activities/{activity}/signup?email={email}")
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert email in data["message"]
    assert activity in data["message"]
    
    # Verify the participant was added
    response = client.get("/activities")
    activities_data = response.json()
    assert email in activities_data[activity]["participants"]


def test_signup_duplicate(client):
    """Test signing up for the same activity twice"""
    email = "duplicate@mergington.edu"
    activity = "Chess Club"
    
    # First signup should succeed
    response1 = client.post(f"/activities/{activity}/signup?email={email}")
    assert response1.status_code == 200
    
    # Second signup should fail
    response2 = client.post(f"/activities/{activity}/signup?email={email}")
    assert response2.status_code == 400
    
    error_data = response2.json()
    assert "detail" in error_data
    assert "already signed up" in error_data["detail"]


def test_signup_invalid_activity(client):
    """Test signing up for a non-existent activity"""
    response = client.post("/activities/NonExistent/signup?email=test@mergington.edu")
    assert response.status_code == 404
    
    error_data = response.json()
    assert "detail" in error_data
    assert "Activity not found" in error_data["detail"]


def test_signup_activity_full(client):
    """Test signing up when activity is at capacity"""
    activity = "Chess Club"
    max_participants = ORIGINAL_ACTIVITIES[activity]["max_participants"]
    current_participants = len(ORIGINAL_ACTIVITIES[activity]["participants"])
    
    # Fill the activity to capacity
    for i in range(max_participants - current_participants):
        email = f"fill_{i}@mergington.edu"
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
    
    # Try to add one more - should fail
    response = client.post(f"/activities/{activity}/signup?email=overflow@mergington.edu")
    assert response.status_code == 400
    
    error_data = response.json()
    assert "detail" in error_data
    assert "full" in error_data["detail"]


def test_delete_participant_success(client):
    """Test successfully removing a participant from an activity"""
    email = "to_delete@mergington.edu"
    activity = "Programming Class"
    
    # First sign up
    signup_response = client.post(f"/activities/{activity}/signup?email={email}")
    assert signup_response.status_code == 200
    
    # Then delete
    delete_response = client.delete(f"/activities/{activity}/participants/{email}")
    assert delete_response.status_code == 200
    
    data = delete_response.json()
    assert "message" in data
    assert "Removed" in data["message"]
    assert email in data["message"]
    
    # Verify the participant was removed
    get_response = client.get("/activities")
    activities_data = get_response.json()
    assert email not in activities_data[activity]["participants"]


def test_delete_participant_not_signed_up(client):
    """Test deleting a participant who is not signed up"""
    email = "not_signed_up@mergington.edu"
    activity = "Chess Club"
    
    response = client.delete(f"/activities/{activity}/participants/{email}")
    assert response.status_code == 400
    
    error_data = response.json()
    assert "detail" in error_data
    assert "not signed up" in error_data["detail"]


def test_delete_invalid_activity(client):
    """Test deleting from a non-existent activity"""
    response = client.delete("/activities/Invalid/participants/test@mergington.edu")
    assert response.status_code == 404
    
    error_data = response.json()
    assert "detail" in error_data
    assert "Activity not found" in error_data["detail"]