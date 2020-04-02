"""
Load the config file and create any custom variables
that are available for ease of use purposes
"""

import yaml
import os

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

with open(BASE_DIR + "/config/config.yml", "r") as configFile:
    data = configFile.read()

data = yaml.load(data, Loader=yaml.FullLoader)
