"""Extract extended data from a KML and fill in the basic attributes.

Parses through a KML with an extended schema and fills in the basic data.
"""

# Standard Python Libraries
# Python library imports
import csv
import logging
import os
import sys

# Third-Party Libraries
from defusedxml import etree
from pykml import parser

# Global variables
DEFAULT_INPUT_FILE = "/Users/jeffreyh/Downloads/NC State-Owned_Lands.kml"
DEFAULT_OUTPUT_PATH = "~/fixed_kml/"
XML_HEADER = '<?xml version="1.0" encoding="utf-8" ?>\n'

# Debug settings
LOG_LEVEL = logging.INFO
SAVE_DEBUG_FILES = False
USE_CACHED_FILES = False


def save_file(filename, content, header="", writemode="w"):
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
        f.write(header)
        f.write(content)

    return True


def save_csv_file(filename, csv_columns, data_list):
    """Save specified contents into a CSV file.

    [description]

    Arguments:
        filename {[type]} -- [description]
        headers {[type]} -- [description]
        content {[type]} -- [description]
    """
    try:
        with open(filename, "w") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            for data in data_list:
                writer.writerow(data)
    except IOError:
        print("I/O error")


def load_file(source):
    """Load a KML file, parse, and return its contents.

    [description]

    Arguments:
        source {[str]} -- Location to load from

    Returns:
        [type] -- [description]
    """
    with open(source) as f:
        doc = parser.parse(f)

    return doc


def main(kml_file, output_path, log_level=logging.DEBUG) -> int:
    """Set up logging and call the subsequent functions."""
    # Set up logging
    logging.basicConfig(
        format="%(asctime)-15s %(levelname)s %(message)s", level=log_level
    )

    # Make sure input file exists
    input_file = os.path.abspath(os.path.expanduser(kml_file))
    if not os.path.exists(input_file):
        logging.error("Specified KML file does not exist: %s", input_file)

    # Make sure output path exists
    output_path = os.path.abspath(os.path.expanduser(output_path))
    if not os.path.exists(output_path):
        logging.debug("Creating output path: %s", output_path)
        os.makedirs(output_path)

    # Process
    logging.info("Loading file...")
    kml_src = load_file(input_file)
    kml_root = kml_src.getroot()

    # Get Schema and defined field names
    schema = kml_root.Document.Schema
    logging.info("Found schema: %s", schema.tag)
    field_names = []
    for field in schema.iter():
        field_names.append(field.get("name"))
    logging.debug("Schema field names: %s", field_names)

    # Get Folder and its name
    folder = kml_root.Document.Folder
    if len(folder) > 1:
        logging.warning(
            "Not supported: Found %i Folders; will process FIRST only", len(folder)
        )
        folder = folder[0]
    logging.info("Found Folder named %s", folder.name)

    # Process Placemarks
    place_data = []
    placemarks = kml_root.findall(
        ".//{http://www.opengis.net/kml/2.2}Placemark"
    )  # noqa
    logging.info("Folder contains %i Placemarks", len(placemarks))
    for mark in placemarks:
        mark_dict = {}
        for field in mark.ExtendedData.iter():
            field_name = field.get("name")
            if not field_name:
                continue

            mark_dict[field_name] = field.text
        # Construct placemark name
        # [ComplexNam] - [DivName]
        mark_name = mark_dict["ComplexNam"]
        # logging.debug("Complex name: %s", mark_name)

        place_data.append(mark_dict)

        mark_name_el = etree.Element("name", text=mark_name)
        mark.insert(0, mark_name_el)

        # placemarks[mark_name] = mark_dict
        # logging.debug("Added Placemark %s:\n%s", mark_name, pformat(placemarks[mark_name]))

    # Save fixed KML
    out_name = os.path.join(output_path, os.path.split(kml_file)[1])
    logging.info("Saving data to KML file: %s", out_name)
    save_file(out_name, etree.tostring(kml_root, pretty_print=True, encoding="unicode"))

    # Save CSV of placemark data
    logging.info("Saving field data to CSV file: %s", out_name.replace(".kml", ".csv"))
    save_csv_file(out_name.replace(".kml", ".csv"), field_names, place_data)

    logging.info("Processing complete! Exiting...")

    # Stop logging and clean up
    logging.shutdown()
    return 0


if __name__ == "__main__":
    # Standard Python Libraries
    import argparse

    arg_parser = argparse.ArgumentParser(
        description="Fixes KML files such as NC State-Owned Land"
    )

    arg_parser.add_argument(
        "-i",
        "--input",
        default=DEFAULT_INPUT_FILE,
        type=str,
        dest="input_path",
        help="Input file path " + '(Default: "{}")'.format(DEFAULT_INPUT_FILE),
    )

    arg_parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        type=str,
        dest="output_path",
        help='Output path (Default: "{}"")'.format(DEFAULT_OUTPUT_PATH),
    )

    arg_parser.add_argument(
        "-s",
        "--start-with",
        type=int,
        dest="startwithbookid",
        help="Indicate a bookid to start with",
    )

    args = arg_parser.parse_args()

    sys.exit(main(args.input_path, args.output_path))
