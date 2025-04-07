"""
****************************************************************************************
* Title: parse_yml.py
* Project: ROCK-IT Containers
* This script is used to parse a yaml file and return the value of a given key.
****************************************************************************************
"""

import yaml
import re


def sanitize_input(input_string: str) -> str:
    input_string = input_string.lower()
    if not re.match("^[a-z0-9_]*$", input_string):
        raise ValueError(
            f"Invalid input: {input_string}. Input should be alphanumeric " f"and can include underscores."
        )

    return input_string


def parse_yml(*keys: str, yml_file: str = "config.yml") -> dict or str:
    """
    This function is used to parse a yaml file and return the value of a given key.
    Any number of keys can be passed to the function to navigate through the yaml file.

    :param keys: list of keys to navigate through the yaml file
    :param yml_file: path to the yaml file
    """
    with open(yml_file, "r") as f:
        yml = yaml.safe_load(f)

    # If no keys are passed, return the entire yaml file
    if not keys:
        return yml

    # Navigate through nested keys
    data = {}
    for key in keys:
        sanitized_key = sanitize_input(key)
        data = yml[sanitized_key]
        # Check if key is in the yaml file
        if data == {}:
            raise KeyError(f"Key {key} not found in the yaml file.")

    return data
