import pytest

from app.config import ConfigError, load_settings

VALID = {
    "TELEGRAM_BOT_TOKEN": "123456789:AAHtestTokenValue",
    "ADMIN_ID": "555000111",
}


def test_minimal_valid_config():
    settings = load_settings(VALID)
    assert settings.admin_id == 555000111
    assert settings.group_chat_id is None
    assert settings.db_path == "/data/payments.db"
    assert settings.ai_enabled is False
    assert settings.daily_report_time.strftime("%H:%M") == "23:00"


def test_missing_token():
    with pytest.raises(ConfigError, match="TELEGRAM_BOT_TOKEN"):
        load_settings({"ADMIN_ID": "1"})


def test_malformed_token():
    with pytest.raises(ConfigError, match="noto'g'ri ko'rinishda"):
        load_settings({**VALID, "TELEGRAM_BOT_TOKEN": "abcdef"})


def test_missing_admin_id():
    with pytest.raises(ConfigError, match="ADMIN_ID"):
        load_settings({"TELEGRAM_BOT_TOKEN": VALID["TELEGRAM_BOT_TOKEN"]})


def test_non_numeric_admin_id():
    with pytest.raises(ConfigError, match="raqam bo'lishi kerak"):
        load_settings({**VALID, "ADMIN_ID": "menman"})


def test_blank_values_treated_as_unset():
    settings = load_settings({**VALID, "GROUP_CHAT_ID": "   ", "ANTHROPIC_API_KEY": ""})
    assert settings.group_chat_id is None
    assert settings.ai_enabled is False


def test_negative_group_chat_id_is_valid():
    settings = load_settings({**VALID, "GROUP_CHAT_ID": "-1001234567890"})
    assert settings.group_chat_id == "-1001234567890"


def test_invalid_group_chat_id():
    with pytest.raises(ConfigError, match="GROUP_CHAT_ID"):
        load_settings({**VALID, "GROUP_CHAT_ID": "guruhim"})


def test_report_chat_defaults_to_admin():
    assert load_settings(VALID).report_chat_id == 555000111


def test_report_chat_override():
    settings = load_settings({**VALID, "REPORT_CHAT_ID": "-100999"})
    assert settings.report_chat_id == "-100999"


def test_custom_report_time():
    settings = load_settings({**VALID, "DAILY_REPORT_TIME": "09:30"})
    assert settings.daily_report_time.strftime("%H:%M") == "09:30"


def test_invalid_report_time():
    with pytest.raises(ConfigError, match="HH:MM"):
        load_settings({**VALID, "DAILY_REPORT_TIME": "kechqurun"})


def test_invalid_timezone():
    with pytest.raises(ConfigError, match="TZ"):
        load_settings({**VALID, "TZ": "Mars/Olympus"})


def test_ai_enabled_when_key_present():
    settings = load_settings({**VALID, "ANTHROPIC_API_KEY": "sk-ant-test"})
    assert settings.ai_enabled is True


def test_network_defaults_are_generous():
    settings = load_settings(VALID)
    assert settings.network_timeout == 30.0
    assert settings.send_retries == 3


def test_network_timeout_override():
    settings = load_settings({**VALID, "NETWORK_TIMEOUT": "45"})
    assert settings.network_timeout == 45.0


def test_invalid_network_timeout():
    with pytest.raises(ConfigError, match="raqam bo'lishi kerak"):
        load_settings({**VALID, "NETWORK_TIMEOUT": "sekin"})

    with pytest.raises(ConfigError, match="musbat"):
        load_settings({**VALID, "NETWORK_TIMEOUT": "-5"})


def test_reaction_defaults():
    settings = load_settings(VALID)
    assert settings.reaction_received == "👀"
    assert settings.reaction_paid == "👌"


def test_reaction_override():
    settings = load_settings({**VALID, "REACTION_PAID": "💯"})
    assert settings.reaction_paid == "💯"


def test_default_ai_model_is_the_cheap_one():
    assert load_settings(VALID).ai_model == "claude-haiku-4-5"
