import yaml
import os
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

logger = CustomLogger().get_logger(__file__)

def load_config(config_path: str = "config/config.yaml") -> dict:
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)

        logger.info(
            "config_loaded",
            config_path=config_path
        )
        return config

    except Exception as e:
        logger.error(
            "config_load_failed",
            config_path=config_path,
            error=str(e)
        )
        raise DocumentPortalException("Failed to load configuration", e) from e
# if __name__ == "__main__":
#     load_config("config/config.yaml")
