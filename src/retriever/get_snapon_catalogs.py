"""Retrieve SnapOn catalogs automagically.

Determines start and stop IDs to retrieve data for and then gets the images
from each page.
"""

# Standard Python Libraries
import logging

# Python library imports
import os
from pprint import pformat
import sys

# Third-Party Libraries
# Third party library imports
import requests

DEFAULT_OUTPUT_PATH = "~/snapon"
SLEEP_TIME = 0.1

YEAR = "1958"
LETTER = "W"
BASE_CATALOG = "http://www.collectingsnapon.com/catalogs/catalogs-large/{0}_Industrial_Catalog_{1}/{0}-Industrial-Catalog-{1}-"  # noqa
BASE_PAGE = "p{:02d}.jpg"
BASE_URL = BASE_CATALOG.format(YEAR, LETTER) + BASE_PAGE
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"  # noqa
}


def get_page(pageid, baseurl=BASE_URL, dest=DEFAULT_OUTPUT_PATH) -> int:
    """Get a specified page and write its contents to the destination.

    [description]

    Arguments:
        pageid {[type]} -- [description]

    Keyword Arguments:
        baseurl {[type]} -- [description] (default: {BASE_URL})
        dest {[type]} -- [description] (default: {DEFAULT_OUTPUT_PATH})

    Returns:
        [type] -- [description]
    """
    # Initialize variables for scope
    url = baseurl.format(pageid)

    # Get image name
    filename = url.split("/")[-1]
    destfile = os.path.join(dest, filename)

    logging.info("Retrieving '%s'", filename)
    # Retrieve the image
    r = requests.get(url, headers=HEADERS)

    if not r.ok:
        logging.info("Not OK: %i", r.status_code)
        return r.status_code

    logging.debug("Saving filename: '%s'", filename)
    with open(destfile, "wb") as f:
        f.write(r.content)

    return 1


def main(start, stop, outputpath, base_url, log_level=logging.DEBUG) -> int:
    """Set up logging and call the subsequent functions."""
    # Set up logging
    logging.basicConfig(
        format="%(asctime)-15s %(levelname)s %(message)s", level=log_level.upper()
    )

    # Make sure output dirs exist
    outputpath = os.path.abspath(os.path.expanduser(outputpath))
    if not os.path.exists(outputpath):
        logging.debug("Creating output path: %s", outputpath)
        os.makedirs(outputpath)

    logging.info("Base URL: %s", base_url)

    bad_ids = {}

    logging.info("Loading IDs from %i to %i", start, stop - 1)
    for idnum in range(start, stop):
        retcode = get_page(idnum, baseurl=base_url, dest=outputpath)

        if retcode is not None:
            bad_ids[idnum] = retcode

        # if idnum < stop - 1:
        #     time.sleep(SLEEP_TIME)

    logging.info("Downloads complete!")
    logging.info("Downloads saved in %s", outputpath)

    if len(bad_ids) > 0:
        logging.warning("IDs and failure codes:\n%s", pformat(bad_ids))

    # Stop logging and clean up
    logging.shutdown()
    return 0


if __name__ == "__main__":
    # Standard Python Libraries
    import argparse

    parser = argparse.ArgumentParser(
        description="Downloads a series of images or files by ID and base url"
    )

    parser.add_argument(type=int, dest="startid", help="ID number to start at")

    parser.add_argument(
        type=int, dest="stopid", help="ID number to stop at (inclusive)"
    )

    parser.add_argument(
        "-year",
        default=YEAR,
        type=str,
        dest="year",
        help="Catalog year, e.g. {}".format(YEAR),
    )

    parser.add_argument(
        "-letter",
        default=LETTER,
        type=str,
        dest="letter",
        help="Catalog letter, e.g. {}".format(LETTER),
    )

    parser.add_argument(
        "-path",
        "--output-path",
        default=DEFAULT_OUTPUT_PATH,
        type=str,
        dest="outputpath",
        help="Output path (Default: current directory)",
    )

    args = parser.parse_args()

    sys.exit(
        main(
            args.startid,
            args.stopid + 1,
            args.outputpath,
            BASE_CATALOG.format(args.year, args.letter) + BASE_PAGE,
        )
    )
