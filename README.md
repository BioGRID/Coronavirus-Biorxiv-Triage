# BioGRID-Coronavirus-Biorxiv-Triage
A simple script to take the Biorxiv Coronavirus Collection and Triage it for interaction terms

## Requirements
+ Pipenv
+ Python 3.6.9

## How to Run
+ Go into the directory containing this repository
+ Run: `pipenv shell`
+ Run: `pipenv install`
+ Run: `python -m space download en_core_web_sm`
+ Create a directory called `downloads` (or whatever you set it to in run.py)
+ Run: `python run.py -d`
+ On subsequent runs, if you don't want to re-download the json, you can simply execute: `python run.py`
+ This will create a file called `results.csv` in the `downloads` foldera