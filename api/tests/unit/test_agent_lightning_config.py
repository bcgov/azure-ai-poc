"""Test cases for agent_lightning_config.py (Agent Lightning configuration).

This module tests configuration management and factory functions for integrating
Agent Lightning with existing LangGraph agents. Tests written FIRST per TDD approach.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.core.agent_lightning_config import (
    AgentLightningSettings,
    create_optimization_config,
    get_agent_lightning_settings,
    is_agent_lightning_available,
    wrap_agent_with_lightning,
)
from app.models.optimization_models import OptimizationConfig


class TestAgentLightningSettings:
    """Test cases for AgentLightningSettings Pydantic settings model."""

    def test_settings_default_values(self) -> None:
        """Test AgentLightningSettings loads with default values."""
        settings = AgentLightningSettings()

        assert settings.enabled is False
        assert settings.api_key is None
        assert settings.api_endpoint is None
        assert settings.enable_rl is True
        assert settings.enable_prompt_opt is True
        assert settings.enable_sft is False
        assert settings.optimization_interval == 50
        assert settings.wrapper_timeout_ms == 100

    def test_settings_load_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test AgentLightningSettings loads from environment variables."""
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLED", "true")
        monkeypatch.setenv("AGENT_LIGHTNING_API_KEY", "test-api-key-123")
        monkeypatch.setenv("AGENT_LIGHTNING_API_ENDPOINT", "https://api.example.com")
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLE_RL", "false")
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLE_PROMPT_OPT", "true")
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLE_SFT", "true")
        monkeypatch.setenv("AGENT_LIGHTNING_OPTIMIZATION_INTERVAL", "100")
        monkeypatch.setenv("AGENT_LIGHTNING_WRAPPER_TIMEOUT_MS", "200")

        settings = AgentLightningSettings()

        assert settings.enabled is True
        assert settings.api_key == "test-api-key-123"
        assert settings.api_endpoint == "https://api.example.com"
        assert settings.enable_rl is False
        assert settings.enable_prompt_opt is True
        assert settings.enable_sft is True
        assert settings.optimization_interval == 100
        assert settings.wrapper_timeout_ms == 200

    def test_settings_optimization_interval_validation(self) -> None:
        """Test optimization_interval validation (must be >= 10)."""
        # Valid: minimum value
        settings = AgentLightningSettings(optimization_interval=10)
        assert settings.optimization_interval == 10

        # Invalid: below minimum
        with pytest.raises(ValidationError) as exc_info:
            AgentLightningSettings(optimization_interval=5)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("optimization_interval",) for error in errors)

    def test_settings_wrapper_timeout_validation(self) -> None:
        """Test wrapper_timeout_ms validation (10 <= value <= 1000)."""
        # Valid: minimum and maximum
        settings_min = AgentLightningSettings(wrapper_timeout_ms=10)
        assert settings_min.wrapper_timeout_ms == 10

        settings_max = AgentLightningSettings(wrapper_timeout_ms=1000)
        assert settings_max.wrapper_timeout_ms == 1000

        # Invalid: below minimum
        with pytest.raises(ValidationError):
            AgentLightningSettings(wrapper_timeout_ms=5)

        # Invalid: above maximum
        with pytest.raises(ValidationError):
            AgentLightningSettings(wrapper_timeout_ms=1001)


class TestGetAgentLightningSettings:
    """Test cases for get_agent_lightning_settings singleton function."""

    def test_get_settings_returns_singleton(self) -> None:
        """Test get_agent_lightning_settings returns same instance (singleton)."""
        # Clear global state
        import app.core.agent_lightning_config as config_module

        config_module._settings = None

        settings1 = get_agent_lightning_settings()
        settings2 = get_agent_lightning_settings()

        assert settings1 is settings2  # Same object reference

    def test_get_settings_creates_instance_on_first_call(self) -> None:
        """Test get_agent_lightning_settings creates instance on first call."""
        import app.core.agent_lightning_config as config_module

        config_module._settings = None

        settings = get_agent_lightning_settings()

        assert isinstance(settings, AgentLightningSettings)
        assert config_module._settings is settings


class TestCreateOptimizationConfig:
    """Test cases for create_optimization_config factory function."""

    def test_create_config_with_defaults_from_settings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test create_optimization_config uses settings defaults."""
        # Clear singleton and set env vars
        import app.core.agent_lightning_config as config_module

        config_module._settings = None

        monkeypatch.setenv("AGENT_LIGHTNING_ENABLE_RL", "false")
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLE_PROMPT_OPT", "true")
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLE_SFT", "true")

        config = create_optimization_config(tenant_id="tenant-123", agent_name="document_qa")

        assert config.tenant_id == "tenant-123"
        assert config.agent_name == "document_qa"
        assert config.enable_rl is False  # From env var
        assert config.enable_prompt_opt is True  # From env var
        assert config.enable_sft is True  # From env var
        assert config.metric_target == "answer_quality"  # Default

    def test_create_config_with_overrides(self) -> None:
        """Test create_optimization_config allows per-agent overrides."""
        config = create_optimization_config(
            tenant_id="tenant-456",
            agent_name="custom_agent",
            metric_target="token_efficiency",
            enable_rl=True,
            enable_prompt_opt=False,
            enable_sft=False,
        )

        assert config.tenant_id == "tenant-456"
        assert config.agent_name == "custom_agent"
        assert config.metric_target == "token_efficiency"
        assert config.enable_rl is True  # Override
        assert config.enable_prompt_opt is False  # Override
        assert config.enable_sft is False  # Override

    def test_create_config_partial_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test create_optimization_config with partial overrides."""
        # Clear singleton
        import app.core.agent_lightning_config as config_module

        config_module._settings = None

        monkeypatch.setenv("AGENT_LIGHTNING_ENABLE_RL", "true")
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLE_PROMPT_OPT", "false")
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLE_SFT", "false")

        config = create_optimization_config(
            tenant_id="tenant-789",
            agent_name="hybrid_agent",
            enable_rl=False,  # Override only this
        )

        assert config.enable_rl is False  # Overridden
        assert config.enable_prompt_opt is False  # From env var
        assert config.enable_sft is False  # From env var


class TestWrapAgentWithLightning:
    """Test cases for wrap_agent_with_lightning wrapper function."""

    def test_wrap_agent_returns_original_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test wrap_agent_with_lightning returns original agent when disabled."""
        # Clear singleton and disable
        import app.core.agent_lightning_config as config_module

        config_module._settings = None
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLED", "false")

        mock_agent = MagicMock()
        config = OptimizationConfig(tenant_id="tenant-123")

        wrapped = wrap_agent_with_lightning(mock_agent, config)

        assert wrapped is mock_agent  # Same object, not wrapped

    def test_wrap_agent_calls_agentlightning_wrap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test wrap_agent_with_lightning calls agentlightning.wrap when enabled."""
        # Clear singleton and enable
        import app.core.agent_lightning_config as config_module

        config_module._settings = None
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLED", "true")

        mock_agent = MagicMock()
        mock_wrapped_agent = MagicMock()

        # Mock agentlightning module at import time
        mock_agentlightning = MagicMock()
        mock_agentlightning.wrap.return_value = mock_wrapped_agent

        config = OptimizationConfig(
            tenant_id="tenant-123",
            agent_name="test_agent",
            enable_rl=True,
            enable_prompt_opt=False,
            enable_sft=False,
            metric_target="latency",
        )

        with patch.dict("sys.modules", {"agentlightning": mock_agentlightning}):
            wrapped = wrap_agent_with_lightning(mock_agent, config)

            # Verify agentlightning.wrap was called with correct params
            mock_agentlightning.wrap.assert_called_once_with(
                mock_agent,
                tenant_id="tenant-123",
                agent_name="test_agent",
                optimization_config={
                    "enable_rl": True,
                    "enable_prompt_opt": False,
                    "enable_sft": False,
                    "metric_target": "latency",
                },
            )
            assert wrapped is mock_wrapped_agent

    def test_wrap_agent_raises_import_error_when_package_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test wrap_agent_with_lightning raises ImportError when package not installed."""
        # Clear singleton and enable
        import app.core.agent_lightning_config as config_module

        config_module._settings = None
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLED", "true")

        # Simulate missing agentlightning package
        import sys

        original_modules = sys.modules.copy()

        # Remove agentlightning from sys.modules if present
        if "agentlightning" in sys.modules:
            del sys.modules["agentlightning"]

        # Mock the import to fail
        with patch.dict(
            sys.modules,
            {"agentlightning": None},  # type: ignore[arg-type]
        ):
            mock_agent = MagicMock()
            config = OptimizationConfig(tenant_id="tenant-123")

            with pytest.raises(ImportError, match="agentlightning package not installed"):
                wrap_agent_with_lightning(mock_agent, config)

        # Restore original modules
        sys.modules.update(original_modules)


class TestIsAgentLightningAvailable:
    """Test cases for is_agent_lightning_available availability check."""

    def test_available_when_installed_and_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test is_agent_lightning_available returns True when installed and enabled."""
        # Clear singleton and enable
        import app.core.agent_lightning_config as config_module

        config_module._settings = None
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLED", "true")

        # Mock agentlightning as installed
        mock_agentlightning = MagicMock()
        with patch.dict("sys.modules", {"agentlightning": mock_agentlightning}):
            assert is_agent_lightning_available() is True

    def test_unavailable_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test is_agent_lightning_available returns False when disabled."""
        # Clear singleton and disable
        import app.core.agent_lightning_config as config_module

        config_module._settings = None
        monkeypatch.setenv("AGENT_LIGHTNING_ENABLED", "false")

        # Mock agentlightning as installed (but disabled via settings)
        mock_agentlightning = MagicMock()
        with patch.dict("sys.modules", {"agentlightning": mock_agentlightning}):
            assert is_agent_lightning_available() is False

    def test_unavailable_when_not_installed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test is_agent_lightning_available returns False when package not installed."""
        # Clear singleton
        import app.core.agent_lightning_config as config_module

        config_module._settings = None

        # Simulate missing agentlightning package
        import sys

        original_modules = sys.modules.copy()

        if "agentlightning" in sys.modules:
            del sys.modules["agentlightning"]

        with patch.dict(
            sys.modules,
            {"agentlightning": None},  # type: ignore[arg-type]
        ):
            assert is_agent_lightning_available() is False

        # Restore
        sys.modules.update(original_modules)
