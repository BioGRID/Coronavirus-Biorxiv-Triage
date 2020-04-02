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
import spacy
from nltk.stem.snowball import SnowballStemmer
from collections import Counter

data_file = 'downloads/data.json'
output_file = 'downloads/results.csv'
biorxiv_url = 'https://connect.biorxiv.org/relate/collection_json.php?grp=181'
high_file = 'high_hits.txt'
med_file = 'med_hits.txt'
low_file = 'low_hits.txt'
stemmer = SnowballStemmer( language='english' )

def is_token_allowed( token ) :
    """ Only allow valid tokens """
    if (not token or not token.string.strip() or token.is_stop or token.is_punct) :
        return False
    return True

def preprocess_token( token ) :
    """ Preprocess a token """
    token = token.lemma_.strip().lower()
    return stemmer.stem(token)

def author_clean( author ) :
    """ Clean an author and return the formatted string """
    replace = ['.',';',' ',',','_','-']
    author_split = author.strip().split(",")
    clean_author = ""
    if len(author_split) >= 2 :
        last_name = author_split[0]
        first_name = author_split[1]
        for rep in replace :
            first_name = first_name.replace( rep, '' )
        clean_author = last_name + " " + first_name
    else :
        for rep in replace :
            clean_author = author.replace( rep, '' )

    return clean_author

def format_author_short( authors, date ) :
    """ Create an authors short formatted author entry """
    author = author_clean( authors[0] )
    date_split = date.split("-")
    author = author + " (" + date_split[0] + ")"
    return author 

def calculate_score_and_matching_keywords( keywords, doc_tokens, site ) :
    """ Generate a score for each paper based on occurrences of triage keywords """
    score = 0
    matching_keywords = []
    for keyword in keywords :
        if keyword in doc_tokens :
            score += doc_tokens[keyword]
            matching_keywords.append(keyword)

    return sorted(matching_keywords), score

def fetch_keyword_set( file_name, nlp ) :
    """ Fetch a set of keywords out of a file """
    keywords = set()
    with open( file_name, 'r' ) as f :
        for line in f :
            keywords.add(line.replace("-", "").strip())
    
    keywords = nlp( " ".join(keywords) )
    keywords = [preprocess_token(token) for token in keywords if is_token_allowed(token)]

    return set(keywords)

def main(args):
    # If download argument is set, grab the latest json from BioRxiv
    if args.download :
        resp = requests.get( biorxiv_url )
        if resp.status_code == 200 :
            data = ujson.loads(resp.text)
            with open( data_file, 'w' ) as f :
                ujson.dump(data, f)
        else :
            print( resp )
            sys.exit(0)

    nlp = spacy.load('en_core_web_sm')

    # Load data from json data file
    with open( data_file, 'r' ) as f :
        data = ujson.load( f )

    # Fetch Keyword Sets
    high_keywords = fetch_keyword_set( high_file, nlp )
    med_keywords = fetch_keyword_set( med_file, nlp )
    low_keywords = fetch_keyword_set( low_file, nlp )

    print( 'Triaging: ' + str(len(data['rels'])) + ' preprint articles from BioRxiv and MedRxiv' )
    with open( output_file, 'w' ) as out :
        csv_out = csv.writer( out )
        csv_out.writerow(["DOI","AUTHOR_SHORT","TITLE","ABSTRACT","AUTHORS","DATE","SOURCE","LINK","DOC_SCORE","MATCHING_KEYWORDS"])
        for rel in data['rels'] :
            authors = rel['rel_authors'].split(';')
            authors = [author_clean(author) for author in authors]

            # Determine the score value for the document
            # by converting Title and Abstract to Tokens
            # and seeing how many of our keywords occur in
            # the text
            pub_doc = nlp(rel['rel_title'].replace( "-", "" ) + " " + rel['rel_abs'].replace( "-", "" ))
            filtered_tokens = [preprocess_token(token) for token in pub_doc if is_token_allowed(token)]
            token_count = Counter(filtered_tokens)

            high_matches, high_score = calculate_score_and_matching_keywords( high_keywords, token_count, rel['rel_site'] )
            med_matches, med_score = calculate_score_and_matching_keywords( med_keywords, token_count, rel['rel_site'] )
            low_matches, low_score = calculate_score_and_matching_keywords( low_keywords, token_count, rel['rel_site'] )

            matching_keywords = high_matches + med_matches + low_matches
            score = (high_score * 10) + (med_score * 5) + (low_score)

            if rel['rel_site'].lower() == "biorxiv" :
                score += 1

            file_keywords = ""
            if len(matching_keywords) > 0 :
                file_keywords = "|".join(matching_keywords)

            csv_out.writerow([
                rel['rel_doi'],
                format_author_short( authors, rel['rel_date'] ),
                rel['rel_title'],
                rel['rel_abs'],
                "|".join(authors),
                rel['rel_date'],
                rel['rel_site'],
                rel['rel_link'],
                score,
                file_keywords
            ])

            print( "Document Score: " + str(score) )
        


if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='Parse a set of papers from Biorxiv JSON, and test against a set of keywords to determine a score' )

    # Argument to load the data in the download file into the database
    parser.add_argument( '-d','--download', action='store_true', required=False, help='Download the JSON file new before starting parsing' )

    args = parser.parse_args()
    main(args)