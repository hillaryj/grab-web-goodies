"""Retrieve GMPartsWiki images automagically.

Downloads images or files from a partswiki into folders for each manual.
"""

# Standard Python Libraries
import logging

# Python library imports
import os
from pprint import pformat
import sys
import time
from typing import Dict

# Third-Party Libraries
from bs4 import BeautifulSoup

# Third-party imports
import requests

# Global variables
DEFAULT_OUTPUT_PATH = "~/manuals"
PARTSWIKI_BASE_URL = "http://gmpartswiki.com"
BROWSE_PAGE = "/browse"
BIG_PAGE_QUERY = "/getbigpage?pageid={}"
PARTSWIKI_DEFAULT_QUERY = PARTSWIKI_BASE_URL + BIG_PAGE_QUERY

# Keywords for parsing manuals' listings
INDEX_KEY = "/bookindex"
TITLE_KEY = "/getpage"

# User agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"  # noqa
}
SLEEP_TIME = 0.1

# Debug settings
LOG_LEVEL = logging.INFO
SAVE_DEBUG_FILES = False
USE_CACHED_FILES = False
DEBUG_SOUP_FILE = "testoutput_soup.txt"
DEBUG_MANUALS_FILE = "testoutput_manuals.txt"


def save_file(filename, content, writemode="w"):
    """Save specified string contents to a file with the specified filename.

    [description]

    Arguments:
        filename {[type]} -- [description]
        content {[type]} -- [description]

    Keyword Arguments:
        writemode {str} -- Changes the write mode on output (default: {"w"})

    Returns:
        bool -- [description]
    """
    with open(filename, writemode) as f:
        f.write(content)

    return True


def load_page(source, use_local_cache=False):
    """Load a page from file or URL.

    [description]

    Arguments:
        source {[str]} -- Location to load from

    Keyword Arguments:
        use_local_cache {bool} -- If true, loads from a locally-cached
            saved copy. If false, loads from a URL. (default: {False})

    Returns:
        [type] -- [description]
    """
    if use_local_cache:
        return load_page_from_file(source)

    return load_page_from_URL(source)


def load_page_from_file(filename):
    """Load a local cached soup from file and returns BeautifulSoup object.

    [description]

    Arguments:
        filename {[type]} -- [description]

    Returns:
        [type] -- [description]

    Raises:
        IOError -- [description]
    """
    filename = os.path.abspath(os.path.expanduser(filename))
    logging.info("Retrieving cached soup from '%s'", filename)

    if not os.path.exists(filename):
        raise IOError("File does not exist: '{}'".format(filename))

    with open(filename) as fp:
        soup = BeautifulSoup(fp, "html.parser")

    check = soup.title.get_text().strip()
    logging.info("Loaded soup with title '%s'", check)

    return soup


def load_page_from_URL(url):
    """Load a page from URL into a BeautifulSoup object.

    Returns a BeautifulSoup object if page url request is successful.

    Arguments:
        url {string} -- URL of page to load

    Returns:
        BeautifulSoup -- page content, parsed for HTML

    """
    logging.info("Retrieving '{}'".format(url))
    r = requests.get(url, headers=HEADERS)

    if not r.ok:
        logging.warning("Browse page not OK, returned code: %s", r.status_code)
        return None

    return BeautifulSoup(r.content, "html.parser")


def extract_manual_list(soup):
    """Extract information from a BeautifulSoup page object.

    Take a BeautifulSoup page object and extracts information from
    table of manuals.

    Arguments:
        soup {[type]} -- [description]

    Returns:
        [type] -- [description]

    Raises:
        ValueError -- [description]
    """
    manuals = {}

    # Find all <table> attributes - the manuals are individual <tr>
    for row in soup.find_all("tr"):

        manual = {}

        # Get title, book id, and start page id from links
        for link in row.find_all("a"):
            link_text = link.text.strip()
            link_href = link.get("href")

            logging.debug("Found link: '%s': '%s'", link_text, link_href)

            if link_href.startswith(INDEX_KEY):
                manual["bookid"] = int(link_href.split("=")[-1])
            elif link_href.startswith(TITLE_KEY):
                manual["title"] = link_text
                try:
                    manual["startid"] = int(link_href.split("=")[-1])
                except ValueError:
                    # This record is malformed so don't record it
                    logging.warning("'%s': No page id specified", link_text)
                    manual["startid"] = -1

        # Get Type, Effective Date, Publisher, Covers, and # Pages from text
        # logging.debug('Row text: {}'.format(repr(row.get_text())))
        info = list(row.find_all("td")[1].stripped_strings)
        logging.debug("Second cell: %s", info)

        # Extract label positions
        index_effective_date = info.index(u"Effective:") + 1
        index_publisher = info.index(u"Published By:") + 1
        index_covers = info.index(u"Covers:") + 1
        index_page_total = info.index(u"Pages:") + 1
        index_max = len(info)

        # Extract data from label positions
        # Entries can be blank, in which case the next label directly
        # follows the previous label, so check the following label index

        # Effective date (Month YYYY)
        if index_effective_date > 0:
            if index_publisher - index_effective_date > 1:
                logging.debug(
                    "Effective date [%s]: %s",
                    index_effective_date,
                    info[index_effective_date],
                )
                manual["date"] = info[index_effective_date]
            else:
                logging.debug("Effective date [%s]: N/A", index_effective_date)
                manual["date"] = ""
        else:
            logging.warning("Effective date label NOT FOUND in '%s'", manual["title"])

        # Publisher
        if index_publisher > 0:
            if index_covers - index_publisher > 1:
                logging.debug(
                    "Publisher [%s]: %s", index_publisher, info[index_publisher]
                )
                manual["publisher"] = info[index_publisher]
            else:
                logging.debug("Publisher [%s]: N/A", index_covers)
                manual["publisher"] = ""
        else:
            logging.warning("Publisher label NOT FOUND in '%s'", manual["title"])

        # What models the document covers, if specified
        if index_covers > 0:
            if index_page_total - index_covers > 1:
                logging.debug(
                    "Models covered [%s]: %s", index_covers, info[index_covers]
                )

                # Check for duplicate dates and insert dashes for date ranges
                manual["covers"] = fix_covered_model_text(info[index_covers])
            else:
                logging.debug("Models covered [%s]: N/A", index_covers)
                manual["covers"] = ""
        else:
            logging.warning("Covered models label NOT FOUND in '%s'", manual["title"])

        # Total number of pages in the manual
        if index_page_total > 0:
            if index_max - index_page_total > 0:
                logging.debug(
                    "Total pages [%s]: %s", index_page_total, info[index_page_total]
                )

                manual["pages"] = int(info[index_page_total])
            else:
                logging.debug("Total pages [%s]: N/A", index_covers)
                manual["pages"] = 0
        else:
            logging.warning("Page total label NOT FOUND in '%s'", manual["title"])

        # Determine the output folder name for the manual
        manual["dest"] = generate_folder_name(manual)

        # Add this record, but throw an error if there's already one there
        logging.debug("Parsed record:\n%s", manual)
        idnum = manual["bookid"]
        if idnum in manuals:
            raise ValueError(
                "Duplicate id found for titles:\n'{}'\n'{}'".format(
                    manuals[idnum]["title"], manual["title"]
                )
            )
        manuals[idnum] = manual

    return manuals


def fix_covered_model_text(raw) -> str:
    """Apply fixes to the text for what models a manual covers.

    What models the manual covers is sometimes listed as, e.g.
    "1993 1993 Chevrolet Camaro" -> "1993 Chevrolet Camaro".
    Similarly, dashes should be inserted for date ranges, e.g.
    "1982 1992 Chevrolet Camaro" -> "1982-1992 Chevrolet Camaro"

    Collapse repetitive manufacturer labels like
    "Chevrolet Chevelle, Chevrolet Camaro, Chevrolet Corvair"
    into
    "Chevrolet Chevelle, Camaro, Corvair"
    """
    # Fix date range text
    begin = raw[:4]
    end = raw[5:9]
    rawtext = raw[10:]

    if begin == end:
        date = begin
    else:
        date = "{}-{}".format(begin, end)

    # Collapse repetitive manufacturer labels
    makes: Dict[str, list] = {}
    makes = {}
    models = rawtext.split(", ")

    for model in models:
        idx = model.find(" ")
        if idx > 0:
            mfr = model[:idx]
            idx_next = idx + 1
            make = model[idx_next:]

            if mfr in makes:
                makes[mfr].append(make)
            else:
                makes[mfr] = [make]

    # Create string list
    text = ", ".join(["{} {}".format(mfr, ", ".join(makes[mfr])) for mfr in makes])

    return "{} {}".format(date, text)


def generate_folder_name(entry):
    """Generate a folder name from the manual information.

    Manual dict contains:
    # {'bookid': 1,
    #  'covers': u'1960 Chevrolet Corvair',
    #  'date': u'April 1960',
    #  'pages': 160,
    #  'publisher': u'Chevrolet Motor Division',
    #  'startid': 1,
    #  'title': u'Parts and Accessories Catalog P&A 34'}

    # Covers + Title + Effective:
    1960 Chevrolet Corvair - Parts and Accessories Catalog P&A 34 - April 1960
    # Pub + Title + Effective
    Chevrolet Motor Division - Master Parts List Six Cylinder Models - August 1941
    """
    if entry["covers"]:
        folder = " - ".join([entry["covers"], entry["title"], entry["date"]])
    else:
        folder = " - ".join([entry["publisher"], entry["title"], entry["date"]])

    logging.debug("Output folder name: '%s'", folder)

    return folder


def get_manual(entry, url=PARTSWIKI_DEFAULT_QUERY, dest=DEFAULT_OUTPUT_PATH):
    """Retrieve a specified manual entry.

    Input entry is a dictionary describing a manual, e.g.:
    {'bookid': 1,
     'covers': '1960 Chevrolet Corvair',
     'date': u'April 1960',
     'dest': u'1960 Chevrolet Corvair - Parts and Accessories Catalog P&A 34 - April 1960',
     'pages': 160,
     'publisher': u'Chevrolet Motor Division',
     'startid': 1,
     'title': u'Parts and Accessories Catalog P&A 34'}

    This function determines the number of files and gets each page image into
    the specified output directory inside the specified 'dest' parent directory
    Returns a list of any IDs that fail.
    """
    bad_ids = []

    logging.info("Downloading manual (%s): '%s'", entry["bookid"], entry["title"])

    start = entry["startid"]
    total = entry["pages"]

    dest = os.path.join(dest, entry["dest"])
    if not os.path.exists(dest):
        os.mkdir(dest)
        logging.info("Created output directory '%s'", dest)
        # May want to ask to overwrite images if a directory already exists?

    logging.info("Loading %i IDs starting from %i", total, start)
    kk = total
    idnum = start

    while kk > 0:
        retcode = get_page_img(idnum, url, dest)

        if retcode is not None:
            bad_ids.append(idnum)
        else:
            kk -= 1

        idnum += 1
        time.sleep(SLEEP_TIME)

    logging.info("Manual download complete!")

    return total - kk, bad_ids


def get_page_img(pageid, baseurl=PARTSWIKI_DEFAULT_QUERY, dest=DEFAULT_OUTPUT_PATH):
    """Retrieve an image from the specified page.

    [description]

    Arguments:
        pageid {[type]} -- [description]

    Keyword Arguments:
        baseurl {[type]} -- [description] (default: {PARTSWIKI_DEFAULT_QUERY})
        dest {[type]} -- [description] (default: {DEFAULT_OUTPUT_PATH})

    Returns:
        [type] -- [description]
    """
    # Load the page
    pageurl = baseurl.format(pageid)
    logging.debug("..Getting page: %s", pageurl)
    r = requests.get(pageurl, headers=HEADERS)

    if r.status_code == requests.codes["ok"]:
        # Get image name
        logging.debug(
            "Determining attachment name from %s", r.headers["content-disposition"]
        )
        filename = r.headers["content-disposition"].replace("attachment; filename=", "")
        logging.debug("Filename: '%s'", filename)

        # Save image
        destfile = os.path.join(dest, filename)
        logging.debug("ID %s: Writing to '%s'", pageid, filename)
        with open(destfile, "wb") as f:
            f.write(r.content)

    else:
        logging.warning(
            "ID %s: status not ok - code %s at %s", pageid, r.status_code, pageurl
        )
        return r.status_code


def main(baseurl, outputpath, startwithbookid, log_level=logging.DEBUG) -> int:
    """Set up logging and call the subsequent functions."""
    # Set up logging
    logging.basicConfig(
        format="%(asctime)-15s %(levelname)s %(message)s", level=log_level.upper()
    )

    # Make sure output path exists
    outputpath = os.path.abspath(os.path.expanduser(outputpath))
    if not os.path.exists(outputpath):
        logging.debug("Creating output path: %s", outputpath)
        os.makedirs(outputpath)

    # Create URLs
    soup_source = baseurl + BROWSE_PAGE
    big_img_query = baseurl + BIG_PAGE_QUERY

    logging.debug("Browse-page URL: %s", soup_source)
    logging.debug("Large-image query string: %s", big_img_query)

    # Load browse page and scan to extract manuals
    cached = USE_CACHED_FILES
    if cached:
        filename = os.path.join(outputpath, DEBUG_SOUP_FILE)
        if not os.path.exists(filename):
            logging.error(
                "Specified soup cache '%s' DOES NOT EXIST! Reverting to load from URL.",  # noqa
                filename,
            )
            cached = False
        else:
            soup_source = filename

    soup = load_page(soup_source, use_local_cache=cached)

    if not soup:
        logging.error("Load error on '%s'", soup_source)
        return 1

    # Save soup for testing (if not loading from cached soup)
    if not cached and SAVE_DEBUG_FILES:
        testoutput = os.path.join(outputpath, "testoutput_soup.txt")
        logging.debug("Saving browse page contents to %s", testoutput)
        save_file(testoutput, soup.prettify())

    # Extract information on available manuals
    manuals = extract_manual_list(soup)

    logging.info("Extracted listings for %i manuals", len(manuals))

    # Save extracted manuals' info for testing
    if SAVE_DEBUG_FILES:
        testoutput = os.path.join(outputpath, "testoutput_manuals.txt")
        logging.debug("Saving manual contents to %s", testoutput)

        save_file(testoutput, pformat(manuals))

    # Download each manual
    bad_ids = {}
    for book_id in manuals:
        # Skip indicated book ids
        if book_id < startwithbookid:
            continue

        num_success, failures = get_manual(manuals[book_id], big_img_query, outputpath)
        bad_ids[manuals[book_id]["bookid"]] = failures

    logging.info("%i Downloads complete! Saved in %s", num_success, outputpath)

    if len(bad_ids) > 0:
        logging.warning("Failed to download IDs:\n%s", bad_ids)

    logging.info("Processing complete! Exiting...")

    # Stop logging and clean up
    logging.shutdown()
    return 0


if __name__ == "__main__":
    # Standard Python Libraries
    import argparse

    parser = argparse.ArgumentParser(
        description="Downloads images or files from a partswiki by manual"
    )

    parser.add_argument(
        "-u",
        "--url",
        default=PARTSWIKI_BASE_URL,
        type=str,
        dest="baseurl",
        help="Site URL " + '(Default: "{}")'.format(PARTSWIKI_BASE_URL),
    )

    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        type=str,
        dest="outputpath",
        help='Output path (Default: "{}"")'.format(DEFAULT_OUTPUT_PATH),
    )

    parser.add_argument(
        "-s",
        "--start-with",
        type=int,
        dest="startwithbookid",
        help="Indicate a bookid to start with",
    )

    args = parser.parse_args()

    sys.exit(main(args.baseurl, args.outputpath, args.startwithbookid))
