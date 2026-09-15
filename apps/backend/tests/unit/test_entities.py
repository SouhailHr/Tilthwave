from core.entities.farm import Farm
from core.entities.users import Users


def _user(**overrides):
    data = dict(
        username="jo",
        password="$2b$12$hash",
        email="jo@example.com",
        phone_number="+1",
        first_name="Jo",
        last_name="Doe",
        role="worker",
    )
    data.update(overrides)
    return Users(**data)


def test_to_dict_keeps_password_for_persistence():
    assert _user().to_dict()["password"] == "$2b$12$hash"


def test_to_public_dict_strips_password_and_nothing_else():
    user = _user()
    public = user.to_public_dict()
    assert "password" not in public
    assert public == {k: v for k, v in user.to_dict().items() if k != "password"}


def test_new_private_field_is_hidden_without_overriding_anything():
    class Secretive(Users):
        PRIVATE_FIELDS = ("password", "email")

    public = Secretive(**{k: v for k, v in _user().to_dict().items()}).to_public_dict()
    assert "email" not in public and "password" not in public


def test_entities_without_secrets_are_fully_public():
    farm = Farm(farm_name="F", address="a", location={}, size=1.0)
    assert farm.to_public_dict() == farm.to_dict()
