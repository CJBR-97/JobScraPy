import re
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

# Some acknowledgements:
# The first example of using Selenium to extract hrefs from a webpage was 13 lines (including comments) of code obtained via the Bing-Copilot AI interface
# Thanks to https://www.digitalocean.com/community/tutorials/python-string-encode-decode for information on encoding-decoding web scaped data
# Ditto for https://realpython.com/python-encodings-guide/
# Thanks to https://www.selenium.dev/documentation/webdriver/interactions/windows/ for a better understanding of webdriver window operations
# And as always, thanks to RegexOne for their excellent tutorials

# Fish text out of webelement objects using regX and customizable encoding
def text_fisher(webList, regX, encoding = "cp1252", decoding = "utf-8"):
    return [re.search(regX, w.text.encode(encoding,"ignore").decode(decoding,"ignore").replace(u"\u2013", '-'), re.M).group(1) if w != None else None for w in webList]

# Page-down on webpages that display postings in a piece-by-piece loading format without pagination
def downer(browse, retrieveClasses = [None], pageLenClass = "title", pageTag = "body", no_of_pagedowns = 100, ):

    # Access page and check how many postings are initially present
    pageElem = browse.find_element(By.TAG_NAME, pageTag)
    numPresent = len(browse.find_elements(By.CLASS_NAME, pageLenClass))
    print("Current len is {}".format(numPresent))
    pageElem.send_keys(Keys.PAGE_DOWN)
    # Give the page time to load, any less than .2 s of sleep may produce erratic results due to incomplete loading
    time.sleep(0.5)
    no_of_pagedowns-=1

    # Loop page-down command until no more postings are found
    while no_of_pagedowns:
        pageElem.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.5)
        no_of_pagedowns-=1
        # Check number of postings on the side after the page-down
        updateElems = browse.find_elements(By.CLASS_NAME, pageLenClass)
        # Update number of postings detected every few page-downs
        # And kill the loop if the number has stopped increasing
        if no_of_pagedowns%10 == 0:
            if len(updateElems) > numPresent:
                print("Current len is {} with increase of {}".format(len(updateElems), len(updateElems) - numPresent))
                numPresent = len(updateElems)
            elif len(updateElems) == numPresent:
                print("Current len is {} with increase of {}".format(len(updateElems), len(updateElems) - numPresent))
                no_of_pagedowns = 0

    print("Final len is {}".format(len(updateElems)))

    # Give back the webelements initially specified by the user
    returnWebElem = {}
    for c in retrieveClasses:
        returnWebElem[c] = (browse.find_elements(By.CLASS_NAME, c))
    return returnWebElem

# Adapted from https://stackoverflow.com/questions/46753393/how-to-run-headless-firefox-with-selenium-in-python
# Initialize headless firefox webdriver
def headless_fox():
    fox_options = Options()
    fox_options.add_argument("-headless")
    browser = webdriver.Firefox(options=fox_options)
    print ("Headless Firefox Initialized")
    return browser

# Use Regex to match the last n words before a target word
def get_last_n_words(text, word, n = 5):
    pattern = r"(?:\S*\s*){1,4}" + re.escape(word)
    matches = re.search(pattern, text, re.M)
    if not matches:
        print("No matches found")
        return None
    return matches

# Detect common education requirements using Regex
def edu_prereqs(text):
    pattern = r"(?:[Dd]egree|[Mm]aster'?s?|[Bb]achelor'?s?|[Ss]econdary [Ss]chool|(?:[Pp]ost)?-?[Dd]octor(?:al)?(?:ate)?|[Pp]ost-?[Dd]oc|[Pp]ost-[Ss]econdary|[Mm]\.?[Ss][Cc]|[Bb]\.?[Ss][Cc]|(?:[Pp]ost|[Uu]nder)?-?grad(?:uate)?|[Pp][Hh]\.?[Dd])"
    matches = re.findall(pattern, text, re.M)
    if not matches:
        return None
    return matches

# Remove extraneous material from job description
# Note: Can nuke large sections of text, so be sure to check if any important data has been removed before proceeding
def filter_extras(sift_words):
    pattern = r".*?(?:" + "|".join(sift_words) + r").*?\."
    matches = re.sub(pattern, '', text, flags = re.M | re.I)
    if not matches:
        return None
    return matches
