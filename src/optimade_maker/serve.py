import json
import os
import traceback
import warnings
from pathlib import Path

import bson.json_util
import uvicorn

from optimade_maker.logger import LOGGER


def get_optimake_provider_info(index_base_url=None):
    info = {
        "prefix": "optimake",
        "name": "Optimake",
        "description": "Provider created with optimade-maker",
        "homepage": "https://github.com/materialscloud-org/optimade-maker",
        "index_base_url": index_base_url,
    }
    if index_base_url:
        info["index_base_url"] = index_base_url

    return info


def set_config_env_variables(config_dict):
    """Set optimade environment variables used by the API, according to a config dictionary.

    Notes:
    When starting the fastapi of optimade-python-tools, the ServerConfig seems to be read
    either from
    * environment variables starting with 'OPTIMADE_'; or
    * config file specified either by OPTIMADE_CONFIG_FILE or DEFAULT_CONFIG_FILE_PATH;
    there doesn't seem to be a way to just pass in the config directly.

    Therefore, just specify the config through environment variables.
    """
    for key, value in config_dict.items():
        env_var = f"OPTIMADE_{key}"
        if isinstance(value, (dict, list, bool)):
            os.environ[env_var] = json.dumps(value)
        elif value is None:
            os.environ[env_var] = "null"
        else:
            os.environ[env_var] = str(value)


def get_provider_fields_from_jsonl(jsonl_path: Path):
    """
    Go through the "info" collection of the corresponding MongoDB and get the
    provider fields (custom properties)
    """

    info_types = ["structures", "references"]

    provider_fields = {}

    def _read_custom_fields(properties, info_type):
        if info_type not in info_types:
            return None

        fields = []
        for prop, val in properties.items():
            # if property name starts with underscore, it's a custom one
            if prop.startswith("_"):
                provider_field_entry = {
                    "name": prop,
                }
                # add only the keys that are not None.
                for key in ["description", "unit", "type"]:
                    if val.get(key) is not None:
                        provider_field_entry[key] = val.get(key)
                fields.append(provider_field_entry)
        if fields:
            provider_fields[info_type] = fields

    with open(jsonl_path, "r") as fhandle:
        try:
            for line_no, json_str in enumerate(fhandle):
                try:
                    entry = bson.json_util.loads(json_str)
                except json.JSONDecodeError:
                    warnings.warn(f"Found bad JSONL line at L{line_no}")
                    continue

                if "properties" in entry:
                    if "type" not in entry:
                        # possible pre-1.2 info endpoint
                        if "description" in entry:
                            _read_custom_fields(
                                entry["properties"], entry["description"]
                            )
                    else:
                        # 1.2+ info endpoints include type & id
                        if entry["type"] == "info":
                            _read_custom_fields(entry["properties"], entry["id"])

                elif "x-optimade" in entry:
                    continue
                # If this isn't an info endpoint, or the first line header, then we break
                # as presumably we have reached the data itself
                else:
                    break

        except Exception as exc:
            traceback.print_exc()
            print(f"Error {exc}")
    return provider_fields


class OptimakeServer:
    """
    Class to handle input parameters and configuration to start the optimade-python-tools API.
    Uses the MongoMock backend.
    """

    def __init__(self, path: Path, port: int = 5000, **config_kws):
        """Initialise the OptimakeServer instance.

        Parameters:
            path: Path to the directory containing the optimade.jsonl file.
            port: Port to run the API on.
            config_kws: Additional optimade-python-tools configuration options to pass to the API.

        """
        self.path = path
        self.port = port
        self.config_kws = config_kws

        self.base_url = f"http://localhost:{self.port}"
        # self.index_base_url = "http://localhost:5001"

    def get_optimade_config(self):
        jsonl_path = self.path / "optimade.jsonl"

        provider_fields = get_provider_fields_from_jsonl(jsonl_path)

        LOGGER.debug(f"PROVIDER_FIELDS: {provider_fields}")

        config_dict = {
            "debug": False,
            "insert_test_data": False,
            "insert_from_jsonl": str(jsonl_path.resolve()),
            "create_default_index": True,
            "base_url": self.base_url,
            "provider": get_optimake_provider_info(),
            # "index_base_url": self.index_base_url,
            "provider_fields": provider_fields,
            "log_dir": str(self.path.resolve()),
        }

        config_dict.update(self.config_kws)

        # Loop through any environment variables that start with "OPTIMAKE_" and set them
        for env in os.environ:
            if env.startswith("OPTIMAKE_"):
                LOGGER.debug(
                    "Reading environment variable %s into config with value %s",
                    env,
                    os.environ[env],
                )
                config_dict[env.replace("OPTIMAKE_", "").lower()] = os.environ[env]

        LOGGER.debug(f"CONFIG: {config_dict}")

        return config_dict

    def start_api(self):
        set_config_env_variables(self.get_optimade_config())
        uvicorn.run("optimade.server.main:app", host="0.0.0.0", port=self.port)
