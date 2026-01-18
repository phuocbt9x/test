from faker import Faker

fake = Faker()


def get_example_uuid() -> str:
    return fake.uuid4()


def get_example_password() -> str:
    return "P@ssw0rd123!"


def get_example_name() -> str:
    return fake.name()


def get_example_email() -> str:
    return "john.doe@example.com"


def get_example_phone() -> str:
    return fake.numerify(text="0#########")


def get_example_line_id() -> str:
    return "U" + fake.bothify(
        text="????????????????????", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    )


def get_example_authentication_token() -> str:
    return (
        fake.bothify(
            text="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.",
            letters="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        )
        + "..."
    )


def get_example_type() -> str:
    return fake.random_element(elements=["admin", "user"])


def get_example_status() -> str:
    return fake.random_element(elements=["active", "inactive"])


def get_example_path() -> str:
    return fake.file_path(depth=3, extension="jpg")


def get_example_avatar_url() -> str:
    return fake.image_url(width=256, height=256)


def get_example_timestamp() -> str:
    dt = fake.date_time_this_decade()
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "get_example_uuid",
    "get_example_password",
    "get_example_name",
    "get_example_email",
    "get_example_phone",
    "get_example_line_id",
    "get_example_authentication_token",
    "get_example_type",
    "get_example_status",
    "get_example_path",
    "get_example_avatar_url",
    "get_example_timestamp",
]
