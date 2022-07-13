# geprotocol

## Synopsis
Extract or compare parameters from GE MRI DICOM protocol data block

## Usage

```bash
geprotocol [options] {json,diff}
```
- `json`: write protocol parameters to JSON file. The required arguments are:
   - `d`: DICOM file
   - `j`: JSON file
- `diff`: compare protocol parameters with a second DICOM file or LxProtocol file. The required 
arguments are:
   - `r`: reference DICOM or LxProtocol file
   - `t`: test DICOM file
## Options
- `-h`: display help message, and quit
- `--version`: display version and exit

## Description
Extract or compare parameters from GE MRI DICOM protocol data block stored in
element `(0025,101b)`. Element `(0025,101b)` contains text compressed using 
[gzip](gnu.org/software/gzip).

### json mode
The contents of the protocol data block are saved to a JSON file.

### diff mode
Differences between the protocol data block in the reference DICOM, or LxProtocol 
file, and test DICOM file are shown on stdout. Each parameter that differs 
between reference and test files is shown as described below:

1. If a parameter is found in both files but the value differs:

    ```bash
    < NAME ref_value
    > NAME test_value
    ```

2. If a parameter is only found in the reference file:
    ```bash
    < NAME ref_value
    > 
    ```

3. If a parameter is only found in the test DICOM file:
    ```bash
    < 
    > NAME test_value
    ```
 
## Installing
1. Create a directory to store the package e.g.:

    ```bash
    mkdir geprotocol
    ```

2. Create a new virtual environment in which to install `geprotocol`:

    ```bash
    python3 -m venv geprotocol-env
    ```
   
3. Activate the virtual environment:

    ```bash
    source geprotocol-env/bin/activate
    ```

4. Upgrade `pip` and `build`:

    ```bash
    pip install --upgrade pip
    pip install --upgrade build
    ```

5. Install using `pip`:
    ```bash
    pip install git+https://github.com/SWastling/geprotocol.git
    ```

## License
See [MIT license](./LICENSE)

## Authors and Acknowledgements
Written by [Dr Stephen Wastling](mailto:stephen.wastling@nhs.net) 