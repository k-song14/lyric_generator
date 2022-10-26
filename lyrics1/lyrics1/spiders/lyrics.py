import scrapy
from scrapy.linkextractors import LinkExtractor
from bs4 import BeautifulSoup
import requests
import re
from scrapy.crawler import CrawlerProcess

class LyricSpider(scrapy.Spider):
    name='lyrics_spider'

    start_urls = []

    def __init__(self, form_inp='', **kwargs): # The category variable will have the input URL.
        form_inp = re.sub(', ', ',', form_inp)
        artists = form_inp.split(',')

        for artist in artists:
            artist = re.sub(' ', '-', artist).capitalize()
            self.start_urls.append('https://genius.com/artists/' + artist + '/')
        print(self.start_urls)
        super().__init__(**kwargs)

    def parse(self,response):
        '''parse method; begins at our initial page 
        goes to our desired next page (artist's albums)
        '''
        #creating our soup object
        page = requests.get(response.url)
        soup = BeautifulSoup(page.content, "html.parser")
        #gets links to all albums on the artist's page
        next_page = [i['href'] for i in soup.find_all("a", href=lambda href: href and "https://genius.com/albums/" in href)]

        #yields request for each url in list
        for link in next_page:
            yield scrapy.Request(link, callback=self.parse_songs)

    def parse_songs(self, response):
        '''generates and visits sites of all songs in the album
        '''

        #create soup object
        album_page = requests.get(response.url)
        soup2 = BeautifulSoup(album_page.content, "html.parser")
        #gets all links for songs on the page 
        songs = [i['href'] for i in soup2.find_all("a", href=lambda href: href and "https://genius.com/" and "lyrics" in href)]
        #gets artist name as list
        artist = response.css("a.header_with_cover_art-primary_info-primary_artist::text").get()
        
        #get name inside list
        name = artist[0:]
        #convert to lowercase
        name = name.lower()
        #capitalize only first letter
        name = name[0:].capitalize()
        #replace spaces with hyphen
        name= re.sub(" ", "-", name)

        #yields request for each url in list if it's a song by our desired artist(s)
        for new_link in songs:
            if name not in new_link:
                songs.remove(new_link)
            else:
                yield scrapy.Request(new_link, callback=self.parse_song_page)

    def parse_song_page(self, response):
        '''creates dictionary with lyrics in each song and corresponding song name
        '''
        #extracts song name from header
        song_name = response.css('span.SongHeaderVariantdesktop__HiddenMask-sc-12tszai-10.bFjDxc::text').get()
        #extracts lyrics from page
        song_lyrics = response.css('span.ReferentFragmentVariantdesktop__Highlight-sc-1837hky-1.jShaMP::text').getall() 

        yield{

        "song": song_name,
        "lyrics": song_lyrics

        }
