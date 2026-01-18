import pytest
from httpx import AsyncClient
from fastapi import status
from faker import Faker


class TestAuthFeatures:
    @pytest.mark.asyncio
    async def test_complete_user_registration_and_login_flow(
        self, test_client: AsyncClient, fake: Faker
    ):
        email = fake.email()
        password = fake.password(
            length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
        )
        name = fake.name()

        register_response = await test_client.post(
            "/auth/register",
            data={
                "name": name,
                "email": email,
                "password": password,
                "confirm_password": password,
            },
        )

        assert register_response.status_code == status.HTTP_201_CREATED
        register_data = register_response.json()
        assert register_data["success"] is True
        assert "access_token" in register_data["data"]
        assert "refresh_token" in register_data["data"]
        register_token = register_data["data"]["access_token"]

        me_response = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {register_token}"},
        )

        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["data"]["email"] == email.lower()

        login_response = await test_client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert login_response.status_code == status.HTTP_200_OK
        login_data = login_response.json()
        assert "access_token" in login_data["data"]
        login_token = login_data["data"]["access_token"]

        me_response2 = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {login_token}"},
        )

        assert me_response2.status_code == status.HTTP_200_OK
        assert me_response2.json()["data"]["name"] == name

    @pytest.mark.asyncio
    async def test_complete_token_refresh_flow(
        self, test_client: AsyncClient, fake: Faker
    ):
        email = fake.email()
        password = fake.password(
            length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
        )

        await test_client.post(
            "/auth/register",
            data={
                "name": fake.name(),
                "email": email,
                "password": password,
                "confirm_password": password,
            },
        )

        login_response = await test_client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        old_access_token = login_response.json()["data"]["access_token"]
        old_refresh_token = login_response.json()["data"]["refresh_token"]

        refresh_response = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )

        assert refresh_response.status_code == status.HTTP_200_OK
        new_access_token = refresh_response.json()["data"]["access_token"]
        new_refresh_token = refresh_response.json()["data"]["refresh_token"]
        assert new_access_token != old_access_token
        assert new_refresh_token != old_refresh_token

        me_response = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )

        assert me_response.status_code == status.HTTP_200_OK

        old_me_response = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {old_access_token}"},
        )

        assert old_me_response.status_code == status.HTTP_401_UNAUTHORIZED

        old_refresh_response = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )

        assert old_refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_complete_logout_flow(self, test_client: AsyncClient, fake: Faker):
        email = fake.email()
        password = fake.password(
            length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
        )

        await test_client.post(
            "/auth/register",
            data={
                "name": fake.name(),
                "email": email,
                "password": password,
                "confirm_password": password,
            },
        )

        login1 = await test_client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        token1 = login1.json()["data"]["access_token"]
        refresh1 = login1.json()["data"]["refresh_token"]

        login2 = await test_client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        token2 = login2.json()["data"]["access_token"]
        refresh2 = login2.json()["data"]["refresh_token"]

        logout_response = await test_client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token1}"},
        )

        assert logout_response.status_code == status.HTTP_200_OK

        me1 = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token1}"},
        )
        me2 = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert me1.status_code == status.HTTP_401_UNAUTHORIZED
        assert me2.status_code == status.HTTP_401_UNAUTHORIZED

        ref1 = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh1},
        )
        ref2 = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh2},
        )
        assert ref1.status_code == status.HTTP_401_UNAUTHORIZED
        assert ref2.status_code == status.HTTP_401_UNAUTHORIZED

        new_login = await test_client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )

        assert new_login.status_code == status.HTTP_200_OK
        new_token = new_login.json()["data"]["access_token"]

        me_new = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert me_new.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_complete_profile_update_flow(
        self, test_client: AsyncClient, fake: Faker, create_test_image
    ):
        email = fake.email()
        password = fake.password(
            length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
        )
        original_name = fake.name()

        await test_client.post(
            "/auth/register",
            data={
                "name": original_name,
                "email": email,
                "password": password,
                "confirm_password": password,
            },
        )

        login_response = await test_client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        token = login_response.json()["data"]["access_token"]

        new_name = fake.name()
        update_response = await test_client.patch(
            "/auth/me",
            data={
                "name": new_name,
                "phone": "+84987654321",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["data"]["name"] == new_name
        assert update_response.json()["data"]["phone"] == "+84987654321"

        me_response = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["data"]["name"] == new_name

        files = {"avatar": create_test_image(f"{fake.word()}.jpg")}
        avatar_response = await test_client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
        )

        assert avatar_response.status_code == status.HTTP_200_OK

        new_email = fake.email()
        email_update = await test_client.patch(
            "/auth/me",
            data={"email": new_email},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert email_update.status_code == status.HTTP_200_OK

        old_token_response = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert old_token_response.status_code == status.HTTP_401_UNAUTHORIZED

        new_login = await test_client.post(
            "/auth/login",
            json={"email": new_email, "password": password},
        )

        assert new_login.status_code == status.HTTP_200_OK
        new_token = new_login.json()["data"]["access_token"]

        final_me = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )

        assert final_me.status_code == status.HTTP_200_OK
        final_data = final_me.json()["data"]
        assert final_data["email"] == new_email.lower()
        assert final_data["name"] == new_name
        assert final_data["phone"] == "+84987654321"

    @pytest.mark.asyncio
    async def test_complete_password_change_flow(
        self, test_client: AsyncClient, fake: Faker
    ):
        email = fake.email()
        old_password = fake.password(
            length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
        )

        await test_client.post(
            "/auth/register",
            data={
                "name": fake.name(),
                "email": email,
                "password": old_password,
                "confirm_password": old_password,
            },
        )

        login_response = await test_client.post(
            "/auth/login",
            json={"email": email, "password": old_password},
        )
        old_token = login_response.json()["data"]["access_token"]
        old_refresh = login_response.json()["data"]["refresh_token"]

        new_password = fake.password(
            length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
        )
        update_response = await test_client.patch(
            "/auth/me",
            data={"password": new_password},
            headers={"Authorization": f"Bearer {old_token}"},
        )

        assert update_response.status_code == status.HTTP_200_OK

        old_pass_login = await test_client.post(
            "/auth/login",
            json={"email": email, "password": old_password},
        )

        assert old_pass_login.status_code == status.HTTP_401_UNAUTHORIZED

        old_token_me = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )

        assert old_token_me.status_code == status.HTTP_401_UNAUTHORIZED

        old_refresh_response = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": old_refresh},
        )

        assert old_refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

        new_login = await test_client.post(
            "/auth/login",
            json={"email": email, "password": new_password},
        )

        assert new_login.status_code == status.HTTP_200_OK
        new_token = new_login.json()["data"]["access_token"]

        me_response = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )

        assert me_response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_complete_user_journey_with_avatar(
        self, test_client: AsyncClient, fake: Faker, create_test_image
    ):
        email = fake.email()
        password = fake.password(
            length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
        )
        name = fake.name()

        files = {"avatar": create_test_image(f"{fake.word()}.jpg")}
        register_response = await test_client.post(
            "/auth/register",
            data={
                "name": name,
                "email": email,
                "password": password,
                "confirm_password": password,
            },
            files=files,
        )

        assert register_response.status_code == status.HTTP_201_CREATED
        register_data = register_response.json()
        assert register_data["data"]["user_info"]["avatar_path"] is not None
        first_avatar_path = register_data["data"]["user_info"]["avatar_path"]

        login_response = await test_client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        token = login_response.json()["data"]["access_token"]

        me_response = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["data"]["avatar_path"] == first_avatar_path

        new_files = {"avatar": create_test_image(f"{fake.word()}.jpg")}
        update_response = await test_client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            files=new_files,
        )

        assert update_response.status_code == status.HTTP_200_OK
        new_avatar_path = update_response.json()["data"]["avatar_path"]
        assert new_avatar_path is not None
        assert new_avatar_path != first_avatar_path

        final_me = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert final_me.status_code == status.HTTP_200_OK
        assert final_me.json()["data"]["avatar_path"] == new_avatar_path

    @pytest.mark.asyncio
    async def test_multiple_users_independent_sessions(
        self, test_client: AsyncClient, fake: Faker
    ):
        user1_email = fake.email()
        user1_password = fake.password(
            length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
        )
        user1_name = fake.name()

        user2_email = fake.email()
        user2_password = fake.password(
            length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
        )
        user2_name = fake.name()

        await test_client.post(
            "/auth/register",
            data={
                "name": user1_name,
                "email": user1_email,
                "password": user1_password,
                "confirm_password": user1_password,
            },
        )

        await test_client.post(
            "/auth/register",
            data={
                "name": user2_name,
                "email": user2_email,
                "password": user2_password,
                "confirm_password": user2_password,
            },
        )

        login1 = await test_client.post(
            "/auth/login",
            json={"email": user1_email, "password": user1_password},
        )
        token1 = login1.json()["data"]["access_token"]

        login2 = await test_client.post(
            "/auth/login",
            json={"email": user2_email, "password": user2_password},
        )
        token2 = login2.json()["data"]["access_token"]

        me1 = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token1}"},
        )
        me2 = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token2}"},
        )

        assert me1.status_code == status.HTTP_200_OK
        assert me2.status_code == status.HTTP_200_OK
        assert me1.json()["data"]["name"] == user1_name
        assert me2.json()["data"]["name"] == user2_name

        await test_client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token1}"},
        )

        me1_after = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert me1_after.status_code == status.HTTP_401_UNAUTHORIZED

        me2_after = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert me2_after.status_code == status.HTTP_200_OK
        assert me2_after.json()["data"]["name"] == user2_name

    @pytest.mark.asyncio
    async def test_token_lifecycle_and_security(
        self, test_client: AsyncClient, fake: Faker
    ):
        email = fake.email()
        password = fake.password(
            length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
        )

        await test_client.post(
            "/auth/register",
            data={
                "name": fake.name(),
                "email": email,
                "password": password,
                "confirm_password": password,
            },
        )

        login_response = await test_client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        access_token = login_response.json()["data"]["access_token"]
        refresh_token = login_response.json()["data"]["refresh_token"]

        me_with_refresh = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert me_with_refresh.status_code == status.HTTP_401_UNAUTHORIZED

        refresh_with_access = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert refresh_with_access.status_code == status.HTTP_401_UNAUTHORIZED

        me_response = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.status_code == status.HTTP_200_OK

        refresh_response = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        new_access = refresh_response.json()["data"]["access_token"]
        new_refresh = refresh_response.json()["data"]["refresh_token"]

        old_me = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert old_me.status_code == status.HTTP_401_UNAUTHORIZED

        old_refresh_attempt = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert old_refresh_attempt.status_code == status.HTTP_401_UNAUTHORIZED

        new_me = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert new_me.status_code == status.HTTP_200_OK

        await test_client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {new_access}"},
        )

        final_me = await test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert final_me.status_code == status.HTTP_401_UNAUTHORIZED

        final_refresh = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": new_refresh},
        )
        assert final_refresh.status_code == status.HTTP_401_UNAUTHORIZED
