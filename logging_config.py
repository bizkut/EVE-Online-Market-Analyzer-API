import logging
import os
import sys

def setup_logging():
    """
    Sets up a centralized logger for the application.
    All modules should import the 'logger' from this module.
    """
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Configure the root logger
    # Using a stream handler to output to stdout/stderr, which is standard for containers.
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

# Set up the logger immediately when this module is imported
setup_logging()

# Create a logger instance that other modules can import
logger = logging.getLogger(__name__)