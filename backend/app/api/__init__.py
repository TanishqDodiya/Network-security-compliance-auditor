"""Aggregate all API routers in one place."""

from app.api import audits, configurations, detect, devices, extras, mappings, normalize, reports, rules

routers = [
    devices.router,
    configurations.router,
    detect.router,
    normalize.router,
    audits.router,
    rules.router,
    mappings.router,
    reports.router,
    extras.router,
]
