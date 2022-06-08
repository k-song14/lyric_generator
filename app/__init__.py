import crochet
crochet.setup()
import pandas as pd
import json

from flask import Flask , render_template, jsonify, request, redirect, url_for
import scrapy
from scrapy.linkextractors import LinkExtractor
from bs4 import BeautifulSoup
import requests
import re
from scrapy.crawler import CrawlerRunner
from scrapy import signals
from scrapy.signalmanager import dispatcher
import time
from itertools import islice
import re
import numpy as np
import tensorflow as tf
import string
import os
# Importing our Scraping Function from the lyrics file
from lyrics1.lyrics1.spiders.lyrics import LyricSpider

### stuff from last class
app = Flask(__name__)

output_data = []
crawl_runner = CrawlerRunner()

# By Deafult Flask will come into this when we run the file
@app.route('/')
def index():
	return render_template("index.html") # Returns index.html file in templates folder.


# After clicking the Submit Button FLASK will come into this
@app.route('/', methods=['POST'])
def submit():
    if request.method == 'POST':
        s = request.form['inp'] # Getting the Input Amazon Product URL
        global inp
        inp = s
        
        # This will remove any existing file with the same name so that the scrapy will not append the data to any previous file.


        return redirect(url_for('scrape')) # Passing to the Scrape function


@app.route("/scrape")
def scrape():

    scrape_with_crochet(form_inp=inp) # Passing that URL to our Scraping Function

    time.sleep(100)
    with open('file.json', 'w') as f:
        json.dump(output_data, f)
    
    lyrics_df = pd.read_json(output_data)
    for i in range(len(lyrics_df['lyrics'])):
        for j in range(len(lyrics_df['lyrics'][i])):
            lyrics_df['lyrics'][i][j] = re.sub("\[.*\]", "", lyrics_df['lyrics'][i][j])


    lyrics_input = ' '.join(lyrics_df['lyrics'].apply(lambda t: str(t)))
    pd.set_option("display.max_rows", None, "display.max_columns", None)
    def consec_chars(chars, n):
        '''generates n-long tuples with a sliding window'''
        for i in range(len(chars) - (n-1)):
            yield chars[i:i+n]
    
    def ngram_transition_matrix(chars, n):
        '''Generates a transition matrix given a list of characters'''
        df = pd.DataFrame(consec_chars(chars, n), columns = [str(i) for i in range(1,n+1)])
        ngroup = list(df)[:n-1]
        counts = df.groupby(ngroup)[str(n)].value_counts()
        probs = (counts / counts.groupby(level=ngroup).sum()).unstack()
        return probs.fillna(0)
    
    def standardization(text):
        text = text.lower()
        text = re.sub(r'[\(\[].*?[\)\]]', '', text)
        text = re.sub(r',\s', ',', text)
        return text

    def next_word(tup, mat):
        '''sample next word given previous n-1 characters'''
        poss = mat.loc[tup,]
        return np.random.choice(list(mat), p = poss)

    def generate_block(title, start, length, mat, n):
        '''generates a new text of the given length'''
        start_tup = tuple(start)
        # get current MultiIndex (or regular index if doing bigram)
        curr = start_tup if n > 2 else start
        lyrics = '[' + title + ']' + '\n'
        lyrics += ''.join(start_tup)
        j = 0
        while j < length:
            nxt = next_word(curr, mat)
            lyrics += nxt + ('\n' if nxt == ',' else '')
            curr = nxt if n == 2 else (*curr[1:], nxt)
            if j < length - 1 or curr[-1] == ' ':
                j += 1
        
        lyrics = re.sub(',', ', ', lyrics)
        lyrics = re.sub(' ,', ',', lyrics)
        return re.sub('\n\s', '\n', lyrics) + '\n\n'
    
    def random_start(text, n):
        spaces = [i for i in range(len(text)) if text[i] == ' ']
        j = np.random.choice(spaces)
        return text[j+1:j+n]
    
    def generate_song(text, n=2, len_verse=500, len_chorus=100, num_verses=2):
        np.random.seed()
        text = standardization(text)
        starts = [random_start(text, n) for i in range(num_verses+1)]
        chars = list(text)
        mat = ngram_transition_matrix(chars, n)
        
        song = ""
        chorus = generate_block('Chorus', starts[0], len_chorus, mat, n)

        for i in range(num_verses):
            song += generate_block('Verse ' + str(i+1), starts[i+1], len_verse, mat, n)
            song += chorus
        
        return song
    
    word = generate_song(lyrics_input, n=10)

    return render_template('scrape.html', word = word) # Returns the scraped data after being running for 20 seconds.

@crochet.run_in_reactor
def scrape_with_crochet(form_inp):
    # This will connect to the dispatcher that will kind of loop the code between these two functions.
    dispatcher.connect(_crawler_result, signal=signals.item_scraped)
    
    # This will connect to the ReviewspiderSpider function in our scrapy file and after each yield will pass to the crawler_result function.
    eventual = crawl_runner.crawl(ImdbSpider, form_inp = form_inp)
    return eventual

#This will append the data to the output data list.
def _crawler_result(item, response, spider):
    output_data.append(dict(item))


if __name__== "__main__":
    app.run(debug=True)
