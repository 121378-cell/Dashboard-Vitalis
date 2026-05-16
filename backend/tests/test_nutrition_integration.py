"""
Tests de integracion para endpoints de Nutrition (/api/v1/nutrition/...)
Cubre los 10 endpoints: daily, today, meal-plan, log, delete, history, settings, update settings, water, hydration-status

NOTA: Todos los endpoints son async def sin try/except, por lo que las excepciones
del servicio se propagan como excepciones sin procesar (no como 500).
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.api.deps import get_db, get_current_user_id
from app.services.nutrition_service import NutritionPlan

# --- Test App Setup ---
test_app = FastAPI()
from app.api.api_v1.endpoints.nutrition import router
test_app.include_router(router, prefix="/nutrition", tags=["nutrition"])


@pytest.fixture(autouse=True)
def test_engine():
    """Creates a fresh in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Provides a SQLAlchemy session bound to the test engine."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """FastAPI TestClient with overridden dependencies."""

    def _get_test_db():
        yield db_session

    test_app.dependency_overrides[get_db] = _get_test_db
    test_app.dependency_overrides[get_current_user_id] = lambda: "test_user"
    return TestClient(test_app)


@pytest.fixture
def headers():
    return {"x-user-id": "test_user"}


@pytest.fixture
def _no_auth():
    """Remove auth dependency override for 401 tests."""
    test_app.dependency_overrides.pop(get_current_user_id, None)
    yield


# =============================================================================
# TestDailyNeedsEndpoint - GET /nutrition/daily
# =============================================================================

class TestDailyNeedsEndpoint:
    API_PATH = "/nutrition/daily"

    def test_success(self, client, headers):
        """Should return daily caloric and macro needs."""
        real_plan = NutritionPlan(
            target_calories=2500, protein_g=150, carbs_g=300, fat_g=83,
            hydration_ml=3000, bmr=1800.0, neat_calories=500.0,
            eat_calories=200.0, tdee=2500.0, steps_source="estimate",
            steps=8000, workout_calories=200, goal_type="maintenance",
            meals=[],
        )

        with patch(
            "app.api.api_v1.endpoints.nutrition.NutritionService.calculate_daily_needs",
            return_value=real_plan,
        ):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["target_calories"] == 2500
        assert data["data"]["protein_g"] == 150

    def test_success_with_target_date(self, client, headers):
        """Should accept target_date query param (passed as positional arg)."""
        real_plan = NutritionPlan(
            target_calories=2200, protein_g=130, carbs_g=275, fat_g=73,
            hydration_ml=3000, bmr=1700.0, neat_calories=400.0,
            eat_calories=100.0, tdee=2200.0, steps_source="estimate",
            steps=8000, workout_calories=100, goal_type="cut", meals=[],
        )

        with patch(
            "app.api.api_v1.endpoints.nutrition.NutritionService.calculate_daily_needs",
            return_value=real_plan,
        ) as mock_calc:
            resp = client.get(self.API_PATH, params={"target_date": "2025-06-01"}, headers=headers)

        assert resp.status_code == 200
        # target_date se pasa como argumento posicional (3er arg), no keyword
        args = mock_calc.call_args[0]
        assert args[2] == "2025-06-01"

    def test_error(self, client, headers):
        """Should propagate service exception (async def sin try/except)."""
        with patch(
            "app.api.api_v1.endpoints.nutrition.NutritionService.calculate_daily_needs",
            side_effect=Exception("Calculation failed"),
        ):
            with pytest.raises(Exception):
                client.get(self.API_PATH, headers=headers)

    def test_unauthorized(self, client, _no_auth):
        """Should return 401 without x-user-id header."""
        resp = client.get(self.API_PATH, headers={})
        assert resp.status_code == 401


# =============================================================================
# TestNutritionTodayEndpoint - GET /nutrition/today
# =============================================================================

class TestNutritionTodayEndpoint:
    API_PATH = "/nutrition/today"

    def test_success(self, client, headers):
        """Should return full daily nutritional summary."""
        mock_summary = {
            "targets": {"calories": 2500, "protein": 150, "carbs": 300, "fat": 83},
            "consumed": {"calories": 1800, "protein": 120, "carbs": 200, "fat": 50},
            "remaining": {"calories": 700, "protein": 30, "carbs": 100, "fat": 33},
            "water": {"glasses": 4, "ml": 1000, "target_ml": 3000},
        }

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.get_nutrition_today", return_value=mock_summary):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["targets"]["calories"] == 2500
        assert data["data"]["consumed"]["protein"] == 120

    def test_empty_day(self, client, headers):
        """Should return empty consumed values when nothing logged."""
        mock_summary = {
            "targets": {"calories": 2500, "protein": 150, "carbs": 300, "fat": 83},
            "consumed": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
            "remaining": {"calories": 2500, "protein": 150, "carbs": 300, "fat": 83},
            "water": {"glasses": 0, "ml": 0, "target_ml": 3000},
        }

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.get_nutrition_today", return_value=mock_summary):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["consumed"]["calories"] == 0

    def test_error(self, client, headers):
        """Should propagate service exception."""
        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.get_nutrition_today", side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                client.get(self.API_PATH, headers=headers)

    def test_unauthorized(self, client, _no_auth):
        """Should return 401 without x-user-id header."""
        resp = client.get(self.API_PATH, headers={})
        assert resp.status_code == 401


# =============================================================================
# TestMealPlanEndpoint - GET /nutrition/meal-plan
# =============================================================================

class TestMealPlanEndpoint:
    API_PATH = "/nutrition/meal-plan"

    def test_success(self, client, headers):
        """Should return daily meal plan."""
        mock_meals = [
            {"time": "08:00", "meal": "Desayuno", "calories": 600, "protein": 35, "carbs": 70, "fat": 15},
            {"time": "12:00", "meal": "Almuerzo", "calories": 800, "protein": 50, "carbs": 80, "fat": 25},
        ]
        real_plan = NutritionPlan(
            target_calories=2500, protein_g=150, carbs_g=300, fat_g=83,
            hydration_ml=3000, bmr=1800.0, neat_calories=500.0,
            eat_calories=200.0, tdee=2500.0, steps_source="estimate",
            steps=8000, workout_calories=200, goal_type="maintenance",
            meals=mock_meals,
        )

        with patch(
            "app.api.api_v1.endpoints.nutrition.NutritionService.calculate_daily_needs",
            return_value=real_plan,
        ):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["data"]["meals"]) == 2
        assert data["data"]["meals"][0]["meal"] == "Desayuno"

    def test_success_with_target_date(self, client, headers):
        """Should accept target_date query param."""
        real_plan = NutritionPlan(
            target_calories=2500, protein_g=150, carbs_g=300, fat_g=83,
            hydration_ml=3000, bmr=1800.0, neat_calories=500.0,
            eat_calories=200.0, tdee=2500.0, steps_source="estimate",
            steps=8000, workout_calories=200, goal_type="maintenance",
            meals=[{"time": "12:00", "meal": "Almuerzo", "calories": 800, "protein": 50, "carbs": 80, "fat": 25}],
        )

        with patch(
            "app.api.api_v1.endpoints.nutrition.NutritionService.calculate_daily_needs",
            return_value=real_plan,
        ) as mock_calc:
            resp = client.get(self.API_PATH, params={"target_date": "2025-06-15"}, headers=headers)

        assert resp.status_code == 200
        args = mock_calc.call_args[0]
        assert args[2] == "2025-06-15"

    def test_empty(self, client, headers):
        """Should return empty meals list."""
        real_plan = NutritionPlan(
            target_calories=2500, protein_g=150, carbs_g=300, fat_g=83,
            hydration_ml=3000, bmr=1800.0, neat_calories=500.0,
            eat_calories=200.0, tdee=2500.0, steps_source="estimate",
            steps=8000, workout_calories=200, goal_type="maintenance",
            meals=[],
        )

        with patch(
            "app.api.api_v1.endpoints.nutrition.NutritionService.calculate_daily_needs",
            return_value=real_plan,
        ):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["meals"] == []

    def test_error(self, client, headers):
        """Should propagate service exception."""
        with patch(
            "app.api.api_v1.endpoints.nutrition.NutritionService.calculate_daily_needs",
            side_effect=Exception("Generation failed"),
        ):
            with pytest.raises(Exception):
                client.get(self.API_PATH, headers=headers)

    def test_unauthorized(self, client, _no_auth):
        """Should return 401 without x-user-id header."""
        resp = client.get(self.API_PATH, headers={})
        assert resp.status_code == 401


# =============================================================================
# TestLogMealEndpoint - POST /nutrition/log
# =============================================================================

class TestLogMealEndpoint:
    API_PATH = "/nutrition/log"

    def test_success(self, client, headers):
        """Should log a meal successfully."""
        # El endpoint accede a atributos del ORM: meal.id, meal.meal_type, etc.
        mock_meal = MagicMock()
        mock_meal.id = 1
        mock_meal.date = "2025-06-16"
        mock_meal.meal_type = "almuerzo"
        mock_meal.name = "Pollo con arroz"
        mock_meal.calories = 650
        mock_meal.protein_g = 45
        mock_meal.carbs_g = 60
        mock_meal.fat_g = 15
        mock_meal.fiber_g = 5
        mock_meal.sodium_mg = 200

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.log_meal", return_value=mock_meal):
            resp = client.post(self.API_PATH, json={
                "meal_type": "almuerzo",
                "name": "Pollo con arroz",
                "calories": 650,
                "protein_g": 45,
                "carbs_g": 60,
                "fat_g": 15,
            }, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["meal_type"] == "almuerzo"

    def test_minimal_payload(self, client, headers):
        """Should log meal with minimal required fields."""
        mock_meal = MagicMock()
        mock_meal.id = 2
        mock_meal.date = "2025-06-16"
        mock_meal.meal_type = "snack"
        mock_meal.name = "Barrita"
        mock_meal.calories = 200
        mock_meal.protein_g = 10
        mock_meal.carbs_g = 25
        mock_meal.fat_g = 5
        mock_meal.fiber_g = 0
        mock_meal.sodium_mg = 50

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.log_meal", return_value=mock_meal):
            resp = client.post(self.API_PATH, json={
                "meal_type": "snack",
                "name": "Barrita",
                "calories": 200,
                "protein_g": 10,
                "carbs_g": 25,
                "fat_g": 5,
            }, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_error(self, client, headers):
        """Should propagate service exception."""
        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.log_meal", side_effect=Exception("Log failed")):
            with pytest.raises(Exception):
                client.post(self.API_PATH, json={
                    "meal_type": "desayuno",
                    "name": "Test",
                    "calories": 300,
                    "protein_g": 15,
                    "carbs_g": 40,
                    "fat_g": 10,
                }, headers=headers)

    def test_unauthorized(self, client, _no_auth):
        """Should return 401 without x-user-id header."""
        resp = client.post(self.API_PATH, json={
            "meal_type": "desayuno",
            "name": "Test",
            "calories": 300,
            "protein_g": 15,
            "carbs_g": 40,
            "fat_g": 10,
        }, headers={})
        assert resp.status_code == 401


# =============================================================================
# TestDeleteMealEndpoint - DELETE /nutrition/log/{meal_id}
# =============================================================================

class TestDeleteMealEndpoint:
    API_PATH = "/nutrition/log"

    def test_success(self, client, headers):
        """Should delete a meal successfully."""
        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.delete_meal", return_value=True):
            resp = client.delete(f"{self.API_PATH}/1", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_not_found(self, client, headers):
        """Should return 404 when meal not found."""
        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.delete_meal", return_value=False):
            resp = client.delete(f"{self.API_PATH}/999", headers=headers)

        assert resp.status_code == 404

    def test_error(self, client, headers):
        """Should propagate service exception."""
        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.delete_meal", side_effect=Exception("Delete failed")):
            with pytest.raises(Exception):
                client.delete(f"{self.API_PATH}/1", headers=headers)

    def test_unauthorized(self, client, _no_auth):
        """Should return 401 without x-user-id header."""
        resp = client.delete(f"{self.API_PATH}/1", headers={})
        assert resp.status_code == 401


# =============================================================================
# TestNutritionHistoryEndpoint - GET /nutrition/history
# =============================================================================

class TestNutritionHistoryEndpoint:
    API_PATH = "/nutrition/history"

    def test_success_default_days(self, client, headers):
        """Should return history with default 7 days."""
        mock_history = [
            {"date": "2025-06-09", "target_calories": 2500, "consumed_calories": 2200},
            {"date": "2025-06-10", "target_calories": 2500, "consumed_calories": 2400},
        ]

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.get_nutrition_history", return_value=mock_history) as mock_hist:
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["data"]["history"]) == 2
        # days se pasa como posicional (3er arg), default 7
        args = mock_hist.call_args[0]
        assert args[2] == 7

    def test_success_custom_days(self, client, headers):
        """Should accept custom days param."""
        mock_history = [{"date": "2025-06-09", "target_calories": 2500, "consumed_calories": 2200}]

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.get_nutrition_history", return_value=mock_history) as mock_hist:
            resp = client.get(self.API_PATH, params={"days": 30}, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["data"]["history"]) == 1
        assert data["data"]["days_requested"] == 30
        args = mock_hist.call_args[0]
        assert args[2] == 30

    def test_empty(self, client, headers):
        """Should return empty list when no history."""
        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.get_nutrition_history", return_value=[]):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["history"] == []

    def test_error(self, client, headers):
        """Should propagate service exception."""
        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.get_nutrition_history", side_effect=Exception("History error")):
            with pytest.raises(Exception):
                client.get(self.API_PATH, headers=headers)

    def test_unauthorized(self, client, _no_auth):
        """Should return 401 without x-user-id header."""
        resp = client.get(self.API_PATH, headers={})
        assert resp.status_code == 401


# =============================================================================
# TestGetSettingsEndpoint - GET /nutrition/settings
# =============================================================================

class TestGetSettingsEndpoint:
    API_PATH = "/nutrition/settings"

    def test_success(self, client, headers):
        """Should return nutrition settings."""
        mock_settings = MagicMock()
        mock_settings.goal_type = "maintenance"
        mock_settings.weight_kg = 80.0
        mock_settings.height_cm = 180.0
        mock_settings.age = 30
        mock_settings.gender = "male"
        mock_settings.activity_multiplier = 1.55
        mock_settings.protein_per_kg = 2.0
        mock_settings.fat_per_kg = 1.0
        mock_settings.calorie_adjustment = 0

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.get_nutrition_settings", return_value=mock_settings):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["goal_type"] == "maintenance"
        assert data["data"]["weight_kg"] == 80.0

    def test_default_settings(self, client, headers):
        """Should return default settings for new user with different values."""
        mock_settings = MagicMock()
        mock_settings.goal_type = "maintenance"
        mock_settings.weight_kg = 75.0
        mock_settings.height_cm = 170.0
        mock_settings.age = 28
        mock_settings.gender = "female"
        mock_settings.activity_multiplier = 1.2
        mock_settings.protein_per_kg = 1.8
        mock_settings.fat_per_kg = 0.9
        mock_settings.calorie_adjustment = 0

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.get_nutrition_settings", return_value=mock_settings):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["weight_kg"] == 75.0
        assert data["data"]["gender"] == "female"

    def test_error(self, client, headers):
        """Should propagate service exception."""
        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.get_nutrition_settings", side_effect=Exception("Settings error")):
            with pytest.raises(Exception):
                client.get(self.API_PATH, headers=headers)

    def test_unauthorized(self, client, _no_auth):
        """Should return 401 without x-user-id header."""
        resp = client.get(self.API_PATH, headers={})
        assert resp.status_code == 401


# =============================================================================
# TestUpdateSettingsEndpoint - PUT /nutrition/settings
# =============================================================================

class TestUpdateSettingsEndpoint:
    API_PATH = "/nutrition/settings"

    def test_success(self, client, headers):
        """Should update nutrition settings successfully."""
        mock_settings = MagicMock()
        mock_settings.goal_type = "cut"
        mock_settings.weight_kg = 78.0
        mock_settings.height_cm = 180.0
        mock_settings.age = 30
        mock_settings.gender = "male"
        mock_settings.activity_multiplier = 1.55
        mock_settings.protein_per_kg = 2.2
        mock_settings.fat_per_kg = 0.8
        mock_settings.calorie_adjustment = -300

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.update_nutrition_settings", return_value=mock_settings):
            resp = client.put(self.API_PATH, json={
                "goal_type": "cut",
                "weight_kg": 78.0,
                "protein_per_kg": 2.2,
                "calorie_adjustment": -300,
            }, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["goal_type"] == "cut"
        assert data["data"]["calorie_adjustment"] == -300

    def test_partial_update(self, client, headers):
        """Should accept partial settings update."""
        mock_settings = MagicMock()
        mock_settings.goal_type = "maintenance"
        mock_settings.weight_kg = 80.0
        mock_settings.height_cm = 180.0
        mock_settings.age = 30
        mock_settings.gender = "male"
        mock_settings.activity_multiplier = 1.55
        mock_settings.protein_per_kg = 2.0
        mock_settings.fat_per_kg = 1.0
        mock_settings.calorie_adjustment = 0

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.update_nutrition_settings", return_value=mock_settings):
            resp = client.put(self.API_PATH, json={
                "weight_kg": 80.0,
            }, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_error(self, client, headers):
        """Should propagate service exception."""
        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.update_nutrition_settings", side_effect=Exception("Update failed")):
            with pytest.raises(Exception):
                client.put(self.API_PATH, json={
                    "goal_type": "cut",
                }, headers=headers)

    def test_unauthorized(self, client, _no_auth):
        """Should return 401 without x-user-id header."""
        resp = client.put(self.API_PATH, json={
            "goal_type": "cut",
        }, headers={})
        assert resp.status_code == 401


# =============================================================================
# TestWaterEndpoint - POST /nutrition/water
# =============================================================================

class TestWaterEndpoint:
    API_PATH = "/nutrition/water"

    def test_success(self, client, headers):
        """Should log water glass successfully."""
        mock_summary = MagicMock()
        mock_summary.hydration_ml = 500
        mock_summary.hydration_target_ml = 3000
        mock_summary.water_glasses = 2

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.log_water_glass", return_value=2):
            with patch("app.api.api_v1.endpoints.nutrition.NutritionService.save_daily_summary", return_value=mock_summary):
                resp = client.post(self.API_PATH, json={"glasses": 1}, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["glasses_logged"] == 2
        assert data["data"]["hydration_ml"] == 500

    def test_default_glasses(self, client, headers):
        """Should default to 1 glass when not specified."""
        mock_summary = MagicMock()
        mock_summary.hydration_ml = 250
        mock_summary.hydration_target_ml = 3000
        mock_summary.water_glasses = 1

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.log_water_glass", return_value=1):
            with patch("app.api.api_v1.endpoints.nutrition.NutritionService.save_daily_summary", return_value=mock_summary):
                resp = client.post(self.API_PATH, json={}, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["glasses_logged"] == 1

    def test_error(self, client, headers):
        """Should propagate service exception."""
        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.log_water_glass", side_effect=Exception("Water log failed")):
            with pytest.raises(Exception):
                client.post(self.API_PATH, json={"glasses": 1}, headers=headers)

    def test_unauthorized(self, client, _no_auth):
        """Should return 401 without x-user-id header."""
        resp = client.post(self.API_PATH, json={"glasses": 1}, headers={})
        assert resp.status_code == 401


# =============================================================================
# TestHydrationStatusEndpoint - GET /nutrition/hydration-status
# =============================================================================

class TestHydrationStatusEndpoint:
    API_PATH = "/nutrition/hydration-status"

    def test_success(self, client, headers):
        """Should return hydration status."""
        mock_summary = MagicMock()
        mock_summary.water_glasses = 4
        mock_summary.hydration_ml = 1000
        mock_summary.hydration_target_ml = 3000

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.save_daily_summary", return_value=mock_summary):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["water_glasses"] == 4
        assert data["data"]["hydration_ml"] == 1000
        assert data["data"]["target_ml"] == 3000
        assert data["data"]["progress_pct"] == pytest.approx(33.33, abs=0.5)
        assert data["data"]["glasses_remaining"] == 8

    def test_zero_hydration(self, client, headers):
        """Should return zero values when no water logged."""
        mock_summary = MagicMock()
        mock_summary.water_glasses = 0
        mock_summary.hydration_ml = 0
        mock_summary.hydration_target_ml = 3000

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.save_daily_summary", return_value=mock_summary):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["water_glasses"] == 0
        assert data["data"]["hydration_ml"] == 0
        assert data["data"]["progress_pct"] == 0
        assert data["data"]["glasses_remaining"] == 12

    def test_full_hydration(self, client, headers):
        """Should cap progress at 100% when target exceeded."""
        mock_summary = MagicMock()
        mock_summary.water_glasses = 16
        mock_summary.hydration_ml = 4000
        mock_summary.hydration_target_ml = 3000

        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.save_daily_summary", return_value=mock_summary):
            resp = client.get(self.API_PATH, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["progress_pct"] == 100

    def test_error(self, client, headers):
        """Should propagate service exception."""
        with patch("app.api.api_v1.endpoints.nutrition.NutritionService.save_daily_summary", side_effect=Exception("Hydration error")):
            with pytest.raises(Exception):
                client.get(self.API_PATH, headers=headers)

    def test_unauthorized(self, client, _no_auth):
        """Should return 401 without x-user-id header."""
        resp = client.get(self.API_PATH, headers={})
        assert resp.status_code == 401
