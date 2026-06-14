"""Entity Failover platform stub for Home Assistant."""

from .platform import make_async_setup_entry

async_setup_entry = make_async_setup_entry("binary_sensor")
