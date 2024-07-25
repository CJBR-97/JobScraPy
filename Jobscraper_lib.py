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


# Use Regex to match the last n words before a target word
def get_last_n_words(text, word, n = 5):
    # Create a regex pattern to match the last five words before the specified word
    pattern = r"(?:\S*\s*){1,4}" + re.escape(word) #r"((?:\S+\s+){0,n})" + re.escape(word)
    # Use the re.findall function to find all matches in the text
    matches = re.search(pattern, text, re.M)
    # If there are no matches, return an empty string
    if not matches:
        return None

    #print("matches", matches)
    # Otherwise, return the last match (which is the closest to the end of the text)
    return matches

# Capture or remove extra material from job description
def parse_extras(text, pattern, filter = False):
    if filter:
        matches = re.sub(pattern, '', text, re.M)
    else:
        matches = re.findall(pattern, text, re.M)
    if not matches:
        return None
    return matches

def desc_parser(filter_func, desc_txt, pattern):
    # Get requirements
    reqs = [filter_func(txt, pattern) for txt in desc_txt]
    reqs = [e for e in reqs if e != None]
    if reqs != []:
        reqs = list(set([r for req in reqs for r in req]))
        reqs.sort()
        return reqs
    else:
        warnings.warn(r"No information found by filtering input for pattern {}".format(pattern))
        return None

# Handle refinement of data according to available keys/tags/search methods
def inner_process(browser, key_list, encoding = "cp1252", decoding = "utf-8"):
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

def pull_text(keyw, desc_txt):
    k = list(filter(lambda text: keyw.lower() in text.lower(), desc_txt))
    # Handle the None case
    if k in [[None], None, [], "[]"]:
        warnings.warn("No information found by filtering input for key {}".format(keyw))
        return None
    # or get the proceeding element in the job description if keyword shows up only once
    elif len(k) == 1 and k[0].lower() in keyw:
        return desc_txt[desc_txt.index(k[0])+1]
    # or save the text element containing the word
    else:
        return k


# Filters content from scraping into appropriate final format
def populate(jobDict, jobBoard, retrieveList):
    populatedDict = {k : [] for k in retrieveList}
    for k in retrieveList:
        populatedDict[k] = jobDict["populate"][k](k, jobBoard, jobDict)
return populatedDict


# Function that uses regex to fish out details from page elements
def r_fisher(webList, regX, encoding = "cp1252", decoding = "utf-8"):
    return[re.search(regX, w.text.encode(encoding,"ignore").decode(decoding,"ignore").replace(u"\u2013", '-').replace(u"\u00E9", 'e'), re.M).group(1) if w is not None else None for w in webList]


# Uses regex fisher to filter each item from a list
def p_fisher(attrib, jobBoard, jobDict):
    return [j for j in r_fisher(jobBoard[jobDict[attrib][0]], jobDict[attrib][1]) if j != '']


# Handles web designs that double-up their entries
def p_doubles(attrib, jobBoard, jobDict):
    return [j.get_attribute(attrib) for j in jobBoard[jobDict[attrib]][::2]]


# Replaces some common problem characters in web text elements
def p_replace(attrib, jobBoard, jobDict):
    return [j.text.encode("cp1252","ignore").decode("utf-8","ignore").replace(u"\u2013", '-').replace(u"\u00E9", 'e') for j in jobBoard[jobDict[attrib]] if j.text != '' and j.text.lower() != attrib]


# Basic extraction of details without many significant post-processing
def p_basic(attrib, jobBoard, jobDict):
    return [j.get_attribute(attrib) for j in jobBoard[jobDict[attrib]]]


class Company_Settings():
    Kinectrics = {
        "company":"Kinectrics",
        "home":"https://careers.kinectrics.com/search/?createNewAlert=false&q=&locationsearch=",
        "title":"jobTitle-link",
        "location":"jobLocation",
        "pg_down": "jobTitle-link",
        "href":"jobTitle-link",
        "paginated": True,
        "pageClass":"pagination",
        "populate": {'href': p_doubles, 'title': p_replace, 'location' : p_replace},
        "inner": None,
        "filter": False,
        "notes": ["No internal HTML/CSS class structure to posting pages, full text extraction & post-processing recommended", "Formatting between postings varies, expect more cleanup work in results from this site"]
    }

    CaNuLabs = {
        "company": "CNL",
        "home": "https://tre.tbe.taleo.net/tre01/ats/careers/v2/searchResults?org=CNLLTD&cws=37",
        "title": "viewJobLink",
        "work_type": "workplaceTypes", 
        "work_commit": "commitment",
        "location": ["oracletaleocwsv2-accordion-head-info", r'^[^\n]+\n([\)\(\.\w \-&]+)'],
        "pg_down": "viewJobLink",
        "href": "viewJobLink",
        "paginated": False,
        "populate": {'href': p_basic, 'title': p_replace, 'location' : p_fisher},
        "inner": {"Description" : "cwsJobDescription", "ID": ["well.oracletaleocwsv2-job-description", r'^[Pp]osition [Nn]umbers?\s+(\d+).*\n'], "Dept" : r'^[Dd]epartments?\:\s*(.*)\n'},
        "filter": False,
        "notes": ["No pagination, only scrolldown loads new listings on this site", "Formatting between postings varies, expect more cleanup work in results from this site"]
    }

    
    Kepler = {
        "company": "Kepler",
        "home": 'https://jobs.lever.co/kepler',
        "title": ["posting-title", r"^(.*)\n"],
        "work_type": "workplaceTypes", 
        "work_commit": "commitment",
        "location": "location",
        "pg_down": "posting-apply",
        "href": "posting-title",
        "paginated": False,
        "populate": {'href': p_basic, 'title': p_fisher, 'location' : p_replace},
        "inner": {"Description" : "", "ID" : "", "Education" : "", "XP" : ""},
        "filter": False
    }

    
    OnPowGen = {
        "company": "OPG",
        "home": "https://jobs.opg.com/search/?q=&sortColumn=referencedate&sortDirection=desc&searchby=location&d=15",
        "title": ["a.jobTitle-link", r"(.*)"],
        "location": "span.jobLocation",
        "pg_down": "span.jobFacility",
        "href": "a.jobTitle-link",
        "paginated": True,
        "pageClass": "pagination",
        "populate": {'href': p_doubles, 'title': p_fisher, 'location' : p_replace},
        "inner": {"Description" : "", "ID" : [By.CSS_SELECTOR, "[data-careersite-propertyid='facility']"], "Education" : "", "XP" : ""},
        "filter": "fine",
        "notes": ["Filtering on 'fine' mode is required", "Location and job href duplication are common with the OPG website through this program, partly due to the site's mobile implementation containing duplicate hrefs, strain 'Location' from location results"]
    }


# Collects page links for websites that use pagination
def page_links(browse, pageLinkClass, title = "title", href = "href", tagName = 'a', notFirstLast = True, verbose = True):
    # Find pagination section
    links = browse.find_element(By.CLASS_NAME, pageLinkClass)
    links = links.find_elements(By.TAG_NAME, tagName)
    if links == []: 
        return [None, None]
    linkTexts = [link.get_attribute(title) for link in links]
    linkLinks = [link.get_attribute(href) for link in links]

    # This option removes page buttons that go directly to the beginning/end of a list, as they can be redundant
    if notFirstLast:
        linkTexts.pop(0)
        linkLinks.pop(0)
        linkTexts.pop(-1)
        linkLinks.pop(-1)
    
    if verbose:
        print("Found pagelinks for {}".format(linkTexts))

    return [linkTexts, linkLinks]


# Opens a new tab and moves to it
def turn_page(browse, link, page):
    print("Accessing page {} with {} browser tabs open already".format(page, len(browse.window_handles)))
    # Check we don't have other windows open already
    assert len(browse.window_handles) == 1
    browse.switch_to.new_window('tab')
    browse.get(link)
    return None


def downer(browse, retrieveClasses = [None], pageLenClass = "title", pageTag = "body", no_of_pagedowns = 100, fine = False):
    
    if fine:
        selSelect = By.CSS_SELECTOR
    else:
        selSelect = By.CLASS_NAME

    pageElem = browse.find_element(By.TAG_NAME, pageTag)
    numPresent = len(browse.find_elements(selSelect, pageLenClass))
    
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
        updateElems = len(browse.find_elements(selSelect, pageLenClass))

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
            returnWebElem[c[0]] = (browse.find_elements(selSelect, c[0]))
        else:
            if fine:
                selSelect = By.CSS_SELECTOR
            else:
                selSelect = By.CLASS_NAME
            returnWebElem[c] = browse.find_elements(selSelect, c)

    return returnWebElem
    

# Adapted from https://stackoverflow.com/questions/46753393/how-to-run-headless-firefox-with-selenium-in-python
# Initialize headless firefox webdriver
def headless_fox():
    fox_options = Options()
    fox_options.add_argument("-headless")
    browser = webdriver.Firefox(options=fox_options)
    print ("Headless Firefox Initialized")
    return browser


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
        job_search = { k : [] for k in retrieveList }
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

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

    finally:
        # This code will run whether an exception was raised or not
        # Don't forget to close the driver
        browser.quit()
    
    return job_search


def extract_single(inner_dict, job_search, wanted_keys, filter_func, filter_pattern, browser = None, solo = True, homepage = None):
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

    except Exception as e:
        print(f"An error occurred: {e}")
        # Don't forget to close the driver
        browser.quit()
        traceback.print_exc()

    print(pg_dict)
    return pg_dict
