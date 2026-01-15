import pytest
from httpx import AsyncClient
from fastapi import status
from faker import Faker


class TestUserCreation:
    @pytest.mark.asyncio
    async def test_create_user_without_auth_should_fail(
        self, test_client: AsyncClient, fake: Faker
    ):
        user_data = {
            "name": fake.name(),
            "email": fake.email(),
            "password": fake.password(
                length=12, special_chars=True, digits=True, upper_case=True
            ),
        }

        response = await test_client.post("/users", data=user_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_user_missing_name(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        response = await test_client.post(
            "/users",
            data={
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_create_user_empty_name(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        response = await test_client.post(
            "/users",
            data={
                "name": "",
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_create_user_name_too_long(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        response = await test_client.post(
            "/users",
            data={
                "name": fake.pystr(min_chars=101, max_chars=101),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_create_user_missing_email(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        response = await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "password": fake.password(length=12, special_chars=True),
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_create_user_invalid_email_format(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        invalid_emails = [
            fake.word(),
            f"{fake.word()}@domain",
            f"@{fake.domain_name()}",
            f"{fake.word()} {fake.word()}@{fake.domain_name()}",
        ]

        for invalid_email in invalid_emails:
            response = await test_client.post(
                "/users",
                data={
                    "name": fake.name(),
                    "email": invalid_email,
                    "password": fake.password(length=12, special_chars=True),
                },
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_create_user_email_too_long(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        response = await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.pystr(min_chars=250, max_chars=250)
                + f"@{fake.domain_name()}",
                "password": fake.password(length=12, special_chars=True),
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        dup_email = fake.email()
        user_name1 = fake.name()
        user_name2 = fake.name()
        password = fake.password(length=12, special_chars=True)

        response1 = await test_client.post(
            "/users",
            data={
                "name": user_name1,
                "email": dup_email,
                "password": password,
            },
        )
        assert response1.status_code == status.HTTP_201_CREATED

        response2 = await test_client.post(
            "/users",
            data={
                "name": user_name2,
                "email": dup_email,
                "password": password,
            },
        )
        assert response2.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_create_user_weak_password(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        weak_passwords = [
            fake.numerify(text="######"),
            fake.word().lower(),
            fake.pystr(min_chars=3, max_chars=3),
            fake.numerify(text="########"),
        ]

        for weak_pass in weak_passwords:
            response = await test_client.post(
                "/users",
                data={
                    "name": fake.name(),
                    "email": fake.email(),
                    "password": weak_pass,
                },
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_create_user_without_password_is_valid(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        response = await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_create_user_invalid_phone_format(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        response = await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
                "phone": fake.word(),
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_create_user_invalid_avatar_file_type(
        self, test_client: AsyncClient, override_auth, fake: Faker, create_test_image
    ):
        from io import BytesIO

        files = {
            "avatar": (
                f"{fake.word()}.pdf",
                BytesIO(fake.binary(length=100)),
                "application/pdf",
            )
        }
        response = await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
            },
            files=files,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_create_user_avatar_file_too_large(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        from io import BytesIO

        large_file = BytesIO(b"0" * (11 * 1024 * 1024))
        files = {"avatar": (f"{fake.word()}.jpg", large_file, "image/jpeg")}
        response = await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
            },
            files=files,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_create_user_with_required_fields_only(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        name = fake.name()
        email = fake.email()

        response = await test_client.post(
            "/users",
            data={
                "name": name,
                "email": email,
                "password": fake.password(length=12, special_chars=True),
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == name
        assert data["data"]["email"] == email.lower()
        assert "password" not in data["data"]

    @pytest.mark.asyncio
    async def test_create_user_with_password(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        response = await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "password" not in data["data"]

    @pytest.mark.asyncio
    async def test_create_user_without_password_sends_reset_email(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        response = await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_create_user_with_avatar(
        self, test_client: AsyncClient, override_auth, fake: Faker, create_test_image
    ):
        files = {"avatar": create_test_image(f"{fake.word()}.jpg")}
        response = await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
            },
            files=files,
        )

        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()
        assert result["data"]["avatar_path"] is not None

    @pytest.mark.asyncio
    async def test_create_user_with_all_fields(
        self, test_client: AsyncClient, override_auth, fake: Faker, create_test_image
    ):
        files = {"avatar": create_test_image(f"{fake.word()}.jpg")}
        response = await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
                "phone": "+81" + fake.numerify(text="#########"),
                "line_user_id": f"U{fake.bothify(text='????-????-????-????')}",
                "is_admin": "false",
                "is_active": "true",
            },
            files=files,
        )

        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()
        assert result["data"]["name"]
        assert result["data"]["email"]

    @pytest.mark.asyncio
    async def test_create_user_email_case_insensitive(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        base_email = fake.email()
        mixed_email = base_email.upper()

        response = await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": mixed_email,
                "password": fake.password(length=12, special_chars=True),
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()
        assert result["data"]["email"] == base_email.lower()

    @pytest.mark.asyncio
    async def test_create_user_response_structure(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        email = fake.email()
        name = fake.name()

        response = await test_client.post(
            "/users",
            data={
                "name": name,
                "email": email,
                "password": fake.password(length=12, special_chars=True),
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "success" in data
        assert data["success"] is True
        assert "data" in data
        assert "message" in data

        user_data = data["data"]
        assert "id" in user_data
        assert "name" in user_data
        assert "email" in user_data
        assert "is_active" in user_data
        assert "is_admin" in user_data
        assert "created_at" in user_data
        assert "updated_at" in user_data
        assert "password" not in user_data
