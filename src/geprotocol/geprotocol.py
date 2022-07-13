"""Extract or compare parameters from GE MRI DICOM protocol data block"""

import argparse
import gzip
import json
import pathlib
import re
import sys

import importlib_metadata as metadata
import pydicom

try:
    __version__ = metadata.version("geprotocol")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"


def str_to_dict_dicom(s):
    """
    Convert multi-line string of parameter/value pairs to a dictionary

    The string is of the form:

    PARAMETER1 "value1"\nPARAMETER2 "value2"\n

    The PARAMETERs become the keys in the dictionary and each has an associated
    value

    :param s: parameter/value pairs as multi-line string
    :type s: str
    :return: dictionary of parameters and values
    :rytpe: dict[str, str]
    """
    d = {}
    for line in s.splitlines():
        m = re.match(r'(\w+)\s"(.*?)"', line)
        d[m.group(1)] = m.group(2)

    return d


def str_to_dict_lx(s):
    """
    Convert multi-line string of parameter/value pairs from LxProtocol to a dictionary

    The string is of the form:

        set PARAMETER1 "value1"\n    set PARAMETER2 "value2"\n

    The PARAMETERs become the keys in the dictionary and each has an associated
    value

    :param s: parameter/value pairs as multi-line string
    :type s: str
    :return: dictionary of parameters and values
    :rytpe: dict[str, str]
    """
    d = {}
    for line in s.splitlines():
        m = re.match(r'\s\s\s\sset\s(\w+)\s"(.*?)"', line)
        d[m.group(1)] = m.group(2)

    return d


def extract_protocol(ds):
    """
    Extract the raw protocol block from DICOM element (0025,101b)

    :param ds: DICOM dataset
    :type ds: pydicom.dataset.FileDataset
    :return: protocol parameters
    :rtype: dict
    """
    if [0x25, 0x101B] not in ds:
        sys.stderr.write(
            "DICOM file does not contain private element (0025,101b), exiting\n"
        )
        sys.exit(1)

    protocol_raw = ds[0x25, 0x101B].value
    protocol_decoded = gzip.decompress(protocol_raw[4:]).decode()

    return str_to_dict_dicom(protocol_decoded)


def diff_protocols(r, t):
    """
    Print the differences between a reference and test dictionary to stdout

    :param r: reference dict
    :type r: dict
    :param t: test dict
    :type t: dict
    """
    # check all the items in r
    for k, v in r.items():
        if k in t:
            if v != t[k]:
                print("<", k, v)
                print(">", k, t[k])
                print("---")
        else:
            print("<", k, v)
            print(">")
            print("---")
    # check for items that are in t but not r
    for k, v in t.items():
        if k not in r:
            print("<")
            print(">", k, v)
            print("---")


def main():
    parser = argparse.ArgumentParser(
        description="Extract or compare parameters from GE MRI DICOM "
        "protocol data block in element (0025,101b)"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="algorithm", required=True)

    parser_json = subparsers.add_parser(
        "json", help="write protocol parameters to JSON file"
    )

    parser_json.add_argument(
        "d",
        help="DICOM file",
        type=pathlib.Path,
    )

    parser_json.add_argument(
        "j",
        help="JSON file",
        type=pathlib.Path,
    )

    parser_diff = subparsers.add_parser(
        "diff",
        help="compare protocol parameters with a second DICOM file or LxProtocol file",
    )

    parser_diff.add_argument(
        "r",
        help="reference DICOM or LxProtocol file",
        type=pathlib.Path,
    )

    parser_diff.add_argument(
        "t",
        help="test DICOM file",
        type=pathlib.Path,
    )

    if len(sys.argv) == 1:
        sys.argv.append("-h")

    args = parser.parse_args()

    if args.algorithm == "json":
        ds = pydicom.dcmread(args.d, stop_before_pixels=True)
        with open(args.j, "w") as f:
            json.dump(extract_protocol(ds), f, indent=0)
    else:
        if pydicom.misc.is_dicom(args.r):
            ds_r = pydicom.dcmread(args.r, stop_before_pixels=True)
            protocol_r = extract_protocol(ds_r)
        else:
            with open(args.r, "r") as f:
                protocol_r = str_to_dict_lx(f.read())

        ds_t = pydicom.dcmread(args.t, stop_before_pixels=True)
        protocol_t = extract_protocol(ds_t)

        diff_protocols(protocol_r, protocol_t)


if __name__ == "__main__":  # pragma: no cover
    main()
