#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Connect to the Biorxiv collection for COVID-19/SARS-COV-2 related 
preprints, and test them against a set of keywords to try and narrow
down which ones are good candidates for curation in BioGRID
"""

import ujson
import requests
import sys
import argparse
import csv
import os
import spacy
import config as cfg
from nltk.stem.snowball import SnowballStemmer
from collections import Counter

# Initialize Config Variables
data_file = os.path.join(cfg.data["download_path"], cfg.data["data_file"])
output_file = os.path.join(cfg.data["download_path"], cfg.data["output_file"])
source_url = cfg.data["source_url"]
high_file = cfg.data["high_file"]
med_file = cfg.data["med_file"]
low_file = cfg.data["low_file"]

# Load Text Processing Tools
stemmer = SnowballStemmer(language="english")
nlp = spacy.load("en_core_web_sm")

def is_token_allowed(token):
    """ Only allow valid tokens """
    if not token or not token.string.strip() or token.is_stop or token.is_punct:
        return False
    return True

def preprocess_token(token):
    """ Preprocess a token """
    token = token.lemma_.strip().lower()
    return stemmer.stem(token)

def author_clean(author):
    """ Clean an author and return the formatted string """
    replace = [".", ";", " ", ",", "_", "-"]
    author_split = author.strip().split(",")
    clean_author = ""
    if len(author_split) >= 2:
        last_name = author_split[0]
        first_name = author_split[1]
        for rep in replace:
            first_name = first_name.replace(rep, "")
        clean_author = last_name + " " + first_name
    else:
        for rep in replace:
            clean_author = author.replace(rep, "")

    return clean_author

def format_author_short(authors, date):
    """ Create an authors short formatted author entry """
    author = author_clean(authors[0])
    date_split = date.split("-")
    author = author + " (" + date_split[0] + ")"
    return author

def calculate_score_and_matching_keywords(keywords, doc_tokens, site):
    """ Generate a score for each paper based on occurrences of triage keywords """
    score = 0
    matching_keywords = []
    for keyword in keywords:
        if keyword in doc_tokens:
            score += doc_tokens[keyword]
            matching_keywords.append(keyword)

    return sorted(matching_keywords), score

def fetch_keyword_set(file_name):
    """ Fetch a set of keywords out of a file """
    keywords = set()
    with open(file_name, "r") as f:
        for line in f:
            keywords.add(line.replace("-", "").strip())

    keywords = nlp(" ".join(keywords))
    keywords = [preprocess_token(token) for token in keywords if is_token_allowed(token)]

    return set(keywords)

# python program to print initials of a name 
def author_short(str1):
    # split the string into a list 
    lst = str1.split()
    lastNameLoc = 1
    lastname = lst[-1].title()
    if(lastname[0:2].lower() == "jr" or lastname[0:2].lower() == "sr" ) :
        lastname = lst[-2]
        lastNameLoc = 2

    initials = ""

    # traverse in the list 
    for i in range(len(lst)-lastNameLoc):
        str1 = lst[i].strip().strip(".,;")

        if len(str1) > 0 :
            # If first name or a single character
            if( i == 0 or len(str1) == 1 or str1[0].isupper() ) :
                initials += str1[0].upper()
            else :
                lastname = str1 + " " + lastname
        
    # l[-1] gives last item of list l.
    name = lastname + " " + initials
    return name

def main(args):

    header = [
        "DOI",
        "AUTHOR_SHORT",
        "TITLE",
        "ABSTRACT",
        "AUTHORS",
        "DATE",
        "SOURCE",
        "LINK",
        "DOC_SCORE",
        "MATCHING_KEYWORDS",
    ]

    # If download argument is set
    # grab the latest json from BioRxiv
    if args.download:
        resp = requests.get(source_url)
        if resp.status_code == 200:
            data = ujson.loads(resp.text)
            with open(data_file, "w") as f:
                ujson.dump(data, f)
        else:
            print(resp)
            sys.exit(0)

    # Load data from json data file
    with open(data_file, "r") as f:
        data = ujson.load(f)

    # Fetch Keyword Sets
    keyword_sets = {
        "high": fetch_keyword_set(high_file),
        "med": fetch_keyword_set(med_file),
        "low": fetch_keyword_set(low_file),
    }

    print( "Triaging: " + str(len(data["rels"])) + " preprint articles from BioRxiv and MedRxiv" )

    # Output Results to File
    with open(output_file, "w") as out:
        csv_out = csv.writer(out)
        csv_out.writerow(header)
        for rel in data["rels"]:

            # Ignore papers with no authors
            if(rel["rel_num_authors"] == 0) :
                continue

            # Clean Author Text
            # authors = rel["rel_authors"].split(";")
            # authors = [author_clean(author) for author in authors]
            authors = []
            authors = [author_clean(author_short(author["author_name"])) for author in rel["rel_authors"]]

            # Determine the score value for the document
            # by converting Title and Abstract to Tokens
            # and seeing how many of our keywords occur in
            # the text
            pub_doc = nlp( rel["rel_title"].replace("-", "") + " " + rel["rel_abs"].replace("-", "") )
            filtered_tokens = [preprocess_token(token) for token in pub_doc if is_token_allowed(token)]
            token_count = Counter(filtered_tokens)

            # Calculate the score for each set of keywords
            high_matches, high_score = calculate_score_and_matching_keywords(keyword_sets["high"], token_count, rel["rel_site"])
            med_matches, med_score = calculate_score_and_matching_keywords(keyword_sets["med"], token_count, rel["rel_site"])
            low_matches, low_score = calculate_score_and_matching_keywords(keyword_sets["low"], token_count, rel["rel_site"])

            # Combine keyword lists
            matching_keywords = high_matches + med_matches + low_matches
            file_keywords = ""
            if len(matching_keywords) > 0:
                file_keywords = "|".join(matching_keywords)

            # Calculate final score by multiplying by bounties
            score = (high_score * cfg.data["high_bounty"]) + (med_score * cfg.data["med_bounty"]) + (low_score * cfg.data["low_bounty"])

            # Add an extra bounty if it's a BioRxiv paper
            if rel["rel_site"].lower() == "biorxiv":
                score += cfg.data["biorxiv_bounty"]

            # Output to File in CSV format
            csv_out.writerow(
                [
                    rel["rel_doi"],
                    format_author_short(authors, rel["rel_date"]),
                    rel["rel_title"],
                    rel["rel_abs"],
                    "|".join(authors),
                    rel["rel_date"],
                    rel["rel_site"],
                    rel["rel_link"],
                    score,
                    file_keywords,
                ]
            )

            print("Document Score: " + str(score))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a set of papers from Biorxiv JSON, and test against a set of keywords to determine a score"
    )

    # Argument to load the data in the download file into the database
    parser.add_argument(
        "-d",
        "--download",
        action="store_true",
        required=False,
        help="Download the JSON file new before starting parsing",
    )

    args = parser.parse_args()
    main(args)
