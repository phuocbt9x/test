import pytest
from pydantic import ValidationError

from src.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    UpdateCurrentUserRequest,
)


@pytest.mark.units
class TestRegisterRequest:
    def test_valid_request(self):
        request = RegisterRequest(
            name="Test User",
            email="test@example.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!",
        )

        assert request.name == "Test User"
        assert request.email == "test@example.com"

    def test_email_validation_fails_on_invalid_format(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                name="Test",
                email="invalid-email",
                password="SecurePass123!",
                confirm_password="SecurePass123!",
            )

        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("email",) and "email" in str(e["msg"]).lower() for e in errors
        )

    def test_password_validation_fails_on_short_password(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                name="Test",
                email="test@test.com",
                password="123",
                confirm_password="SecurePass123!",
            )

        errors = exc_info.value.errors()
        password_errors = [e for e in errors if e["loc"] == ("password",)]
        assert len(password_errors) > 0

    def test_confirm_password_validation_fails_on_mismatch(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                name="Test",
                email="test@test.com",
                password="SecurePass123!",
                confirm_password="DifferentPass123!",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confirm_password",) for e in errors)

    def test_name_validation_fails_on_empty(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                name="",
                email="test@test.com",
                password="SecurePass123!",
                confirm_password="SecurePass123!",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)


@pytest.mark.units
class TestLoginRequest:
    def test_valid_request(self):
        request = LoginRequest(email="test@example.com", password="SecurePass123!")

        assert request.email == "test@example.com"
        assert request.password == "SecurePass123!"

    def test_email_validation_fails_on_invalid_format(self):
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(email="invalid-email", password="SecurePass123!")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("email",) for e in errors)

    def test_password_validation_fails_on_short_password(self):
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(email="test@test.com", password="123")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("password",) for e in errors)


@pytest.mark.units
class TestUpdateCurrentUserRequest:
    def test_valid_partial_update(self):
        request = UpdateCurrentUserRequest(name="Updated Name")

        assert request.name == "Updated Name"
        assert request.email is None

    def test_email_validation_fails_on_invalid_format(self):
        with pytest.raises(ValidationError) as exc_info:
            UpdateCurrentUserRequest(email="invalid-email")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("email",) for e in errors)

    def test_password_validation_fails_on_short_password(self):
        with pytest.raises(ValidationError) as exc_info:
            UpdateCurrentUserRequest(password="123")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("password",) for e in errors)

    def test_phone_validation_with_valid_phone(self):
        request = UpdateCurrentUserRequest(phone="0312345678")
        assert request.phone == "+81312345678"

    def test_phone_validation_with_none(self):
        request = UpdateCurrentUserRequest(name="Test")
        assert request.phone is None

    def test_phone_validation_with_empty_string(self):
        request = UpdateCurrentUserRequest(phone="")
        assert request.phone is None

    def test_line_user_id_validation_with_valid_id(self):
        request = RegisterRequest(
            name="Test",
            email="test@test.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!",
            line_user_id="line123",
        )
        assert request.line_user_id == "line123"

    def test_line_user_id_validation_with_none(self):
        request = RegisterRequest(
            name="Test",
            email="test@test.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!",
        )
        assert request.line_user_id is None

    def test_register_with_optional_fields(self):
        request = RegisterRequest(
            name="Test User",
            email="test@example.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!",
            phone="0312345678",
            line_user_id="line123",
            is_active=False,
            is_admin=True,
        )
        assert request.phone == "+81312345678"
        assert request.line_user_id == "line123"
        assert request.is_active is False
        assert request.is_admin is True

    def test_phone_validation_with_whitespace(self):
        request = RegisterRequest(
            name="Test",
            email="test@test.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!",
            phone="  0312345678  ",
        )
        assert request.phone == "+81312345678"

    def test_phone_validation_with_invalid_format(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                name="Test",
                email="test@test.com",
                password="SecurePass123!",
                confirm_password="SecurePass123!",
                phone="invalid-phone",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("phone",) for e in errors)

    def test_line_user_id_validation_with_long_string(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                name="Test",
                email="test@test.com",
                password="SecurePass123!",
                confirm_password="SecurePass123!",
                line_user_id="a" * 101,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("line_user_id",) for e in errors)

    def test_update_current_user_name_validation(self):
        request = UpdateCurrentUserRequest(name="Updated Name")
        assert request.name == "Updated Name"

    def test_update_current_user_name_with_none(self):
        request = UpdateCurrentUserRequest()
        assert request.name is None

    def test_update_current_user_email_with_none(self):
        request = UpdateCurrentUserRequest(name="Test")
        assert request.email is None

    def test_update_current_user_password_with_none(self):
        request = UpdateCurrentUserRequest(name="Test")
        assert request.password is None

    def test_update_current_user_confirm_password_with_none(self):
        request = UpdateCurrentUserRequest(name="Test")
        assert request.confirm_password is None

    def test_update_current_user_phone_with_none(self):
        request = UpdateCurrentUserRequest(name="Test")
        assert request.phone is None

    def test_update_current_user_line_user_id_with_none(self):
        request = UpdateCurrentUserRequest(name="Test")
        assert request.line_user_id is None

    def test_register_phone_with_none(self):
        request = RegisterRequest(
            name="Test",
            email="test@test.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!",
            phone=None,
        )
        assert request.phone is None

    def test_register_phone_with_empty_string(self):
        request = RegisterRequest(
            name="Test",
            email="test@test.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!",
            phone="",
        )
        assert request.phone is None

    def test_register_phone_with_whitespace_only(self):
        request = RegisterRequest(
            name="Test",
            email="test@test.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!",
            phone="   ",
        )
        assert request.phone is None

    def test_register_line_user_id_with_none(self):
        request = RegisterRequest(
            name="Test",
            email="test@test.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!",
            line_user_id=None,
        )
        assert request.line_user_id is None

    def test_update_current_user_confirm_password_with_password_none(self):
        request = UpdateCurrentUserRequest(
            password=None,
            confirm_password="SomePassword123!",
        )
        assert request.password is None
        assert request.confirm_password == "SomePassword123!"

    def test_update_current_user_phone_with_empty_string(self):
        request = UpdateCurrentUserRequest(phone="")
        assert request.phone is None

    def test_update_current_user_phone_with_whitespace_only(self):
        request = UpdateCurrentUserRequest(phone="   ")
        assert request.phone is None

    def test_update_current_user_line_user_id_with_valid_id(self):
        request = UpdateCurrentUserRequest(line_user_id="line456")
        assert request.line_user_id == "line456"

    def test_update_current_user_name_with_none_explicit(self):
        request = UpdateCurrentUserRequest(name=None)
        assert request.name is None

    def test_update_current_user_email_with_none_explicit(self):
        request = UpdateCurrentUserRequest(email=None)
        assert request.email is None

    def test_update_current_user_password_with_none_explicit(self):
        request = UpdateCurrentUserRequest(password=None)
        assert request.password is None

    def test_update_current_user_confirm_password_with_none_explicit(self):
        request = UpdateCurrentUserRequest(confirm_password=None)
        assert request.confirm_password is None

    def test_update_current_user_phone_with_none_explicit(self):
        request = UpdateCurrentUserRequest(phone=None)
        assert request.phone is None

    def test_update_current_user_line_user_id_with_none_explicit(self):
        request = UpdateCurrentUserRequest(line_user_id=None)
        assert request.line_user_id is None

    def test_update_current_user_confirm_password_when_password_is_none(self):
        request = UpdateCurrentUserRequest(
            password=None,
            confirm_password="SomePassword123!",
        )
        assert request.password is None
        assert request.confirm_password == "SomePassword123!"

    def test_update_current_user_confirm_password_with_password_none_returns_value(
        self,
    ):
        request = UpdateCurrentUserRequest(
            password=None,
            confirm_password="TestPassword123!",
        )
        assert request.confirm_password == "TestPassword123!"

    def test_update_current_user_confirm_password_with_password_provided(self):
        request = UpdateCurrentUserRequest(
            password="NewPassword123!",
            confirm_password="NewPassword123!",
        )
        assert request.password == "NewPassword123!"
        assert request.confirm_password == "NewPassword123!"

    def test_update_current_user_confirm_password_mismatch(self):
        with pytest.raises(ValidationError) as exc_info:
            UpdateCurrentUserRequest(
                password="NewPassword123!",
                confirm_password="DifferentPassword123!",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confirm_password",) for e in errors)
