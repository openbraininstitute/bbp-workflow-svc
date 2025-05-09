"""Logger module."""

import logging

from app.config import settings

if settings.logging_cfg_path.exists():
    logging.config.fileConfig(settings.logging_cfg_path, disable_existing_loggers=False)


L = logging.getLogger("app")
L.setLevel(logging.DEBUG if settings.debug else logging.INFO)
