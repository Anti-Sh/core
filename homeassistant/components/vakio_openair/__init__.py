"""The Vakio Openair integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, ERROR_AUTH, ERROR_CONFIG_NO_TREADY, PLATFORMS
from .vakio import Coordinator, MqttClient

_LOGGER: logging.Logger = logging.getLogger(__package__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the demo environment."""
    _LOGGER.info("Function __init__.async_setup() called")

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set the config entry up."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    data = config_entry.data

    broker = MqttClient(hass, data)

    # Попытка подключения к брокеру
    if not await broker.try_connect():
        raise ConfigEntryAuthFailed(ERROR_AUTH)

    coordinator: Coordinator = Coordinator(hass, data)
    await coordinator.async_config_entry_first_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady(ERROR_CONFIG_NO_TREADY)

    # Регистрация интеграции в hass
    hass.data[DOMAIN][config_entry.entry_id] = coordinator
    config_entry.add_update_listener(async_reload_entry)
    config_entry.async_on_unload(
        config_entry.add_update_listener(config_entry_update_listener)
    )
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def config_entry_update_listener(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Функция вызывается при обновлении конфигурации."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if DOMAIN not in hass.data or config_entry.entry_id not in hass.data[DOMAIN]:
        return True

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
        _LOGGER.debug(
            "Coordinator for domain %s removed, entry_id: %s",
            DOMAIN,
            config_entry.entry_id,
        )

    return unload_ok
    # return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Перезагрузка интеграции."""
    if not await async_unload_entry(hass, config_entry):
        _LOGGER.error("Failed to unload entry for domain %s", DOMAIN)
        return
    await async_setup_entry(hass, config_entry)
