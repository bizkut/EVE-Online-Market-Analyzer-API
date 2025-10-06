import logging
import os
import sys


def setup_logging():
    """
    Configures the root logger for the application.

    This function should be called once when the application starts. By importing
    this module, the `setup_logging()` function is automatically executed.

    It sets up a handler that logs to stdout, which is standard for
    containerized applications. It respects the LOG_LEVEL environment variable.
    """
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicate logs or conflicts with
    # other libraries that might also configure the root logger.
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Add a new handler to stream to stdout
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # For debugging purposes, log that the configuration is complete.
    # We use the root logger directly here as this is the configuration module.
    logging.info(f"Logging has been configured with level {log_level_str}.")


# Set up the logger immediately when this module is imported.
# Any module that needs logging should import this module at the top
# to ensure the configuration is applied before any log messages are emitted.
setup_logging()