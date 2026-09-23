"""API_TRUSTED_PROXIES entries: exact addresses, networks, and test-client names."""

from interfaces.api.helpers.rate_limit import is_trusted_proxy


def test_an_address_entry_matches_only_itself():
    assert is_trusted_proxy("10.0.1.2", ["10.0.1.2"])
    assert not is_trusted_proxy("10.0.1.3", ["10.0.1.2"])


def test_a_network_entry_matches_every_address_in_it():
    assert is_trusted_proxy("10.0.1.200", ["10.0.1.0/24"])
    assert not is_trusted_proxy("10.0.2.1", ["10.0.1.0/24"])
    assert is_trusted_proxy("fd00::1", ["fd00::/64"])


def test_non_ip_entries_match_exactly_and_never_raise():
    assert is_trusted_proxy("testclient", ["testclient"])
    assert not is_trusted_proxy("testclient", ["10.0.1.0/24"])
    assert not is_trusted_proxy("10.0.1.2", ["not-an-ip"])
    assert not is_trusted_proxy("unknown", [])
