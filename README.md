# BioGRID-Coronavirus-Biorxiv-Triage
A simple script to take the Biorxiv Coronavirus Collection and Triage it for interaction terms

## Requirements
+ Pipenv (https://pypi.org/project/pipenv/)
+ Python 3.6.9 (https://www.python.org/)

## Configuration
+ You need to create a new file called `config/config.yml` containing the settings for your implementation. You can use the `config/config.sample.yml` file as a template.

## How to Run
+ Go into the directory containing this repository
+ Run: `pipenv shell`
+ Run: `pipenv install`
+ Run: `python -m spacy download en_core_web_sm`
+ Create a directory called `<DOWNLOAD_PATH>` (what you set `download_path` equal to in the config file)
+ Run: `python run.py -d`
+ On subsequent runs, if you don't want to re-download the json, you can simply execute: `python run.py`
+ This will create a file called `results.csv` in the `<DOWNLOAD_PATH>` folder