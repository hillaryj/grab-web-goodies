import json
import logging
import os
from pprint import pprint
import requests
import sys

BASE_URL = "https://www.hikewnc.info/maps/data/{}/{}.kml"
DEFAULT_OUTPUT_PATH = "C:\\Users\\alexr\\Desktop\\GPS\\hikewnc\\{}\\{}.kml"
PRETTY_FORMAT_NAME = "{}_fmt"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"  # noqa
}

# Trail names: #<trail_num> <trail_name> - (<trail distance>mi)
# Verify before using
# trail_distance is up to two decimal places


def get_kml(id, file_name, track_type="trails", base_url=BASE_URL, dest=DEFAULT_OUTPUT_PATH) -> int:
    """Get a specified kml URL and write its contents to the destination.

    [description]

    Arguments:
        id {[type]} -- [description]

    Keyword Arguments:
        base_url {[type]} -- [description] (default: {BASE_URL})
        dest {[type]} -- [description] (default: {DEFAULT_OUTPUT_PATH})

    Returns:
        [type] -- [description]
    """
    # Initialize variables for scope
    url = base_url.format(track_type, id)

    logging.info("Retrieving '%s'", url)
    # Retrieve the image
    r = requests.get(url, headers=HEADERS)

    if not r.ok:
        logging.warn("Not OK: %i", r.status_code)
        return r.status_code

    # Make sure output path exists or make it
    dest_path = dest.format(track_type, file_name) 
    if not os.path.exists(os.path.dirname(dest_path)):
        os.makedirs(os.path.dirname(dest_path))

    logging.debug("Saving file: '%s'", file_name)
    with open(dest_path, "wb") as f:
        f.write(r.content)

    return 1

def main(source_path, track_type="trails", log_level=logging.DEBUG):
    # Set up logging
    logging.basicConfig(
        format="%(asctime)-15s %(levelname)s %(message)s", level=log_level
    )

    source = os.path.abspath(os.path.expanduser(source_path))
    if not os.path.exists(source):
        logging.error("Specified input file does not exist: {}", source)
        return 0

    # Load source data
    with open(source, "r") as f:
        json_source = json.loads(f.read())

    # Make a pretty file for ease of use if it doesn't exist
    pretty_out_path = PRETTY_FORMAT_NAME.format(source)
    if not os.path.exists(pretty_out_path):
        logging.info("Saving formatted JSON to {}", pretty_out_path)
        with open(pretty_out_path, "w") as f:
            f.write(json.dumps(json_source, indent=4))

    # Parse data out of json properties
    track_ids = {}

    # Make sure JSON has initial expected schema
    if json_source["type"] != "FeatureCollection":
        logging.error("JSON file does not contain expected keywords")
        return 0

    # Parse through feature list for items
    for item in json_source["features"]:
        props = item["properties"]
        if track_type == "trails":
            track_ids[item["id"]] = {
                "name": props["trail_name"],
                "second_name": props["trail_trailhead"],
                "usgsmapno": props["trail_usgsmapno"],
                }
        elif track_type == "trailheads":
            track_ids[item["id"]] = {
                "name": props["name"],
                "second_name": props["landowner"],
                "agency": props["agency"],
                }
        else:
            logging.error("Unsupported track type")
            return 0

    # Parse through saved IDs to retrieve KML files
    for k_id in track_ids:
        if track_ids[k_id]["second_name"]:
            fname = "[{}] {} - {}".format(
                k_id,
                track_ids[k_id]["name"],
                track_ids[k_id]["second_name"]
                )
        else:
            frame = "[{}] {}".format(
                k_id,
                track_ids[k_id]["name"],
                )
        
        retcode = get_kml(k_id, fname, track_type)
        if retcode > 1:
            logging.warn("Something went wrong with {}", k_id)

    logging.info("Processing complete!")

if __name__ == "__main__":
    track_type = "trailheads"
    source = "C:\\Users\\alexr\\Downloads\\{}".format(track_type)

    sys.exit(main(source, track_type))