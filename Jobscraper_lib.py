import re
import time
import warnings
import datetime
from functools import partial
import traceback
import pandas as pd
from pprint import pprint
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


class jobScraPy:
    def __init__(self):
        """
        A job scraping class, designed to take a single website per instance and process any detected postings into Pandas and/or Excel details for the user.
        Parameters:
        * None
        """

        self.today = datetime.datetime.now()
        self.board = None
        self.helpsites = ["https://regex101.com/", "https://regexone.com/"]
        print("Initialized jobScraPy class instance at {}:{}".format(self.today.hour, self.today.minute))

        ###### Initialize class object variables ######

        # Detect various requirements (future update: to caseless regex search mode)
        self.patterns = {
            "education" : r"(?:[Dd]egree|[Mm]aster'?s?|[Bb]achelor'?s?|PEO|[Ee]ngineer(?:ing)?|[Uu]niversity\s[Ee]ducation|[Cc]ollege|[Dd]iploma|[Hh]igher\seducation|[Ss]econdary\s[Ss]chool|(?:[Pp]ost)?-?[Dd]octor(?:al)?(?:ate)?|[Pp]ost-?[Dd]oc|[Pp]ost-[Ss]econdary|[Mm]\.?[Ss][Cc]|[Bb]\.?[Ss][Cc]|(?:[Pp]ost|[Uu]nder)?-?grad(?:uate)?|[Pp][Hh]\.?[Dd])",
            "experience" : r"(?:.*[Ee]xperience.*|.*(?:[Yy]ear|yr)s?.*role.*|.*role.*(?:[Yy]ear|yr)s?.*)",
            "department" : r"^[Dd]epartments?:?\s*(.*)\s*?\n?",
            "looking for" : r"[Ll]ooking\sfor:?\s*(.*)\s*?\n?$",
            "location" : r"^(?:[Ll]ocations?:?\s*(.*)\s*?\n?)$",
            "type" : r"^(?:[Ee]mployment|[Oo]pportunity|[Jj]ob)\s[Tt]ypes?:?\s*(.*)\n?$",
            "reports to" : r"[Rr]eports to\s?:?\s*(.*)\s*?\n?$"
        }

    
    def custom_company(self):
        """
        A fillable empty dictionary that allows users to customize the processing of a specific website.
        Parameters:
        * None
        Returns:
        * company_dict (dict): A dictionary containing keys with placeholder values that are used by functions in the parent class.
        """
        company_dict = {
            "company": "",
            "home": "",
            "title": ["", r""],
            "location": "",
            "type": "",
            "department": "",
            "pg_down": "",
            "href": "",
            "pagefunc": None,
            "populate": {'href': "", 'title': "", 'location' : ""},
            "inner": {"": [None, "", None]},
            "filter": "",
            "notes": ""
        }
        return company_dict

    
    def set_board(self, board):
        """
        Allows the user to set a provided dictionary as the current board variable of the JobScraPy class instance.
        Parameters:
        * board (dict): The user-provided job board dictionary for an arbitrary website. This should use the same structure and keys as company_dict.
        Returns:
        * None
        """
        self.board = board


    ###### Define filter assist functions ######
    

    # Adapted from source stackoverflow, still looking for original link/post
    # Use Regex to match the last n words before a target word
    def get_last_n_words(self, text, word, n = 5):
        # Create a regex pattern to match the last five words before the specified word
        pattern = r"(?:\S*\s*){1,4}" + re.escape(word) #r"((?:\S+\s+){0,n})" + re.escape(word)
        # Use the re.findall function to find all matches in the text
        matches = re.search(pattern, text, re.M)
        # If there are no matches, return an empty string
        if not matches:
            return None
        # Otherwise, return the last match (which is the closest to the end of the text)
        return matches


    # Capture or remove extra material from job description
    def parse_extras(self, text, pattern, filter = False):
        if filter:
            matches = re.sub(pattern, '', text, re.M)
        else:
            matches = re.findall(pattern, text, re.M)
        if not matches:
            return None
        return matches

    
    # Applies a filter function (such as parse_extras) to clean up text from a job description
    def desc_parser(self, filter_func, desc_txt, pattern):
        # Get requirements
        reqs = [filter_func(txt, pattern) for txt in desc_txt]
        reqs = [e for e in reqs if e != None]
        if reqs != []:
            reqs = list(set([r for req in reqs for r in req]))
            reqs.sort()
            return reqs
        else:
            warnings.warn(r"No information found by parsing description for pattern {}".format(pattern))
            return None

    
    # Handle refinement of specific posting page data according to available keys/tags/search methods
    def inner_process(self, browser, key_list, encoding = "cp1252", decoding = "utf-8"):
        x = browser.find_element(key_list[0], key_list[1])
        x = x.text.encode(encoding,"ignore").decode(decoding,"ignore").replace(u"\u2013", '-').replace(u"\u00E9", 'e').replace(u'\u2022', '-').replace(u'\u201D', '\"').replace(u'\u201C', '\"')
        if x is None:
            raise Exception("No data extracted from browser page.  Please check that indices of key_list are correct for the website")

        if all(key_list):
            # Yank & Regex
            x = re.search(key_list[2], x, re.M)
            print(type(x))
            if x is None:
                raise Exception("No regex pattern matches found in input string")
            else:
                x = x.group(1)
                print(type(x))

        if x.isnumeric():
            return int(x)
        else:
            return str(x)


    def pull_text(self, keyw, desc_txt):
        get_next = 1
        k = list(filter(lambda text: keyw.lower() in text.lower(), desc_txt))
        # Handle the None case
        if k in [[None], None, [], "[]"]:
            warnings.warn("Unable to pull non-None text for key {}".format(keyw))
            return None
        # or get the proceeding element in the job description if keyword shows up only once
        elif len(k) == 1 and k[0].lower() in keyw.lower():
            if len(desc_txt[desc_txt.index(k[0]) + get_next]) <= 2:
                return desc_txt[desc_txt.index(k[0]) + get_next + 1]
            else:
                return desc_txt[desc_txt.index(k[0]) + get_next]
        # or save the text element containing the word
        else:
            return k


    # Function that uses regex to fish out details from page elements
    def r_fisher(self, webList, regX, encoding = "cp1252", decoding = "utf-8"):
        return[re.search(regX, w.text.encode(encoding,"ignore").decode(decoding,"ignore").replace(u"\u2013", '-').replace(u"\u00E9", 'e'), re.M).group(1) if w is not None else None for w in webList]

    
    # Uses regex fisher to filter each item from a list
    def p_fisher(self, attrib, jobBoard):
        return [j for j in self.r_fisher(jobBoard[self.board[attrib][0]], self.board[attrib][1]) if j != '']


    # Handles web designs that double-up their entries
    def p_doubles(self, attrib, jobBoard):
        return [j.get_attribute(attrib) for j in jobBoard[self.board[attrib]][::2]]

    
    # Replaces some common problem characters in web text elements
    def p_replace(self, attrib, jobBoard):
        return [j.text.encode("cp1252","ignore").decode("utf-8","ignore").replace(u"\u2013", '-').replace(u"\u00E9", 'e') for j in jobBoard[self.board[attrib]] if j.text != '' and j.text.lower() != attrib]

    
    # Basic extraction of details without many significant post-processing
    def p_basic(self, attrib, jobBoard):
        return [j.get_attribute(attrib) for j in jobBoard[self.board[attrib]]]

    
    # Filters content from scraping into appropriate final format
    def populate(self, jobBoard, retrieveList):
        populatedDict = {k : [] for k in retrieveList}
        for k in retrieveList:
            populatedDict[k] = self.board["populate"][k](k, jobBoard)
        return populatedDict


    # Collects page links for websites that use pagination
    def page_links(self, browser, pageLinkClass, title = "title", href = "href", tagName = 'a', notFirstLast = 'both', verbose = True):
        # Find pagination section
        links = browser.find_element(By.CLASS_NAME, pageLinkClass)
        links = links.find_elements(By.TAG_NAME, tagName)
        
        if links == []: 
            self.pgTxt = None
            self.pgLnk = None
            return None
        
        linkTexts = [link.get_attribute(title) for link in links]
        # Failsafe for pages without title attributes
        if all(linkTexts) == False:
            linkTexts = [link.text.encode("cp1252","ignore").decode("utf-8","ignore") for link in links]

        linkLinks = [link.get_attribute(href) for link in links]

        if notFirstLast:
            indices = [i for i, t in enumerate(linkTexts) if t != ""]
            if notFirstLast.lower() in ["first", "both"]:
                indices.pop(0)
            if notFirstLast.lower() in ["last", "both"]:
                indices.pop(-1)

            linkTexts = [linkTexts[i] for i in indices]
            linkLinks = [linkLinks[i] for i in indices]

        if verbose:
            print("Found pagelinks for {}".format(linkTexts))

        self.pgTxt = linkTexts
        self.pgLnk = linkLinks
        return None

    # Opens a new tab and moves to it
    def turn_page(self, browser, link, page):
        print("Accessing page {} with {} browser tabs open already".format(page, len(browser.window_handles)))
        # Check we don't have other windows open already
        assert len(browser.window_handles) == 1
        browser.switch_to.new_window('tab')
        browser.get(link)
        return None






"""
# Acknowledgement to https://stackoverflow.com/questions/21006940/how-to-load-all-entries-in-an-infinite-scroll-at-once-to-parse-the-html-in-python for page down loading code
def downer(browser, retrieveClasses = [None], pageLenClass = "title", pageTag = "body", no_of_pagedowns = 100, fine = False):  
    if fine:
        selSelect = By.CSS_SELECTOR
    else:
        selSelect = By.CLASS_NAME
    pageElem = browser.find_element(By.TAG_NAME, pageTag)
    numPresent = len(browser.find_elements(selSelect, pageLenClass))

    print("Current len is {}".format(numPresent))
    pageElem.send_keys(Keys.PAGE_DOWN)
    time.sleep(0.5)
    no_of_pagedowns-=1

    while no_of_pagedowns:
        pageElem.send_keys(Keys.PAGE_DOWN)
        time.sleep(1)
        no_of_pagedowns-=1

        if fine:
            selSelect = By.CSS_SELECTOR
        else:
            selSelect = By.CLASS_NAME
        updateElems = len(browser.find_elements(selSelect, pageLenClass))

        if no_of_pagedowns%10 == 0:
            if updateElems > numPresent:
                print("Current len is {} with increase of {}".format(updateElems, updateElems - numPresent))
                numPresent = updateElems
            elif updateElems == numPresent:
                print("Current len is {} with increase of {}".format(updateElems, updateElems - numPresent))
                no_of_pagedowns = 0

    print("Final len is {}".format(updateElems))
    returnWebElem = {}
    for c in retrieveClasses:
        if type(c) is list: 
            if fine:
                selSelect = By.CSS_SELECTOR
            else:
                selSelect = By.CLASS_NAME
            returnWebElem[c[0]] = (browser.find_elements(selSelect, c[0]))

        else:
            if fine:
                selSelect = By.CSS_SELECTOR
            else:
                selSelect = By.CLASS_NAME
            returnWebElem[c] = browser.find_elements(selSelect, c)

    return returnWebElem    

# Adapted from https://stackoverflow.com/questions/46753393/how-to-run-headless-firefox-with-selenium-in-python
# Initialize headless firefox webdriver
def headless_fox():
    fox_options = Options()
    fox_options.add_argument("-headless")
    browser = webdriver.Firefox(options=fox_options)
    print ("Headless Firefox Initialized")
    return browser


# The full scraping process all in one
# TODO turn it into a class and fold the rest inside it
def JobScraPy(jobDict, retrieveList):
    # Start browsing
    browser = headless_fox()

    try:
        browser.get(jobDict["home"])
        time.sleep(1)
        # Store the ID of the original window
        original_window = browser.current_window_handle
        job_search = {k : [] for k in retrieveList}
        classList = [jobDict[k] for k in retrieveList]

        nopages = False
        if jobDict["paginated"]:
            if page_links(browser, jobDict["pageClass"]) == [None, None]:
                nopages = True
                print("No pages found other than starting page")

        if jobDict["paginated"] and nopages == False:
            pgTxt, pgLnk = page_links(browser, jobDict["pageClass"])
            for (lnk, pg) in zip(pgLnk, pgTxt):
                try:
                    turn_page(browser, lnk, pg)
                    jobBoard = downer(browser, retrieveClasses = classList, pageLenClass = jobDict["pg_down"], pageTag = "body", fine = jobDict["filter"])
                    populatedOutput = populate(jobDict, jobBoard, retrieveList)
                    for (k, key) in zip(retrieveList, populatedOutput):
                        job_search[k].extend(populatedOutput[key])

                except Exception as e:
                    print("Skipping page {}".format(pg))
                    print(f"An error occurred: {e}")
                    traceback.print_exc()

                finally:
                    browser.close()
                    # Switch back to the old tab or window
                    browser.switch_to.window(original_window)
                    print("Done scraping main board")
        else:
            try:
                jobBoard = downer(browser, retrieveClasses = classList, pageLenClass = jobDict["pg_down"], pageTag = "body", fine = jobDict["filter"])
                populatedOutput = populate(jobDict, jobBoard, retrieveList)
                for (k, key) in zip(retrieveList, populatedOutput):
                    job_search[k].extend(populatedOutput[key])
            except Exception as e:
                print(f"An error occurred: {e}")
                traceback.print_exc()
            finally:
                print("Done scraping main board")

        print(job_search)
        #print([len(job_search[k]) for k in job_search])

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

    finally:
        # This code will run whether an exception was raised or not
        # Don't forget to close the driver
        browser.quit()
    
    return job_search


def extract_single(inner_dict, wanted_keys, filter_func, filter_pattern, browser = None, solo = True, homepage = None):
    if solo:
        # Start browsing
        browser = headless_fox()

    try:
        browser.get(homepage)
        time.sleep(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

    try:
        pg_dict = {} #{k : [] for k in wanted_keys}
        # Parse the HTML using BeautifulSoup
        source = browser.page_source
        soup = BeautifulSoup(source, 'html.parser')
        # Find all text elements within the HTML
        text_elements = soup.find_all(['p', 'ul', 'ol', 'li'])
        # Extract the touched-up text data from the webpage
        desc_txt = [text.get_text().replace(u"\u00A0", ' ').replace(u"\u00E9", 'e').replace(u"\u2013", '-').encode("cp1252","ignore").decode("utf-8","ignore") for text in text_elements]
        # Filter out any keywords or stuff that we don't want in the full description
        if filter_func:
            desc_txt = [parse_extras(text, filter_pattern, filter = True) for text in desc_txt]
        desc_txt = [r" ".join(text.splitlines()) for text in desc_txt if text != None]        
        job_desc = r" ".join(desc_txt)

        for k in wanted_keys:
            try:
                # If we have a shortcut to finding a desired term or item, take it
                if k in inner_dict:
                    pg_dict[k] = inner_process(browser, inner_dict[k])
                else:
                    # First special case is the description, so we simply take it all here
                    if k.lower() == "description":
                        pg_dict["Description"] = desc_txt
                    # Dept. info is often buried or obscured and so should be handled separately
                    elif k.lower() in ["department", "dept", "dept."]:
                        y = get_last_n_words(job_desc, "[Dd]epartment")
                        if y != None:
                            pg_dict["department"] = y.group(0)
                        else:
                            pg_dict["department"] = desc_parser(parse_extras, desc_txt, patterns[k])                                      
                    # Similar to below, but entire text elements are pulled
                    elif wanted_keys[k] == True:
                        pg_dict[k] = pull_text(k, desc_txt)
                    else:
                        # Sequentially parse description for user-specified data such as degrees, software proficiencies, ect.
                        pg_dict[k] = desc_parser(parse_extras, desc_txt, patterns[k])
            except:
                warnings.warn("No information found by filtering input for key {}".format(k))
                pg_dict[k] = None

        # Don't forget to close the driver
        if solo:
            browser.quit()
        else:
            browser.close()

    except Exception as e:
        print(f"An error occurred: {e}")
        # Don't forget to close the driver on the way out
        browser.quit()
        traceback.print_exc()

    print(pg_dict)
    return pg_dict
"""
