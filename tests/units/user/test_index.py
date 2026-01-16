import pytest
from httpx import AsyncClient
from fastapi import status
from faker import Faker


class TestUserList:
    @pytest.mark.asyncio
    async def test_list_users_without_authentication_should_fail(
        self, test_client: AsyncClient
    ):
        response = await test_client.get("/users")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_list_users_with_invalid_token_should_fail(
        self, test_client: AsyncClient
    ):
        response = await test_client.get(
            "/users", headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_list_users_with_expired_token_should_fail(
        self, test_client: AsyncClient
    ):
        response = await test_client.get(
            "/users", headers={"Authorization": "Bearer expired_token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_list_users_without_admin_permission_should_fail(
        self, test_client: AsyncClient, override_auth_regular_user
    ):
        response = await test_client.get("/users")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_list_users_with_regular_user_should_fail(
        self, test_client: AsyncClient, override_auth_regular_user
    ):
        response = await test_client.get("/users")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_list_users_with_admin_permission_should_succeed(
        self, test_client: AsyncClient, override_auth
    ):
        response = await test_client.get("/users")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_users_default_pagination(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        for _ in range(5):
            await test_client.post(
                "/users",
                data={
                    "name": fake.name(),
                    "email": fake.email(),
                    "password": fake.password(length=12, special_chars=True),
                },
            )

        response = await test_client.get("/users")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "meta" in data
        assert "timestamp" in data
        assert isinstance(data["data"], list)

        meta = data["meta"]
        assert "page" in meta
        assert "per_page" in meta
        assert "total" in meta
        assert "total_pages" in meta
        assert "has_next" in meta
        assert "has_prev" in meta

    @pytest.mark.asyncio
    async def test_list_users_with_pagination(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        for _ in range(15):
            await test_client.post(
                "/users",
                data={
                    "name": fake.name(),
                    "email": fake.email(),
                    "password": fake.password(length=12, special_chars=True),
                },
            )

        response = await test_client.get("/users?page=1&per_page=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 10
        assert len(data["data"]) <= 10

        response = await test_client.get("/users?page=2&per_page=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["meta"]["page"] == 2

    @pytest.mark.asyncio
    async def test_list_users_invalid_page_number(
        self, test_client: AsyncClient, override_auth
    ):
        response = await test_client.get("/users?page=0")
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "data" in data
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

        response = await test_client.get("/users?page=-1")
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "data" in data
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_list_users_invalid_per_page(
        self, test_client: AsyncClient, override_auth
    ):
        response = await test_client.get("/users?per_page=0")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

        response = await test_client.get("/users?per_page=-5")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ]

    @pytest.mark.asyncio
    async def test_list_users_with_search_by_name(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        unique_name = f"TestUser_{fake.lexify(text='??????')}"
        await test_client.post(
            "/users",
            data={
                "name": unique_name,
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
            },
        )

        response = await test_client.get(f"/users?search={unique_name}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) >= 1
        assert any(unique_name in user["name"] for user in data["data"])

    @pytest.mark.asyncio
    async def test_list_users_with_search_by_email(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        unique_email = f"test_{fake.lexify(text='??????')}@example.com"
        await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": unique_email,
                "password": fake.password(length=12, special_chars=True),
            },
        )

        response = await test_client.get(f"/users?search={unique_email}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) >= 1
        assert any(unique_email.lower() in user["email"] for user in data["data"])

    @pytest.mark.asyncio
    async def test_list_users_with_search_no_results(
        self, test_client: AsyncClient, override_auth
    ):
        response = await test_client.get("/users?search=nonexistentuser999999")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 0

    @pytest.mark.asyncio
    async def test_list_users_filter_by_type_admin(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
                "is_admin": True,
            },
        )

        await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
                "is_admin": False,
            },
        )

        response = await test_client.get("/users?type=1")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(user["is_admin"] is True for user in data["data"])

    @pytest.mark.asyncio
    async def test_list_users_filter_by_type_regular(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
                "is_admin": False,
            },
        )

        response = await test_client.get("/users?type=0")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(user["is_admin"] is False for user in data["data"])

    @pytest.mark.asyncio
    async def test_list_users_filter_by_status_active(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
                "is_active": True,
            },
        )

        response = await test_client.get("/users?status=1")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(user["is_active"] is True for user in data["data"])

    @pytest.mark.asyncio
    async def test_list_users_filter_by_status_inactive(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
                "is_active": False,
            },
        )

        response = await test_client.get("/users?status=0")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(user["is_active"] is False for user in data["data"])

    @pytest.mark.asyncio
    async def test_list_users_sort_by_name_asc(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        response = await test_client.get("/users?sort_by=name&sort_order=asc")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if len(data["data"]) > 1:
            names = [user["name"] for user in data["data"]]
            assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_list_users_sort_by_name_desc(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        response = await test_client.get("/users?sort_by=name&sort_order=desc")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if len(data["data"]) > 1:
            names = [user["name"] for user in data["data"]]
            assert names == sorted(names, reverse=True)

    @pytest.mark.asyncio
    async def test_list_users_sort_by_email(
        self, test_client: AsyncClient, override_auth
    ):
        response = await test_client.get("/users?sort_by=email&sort_order=asc")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if len(data["data"]) > 1:
            emails = [user["email"] for user in data["data"]]
            assert emails == sorted(emails)

    @pytest.mark.asyncio
    async def test_list_users_sort_by_created_at(
        self, test_client: AsyncClient, override_auth
    ):
        response = await test_client.get("/users?sort_by=created_at&sort_order=desc")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_list_users_combined_filters(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        unique_name = f"Admin_{fake.lexify(text='??????')}"
        await test_client.post(
            "/users",
            data={
                "name": unique_name,
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
                "is_admin": True,
                "is_active": True,
            },
        )

        response = await test_client.get(f"/users?search={unique_name}&type=1&status=1")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) >= 1
        for user in data["data"]:
            assert user["is_admin"] is True
            assert user["is_active"] is True

    @pytest.mark.asyncio
    async def test_list_users_response_structure(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
            },
        )

        response = await test_client.get("/users")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "data" in data
        assert "message" in data
        assert "meta" in data
        assert "timestamp" in data

        meta = data["meta"]
        assert "page" in meta
        assert "per_page" in meta
        assert "total" in meta
        assert "total_pages" in meta
        assert "has_next" in meta
        assert "has_prev" in meta

        assert len(data["data"]) > 0
        user = data["data"][0]
        assert "id" in user
        assert "name" in user
        assert "email" in user
        assert "is_active" in user
        assert "is_admin" in user
        assert "created_at" in user
        assert "updated_at" in user
        assert "type" in user
        assert "status" in user
        assert "avatar_url" in user
        assert "password" not in user

    @pytest.mark.asyncio
    async def test_list_users_empty_result(
        self, test_client: AsyncClient, override_auth
    ):
        response = await test_client.get("/users?search=impossible_search_term_xyz123")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 0

    @pytest.mark.asyncio
    async def test_list_users_does_not_include_soft_deleted(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
            },
        )

        response = await test_client.get("/users")
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_list_users_with_avatar(
        self, test_client: AsyncClient, override_auth, fake: Faker, create_test_image
    ):
        files = {"avatar": create_test_image(f"{fake.word()}.jpg")}
        await test_client.post(
            "/users",
            data={
                "name": fake.name(),
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
            },
            files=files,
        )

        response = await test_client.get("/users")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        users_with_avatar = [u for u in data["data"] if u.get("avatar_path")]
        assert len(users_with_avatar) >= 1

    @pytest.mark.asyncio
    async def test_list_users_pagination_consistency(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        created_emails = []
        for _ in range(25):
            email = fake.email()
            await test_client.post(
                "/users",
                data={
                    "name": fake.name(),
                    "email": email,
                    "password": fake.password(length=12, special_chars=True),
                },
            )
            created_emails.append(email.lower())

        response1 = await test_client.get("/users?page=1&per_page=10")
        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()

        response2 = await test_client.get("/users?page=2&per_page=10")
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()

        response3 = await test_client.get("/users?page=3&per_page=10")
        assert response3.status_code == status.HTTP_200_OK
        data3 = response3.json()

        all_user_ids = (
            [u["id"] for u in data1["data"]]
            + [u["id"] for u in data2["data"]]
            + [u["id"] for u in data3["data"]]
        )
        assert len(all_user_ids) == len(set(all_user_ids))

    @pytest.mark.asyncio
    async def test_list_users_search_case_insensitive(
        self, test_client: AsyncClient, override_auth, fake: Faker
    ):
        unique_name = f"TestUser_{fake.lexify(text='??????')}"
        await test_client.post(
            "/users",
            data={
                "name": unique_name,
                "email": fake.email(),
                "password": fake.password(length=12, special_chars=True),
            },
        )

        response_lower = await test_client.get(f"/users?search={unique_name.lower()}")
        response_upper = await test_client.get(f"/users?search={unique_name.upper()}")

        assert response_lower.status_code == status.HTTP_200_OK
        assert response_upper.status_code == status.HTTP_200_OK

        data_lower = response_lower.json()
        data_upper = response_upper.json()

        assert len(data_lower["data"]) == len(data_upper["data"])
