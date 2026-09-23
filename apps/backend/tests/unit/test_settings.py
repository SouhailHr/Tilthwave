"""The database URI is assembled from parts; a generated password must never change its shape."""

from config.settings import DatabaseSettings


def test_database_password_is_url_encoded_in_the_assembled_uri(monkeypatch):
    monkeypatch.delenv("POSTGRES_URI", raising=False)
    settings = DatabaseSettings(HOST="db", USER="postgres", PASSWORD="run `make env`/to:gen@erate .env", DB="tilthwave")
    assert settings.URI == "postgresql://postgres:run%20%60make%20env%60%2Fto%3Agen%40erate%20.env@db:5432/tilthwave"


def test_an_explicit_uri_wins(monkeypatch):
    monkeypatch.delenv("POSTGRES_URI", raising=False)
    settings = DatabaseSettings(HOST="x", USER="x", PASSWORD="x", DB="x", URI="sqlite:///t.db")
    assert settings.URI == "sqlite:///t.db"
