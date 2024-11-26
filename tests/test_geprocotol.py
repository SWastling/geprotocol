import gzip
import importlib.metadata
import json
import pathlib

import pydicom
import pytest

import geprotocol.geprotocol as geprotocol

THIS_DIR = pathlib.Path(__file__).resolve().parent

SCRIPT_NAME = "geprotocol"
SCRIPT_USAGE = f"usage: {SCRIPT_NAME} [-h] [--version]"
__version__ = importlib.metadata.version("geprotocol")

@pytest.mark.parametrize(
    "selection, expected_output",
    [
        ('ABC "123"\nDEF "456"', {"ABC": "123", "DEF": "456"}),
        ('ABC_DEF "123 456"\nDEF "456 aef"', {"ABC_DEF": "123 456", "DEF": "456 aef"}),
    ],
)
def test_str_to_dict_dicom(selection, expected_output):
    assert geprotocol.str_to_dict_dicom(selection) == expected_output


@pytest.mark.parametrize(
    "selection, expected_output",
    [
        ('    set ABC "123"\n    set DEF "456"', {"ABC": "123", "DEF": "456"}),
        (
            '    set ABC_DEF "123 456"\n    set DEF "456 aef"',
            {"ABC_DEF": "123 456", "DEF": "456 aef"},
        ),
    ],
)
def test_str_to_dict_lx(selection, expected_output):
    assert geprotocol.str_to_dict_lx(selection) == expected_output


@pytest.mark.parametrize(
    "selection, expected_output",
    [
        ('ABC "123"\nDEF "456"', {"ABC": "123", "DEF": "456"}),
        ('ABC_DEF "123 456"\nDEF "456 aef"', {"ABC_DEF": "123 456", "DEF": "456 aef"}),
    ],
)
def test_extract_protocol_1(selection, expected_output):

    # create the 4 byte header used by GE
    header = b"Q\x03\x00\x00"

    tag_data = header + gzip.compress(selection.encode())

    ds = pydicom.dataset.Dataset()
    ds.StudyDate = "20220101"
    ds.PatientBirthDate = "19800101"
    ds.PerformedProcedureStepDescription = "MRI Head"
    ds.PatientName = "SURNAME^Firstname"
    ds.PatientID = "ABC12345678"
    ds.add_new([0x0025, 0x101B], "UN", tag_data)

    assert geprotocol.extract_protocol(ds) == expected_output


def test_extract_protocol_missing_tag(capsys):

    ds = pydicom.dataset.Dataset()
    ds.StudyDate = "20220101"
    ds.PatientBirthDate = "19800101"
    ds.PerformedProcedureStepDescription = "MRI Head"
    ds.PatientName = "SURNAME^Firstname"
    ds.PatientID = "ABC12345678"
    ds.ReferringPhysicianName = "DrSURNAME^DrFirstname"

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        geprotocol.extract_protocol(ds)

    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert (
        captured.err
        == "DICOM file does not contain private element (0025,101b), exiting\n"
    )


@pytest.mark.parametrize(
    "ref_dict, test_dict, expected_output",
    [
        ({1: "A", 2: "B", 3: "C"}, {1: "A", 2: "B", 3: "C"}, ""),
        (
            {1: "A", 2: "B", 3: "C"},
            {1: "AB", 2: "BC", 4: "F"},
            "< 1 A\n> 1 AB\n---\n< 2 B\n> 2 BC\n---\n< 3 C\n>\n---\n<\n> 4 F\n---\n",
        ),
    ],
)
def test_diff_protocols(ref_dict, test_dict, expected_output, capsys):

    geprotocol.diff_protocols(ref_dict, test_dict)
    captured = capsys.readouterr()
    assert captured.out == expected_output


def test_prints_help_1(script_runner):
    result = script_runner.run([SCRIPT_NAME])
    assert result.success
    assert result.stdout.startswith(SCRIPT_USAGE)


def test_prints_help_2(script_runner):
    result = script_runner.run([SCRIPT_NAME, "-h"])
    assert result.success
    assert result.stdout.startswith(SCRIPT_USAGE)


def test_prints_help_for_invalid_option(script_runner):
    result = script_runner.run([SCRIPT_NAME, "-!"])
    assert not result.success
    assert result.stderr.startswith(SCRIPT_USAGE)


def test_prints_version(script_runner):
    result = script_runner.run([SCRIPT_NAME, "--version"])
    assert result.success
    expected_version_output = SCRIPT_NAME + " " + __version__ + "\n"
    assert result.stdout == expected_version_output


@pytest.mark.parametrize(
    "selection, expected_output",
    [
        ('ABC "123"\nDEF "456"', {"ABC": "123", "DEF": "456"}),
        ('ABC_DEF "123 456"\nDEF "456 aef"', {"ABC_DEF": "123 456", "DEF": "456 aef"}),
    ],
)
def test_geprotocol_json(selection, expected_output, tmp_path, script_runner):

    # create the 4 byte header used by GE
    header = b"Q\x03\x00\x00"

    tag_data = header + gzip.compress(selection.encode())

    test_dcm_fp = tmp_path / "test.dcm"
    ds = pydicom.dataset.Dataset()
    ds.StudyDate = "20220101"
    ds.PatientBirthDate = "19800101"
    ds.PerformedProcedureStepDescription = "MRI Head"
    ds.PatientName = "SURNAME^Firstname"
    ds.PatientID = "ABC12345678"
    ds.add_new([0x0025, 0x101B], "UN", tag_data)
    ds.file_meta = pydicom.dataset.FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = "1.2.840.10008.1.2.1"
    ds.file_meta.MediaStorageSOPInstanceUID = "1.2.3.4"
    ds.file_meta.ImplementationVersionName = "report"
    ds.file_meta.ImplementationClassUID = "1.2.3.4"
    ds.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.4"
    ds.is_implicit_VR = False
    ds.is_little_endian = True
    pydicom.dataset.validate_file_meta(ds.file_meta)
    ds.save_as(test_dcm_fp, write_like_original=False)

    protocol_json = tmp_path / "protocol_dump.json"
    result = script_runner.run(
        [SCRIPT_NAME, "json", str(test_dcm_fp), str(protocol_json)]
    )
    assert result.success

    assert protocol_json.is_file()

    with open(protocol_json) as f:
        contents = json.load(f)

    assert contents == expected_output


def test_geprotocol_json_error(tmp_path, script_runner):

    test_dcm_fp = tmp_path / "test.dcm"
    ds = pydicom.dataset.Dataset()
    ds.StudyDate = "20220101"
    ds.PatientBirthDate = "19800101"
    ds.PerformedProcedureStepDescription = "MRI Head"
    ds.PatientName = "SURNAME^Firstname"
    ds.PatientID = "ABC12345678"
    ds.file_meta = pydicom.dataset.FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = "1.2.840.10008.1.2.1"
    ds.file_meta.MediaStorageSOPInstanceUID = "1.2.3.4"
    ds.file_meta.ImplementationVersionName = "report"
    ds.file_meta.ImplementationClassUID = "1.2.3.4"
    ds.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.4"
    ds.is_implicit_VR = False
    ds.is_little_endian = True
    pydicom.dataset.validate_file_meta(ds.file_meta)
    ds.save_as(test_dcm_fp, write_like_original=False)

    protocol_json = tmp_path / "protocol_dump.json"
    result = script_runner.run(
        [SCRIPT_NAME, "json", str(test_dcm_fp), str(protocol_json)]
    )
    assert not result.success
    assert result.stderr.startswith(
        "DICOM file does not contain private element (0025,101b), exiting\n"
    )


@pytest.mark.parametrize(
    "ref_block, test_block, expected_output",
    [
        ('ABC "123"\nDEF "456"', 'ABC "123"\nDEF "456"', ""),
        (
            'ABC "123"\nDEF "457"\nGHI "89"',
            'ABC "123"\nDEF "456"\nXYZ "101"',
            "< DEF 457\n> DEF 456\n---\n< GHI 89\n>\n---\n<\n> XYZ 101\n---\n",
        ),
    ],
)
def test_geprotocol_diff(
    ref_block, test_block, expected_output, tmp_path, script_runner
):

    # create the 4 byte header used by GE
    header = b"Q\x03\x00\x00"

    ref_tag_data = header + gzip.compress(ref_block.encode())
    test_tag_data = header + gzip.compress(test_block.encode())

    ref_dcm_fp = tmp_path / "ref.dcm"
    test_dcm_fp = tmp_path / "test.dcm"

    ds_ref = pydicom.dataset.Dataset()
    ds_ref.StudyDate = "20220101"
    ds_ref.PatientBirthDate = "19800101"
    ds_ref.PerformedProcedureStepDescription = "MRI Head"
    ds_ref.PatientName = "SURNAME^Firstname"
    ds_ref.PatientID = "ABC12345678"
    ds_ref.add_new([0x0025, 0x101B], "UN", ref_tag_data)
    ds_ref.file_meta = pydicom.dataset.FileMetaDataset()
    ds_ref.file_meta.TransferSyntaxUID = "1.2.840.10008.1.2.1"
    ds_ref.file_meta.MediaStorageSOPInstanceUID = "1.2.3.4"
    ds_ref.file_meta.ImplementationVersionName = "report"
    ds_ref.file_meta.ImplementationClassUID = "1.2.3.4"
    ds_ref.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.4"
    ds_ref.is_implicit_VR = False
    ds_ref.is_little_endian = True
    pydicom.dataset.validate_file_meta(ds_ref.file_meta)
    ds_ref.save_as(ref_dcm_fp, write_like_original=False)

    ds_test = pydicom.dataset.Dataset()
    ds_test.StudyDate = "20220101"
    ds_test.PatientBirthDate = "19800101"
    ds_test.PerformedProcedureStepDescription = "MRI Head"
    ds_test.PatientName = "SURNAME^Firstname"
    ds_test.PatientID = "ABC12345678"
    ds_test.add_new([0x0025, 0x101B], "UN", test_tag_data)
    ds_test.file_meta = pydicom.dataset.FileMetaDataset()
    ds_test.file_meta.TransferSyntaxUID = "1.2.840.10008.1.2.1"
    ds_test.file_meta.MediaStorageSOPInstanceUID = "1.2.3.4"
    ds_test.file_meta.ImplementationVersionName = "report"
    ds_test.file_meta.ImplementationClassUID = "1.2.3.4"
    ds_test.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.4"
    ds_test.is_implicit_VR = False
    ds_test.is_little_endian = True
    pydicom.dataset.validate_file_meta(ds_test.file_meta)
    ds_test.save_as(test_dcm_fp, write_like_original=False)

    result = script_runner.run([SCRIPT_NAME, "diff", str(ref_dcm_fp), str(test_dcm_fp)])
    assert result.success
    assert result.stdout == expected_output


@pytest.mark.parametrize(
    "ref_block, test_block, expected_output",
    [
        ('    set ABC "123"\n    set DEF "456"', 'ABC "123"\nDEF "456"', ""),
        (
            '    set ABC "123"\n    set DEF "457"\n    set GHI "89"',
            'ABC "123"\nDEF "456"\nXYZ "101"',
            "< DEF 457\n> DEF 456\n---\n< GHI 89\n>\n---\n<\n> XYZ 101\n---\n",
        ),
    ],
)
def test_geprotocol_diff_lx(
    ref_block, test_block, expected_output, tmp_path, script_runner
):
    lx_fp = tmp_path / "LxProtocol"
    with open(lx_fp, "w") as f:
        f.write(ref_block)

    # create the 4 byte header used by GE
    header = b"Q\x03\x00\x00"
    test_tag_data = header + gzip.compress(test_block.encode())
    test_dcm_fp = tmp_path / "test.dcm"

    ds_test = pydicom.dataset.Dataset()
    ds_test.StudyDate = "20220101"
    ds_test.PatientBirthDate = "19800101"
    ds_test.PerformedProcedureStepDescription = "MRI Head"
    ds_test.PatientName = "SURNAME^Firstname"
    ds_test.PatientID = "ABC12345678"
    ds_test.add_new([0x0025, 0x101B], "UN", test_tag_data)
    ds_test.file_meta = pydicom.dataset.FileMetaDataset()
    ds_test.file_meta.TransferSyntaxUID = "1.2.840.10008.1.2.1"
    ds_test.file_meta.MediaStorageSOPInstanceUID = "1.2.3.4"
    ds_test.file_meta.ImplementationVersionName = "report"
    ds_test.file_meta.ImplementationClassUID = "1.2.3.4"
    ds_test.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.4"
    ds_test.is_implicit_VR = False
    ds_test.is_little_endian = True
    pydicom.dataset.validate_file_meta(ds_test.file_meta)
    ds_test.save_as(test_dcm_fp, write_like_original=False)

    result = script_runner.run([SCRIPT_NAME, "diff", str(lx_fp), str(test_dcm_fp)])
    assert result.success
    assert result.stdout == expected_output
