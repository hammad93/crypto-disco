# crypto-disco

A repository containing software and resources for archival of data on M-Discs including use cases for cryptocurrency, bioinformatics, artificial intelligence, photos, videos, music, and emergency planning.

## Table of Contents

1. [Installation](#installation)
   - [Development](#development)
       - [Development GUI](#development-gui)
       - [Unit Tests](#unit-tests)
       - [Compilation](#compilation)
2. [Compliance](#compliance)
   - [Disclaimer](#disclaimer)
   - [Trademark Notice](#trademark-notice)
   - [Contact Information](#contact-information)

## Installation

### Development

- [Click here](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer) to install _uv_ through the _Standalone installer_
- Python 3.12 is currently supported
- This gives us a streamlined development experience and configure optimizations
- Download this repository. From the command line, `git clone https://github.com/hammad93/crypto-disco.git`
- If you're encountering problems, deactivate the virtual environment, delete the `.venv` folder, run `uv cache clean`, and restart this process
- Open up a command line and enter these equivalent commands inside the `crypto-disco` folder:

```bash
cd src
uv venv --python 3.12
source .venv/bin/activate # .\.venv\Scripts\activate in Windows
uv pip install -r pyproject.toml
```

#### Development GUI

- Ensure that you have activated the `uv` virtual environment from the above instructions.
- The `src` folder has the Python source code for changes utilizing an IDE.
- _PyCharm Community Edition_ or _VSCode_ are currently recommended.
- Windows OS requires the [Microsoft C++ Redistributable](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- From within the `crypto-disco` folder, run the following command from the command line. 

```bash
python src/app.py # .\src\app.py in Windows
```

#### Unit Tests

- The unit test frameworks include [QTest](https://doc.qt.io/qtforpython-6/PySide6/QtTest/index.html) and the built-in Python library `unittest`.
- Testing includes both backend algorithms and front-end user interface functionality.
- Please reference `src/test.py` Python class and the `src/tests/` folder for test cases.
- Follow the below instructions to run the unit tests.
  - Ensure you have the virtual environment running per [Development](#development).

```bash
python src/test.py # .\src\test.py in Windows
```

#### Compilation

- Please compress the repository into a ZIP file and replace the one in the assets folder for the most current source on the disc
- In order to import various files to the application for deployment, it's necessary to compile them into the _QRC_ format. [Click here](https://doc.qt.io/qtforpython-6/tutorials/basictutorial/qrcfiles.html#tutorial-qrcfiles) for details on this file. Verify that the `assets.qrc` XML file is updated and then run this command,
- Utilize `pyside6-deploy` to compile into a binary standalone executable.
  - Reference `pysidedeploy.spec` and `pyproject.toml`

```bash
pyside6-rcc assets.qrc -o src/assets.py # .\src\assets.py in Windows
pyside6-deploy -c pysidedeploy.spec
```

There is already an `assets.py` included in the repository but it might not be updated. Recompile it for the latest changes.

## Compliance

### Disclaimer

_This software is released under the CC0 license, which means it is in the public domain and can be used freely. Please review requirements.txt for any packaged software that may be subject to other licenses. Additionally, the software supports various disc formats including M-DISC, BD-R, DVD-R, and BDXL. Users should ensure their hardware is compatible with these formats before use. For more detailed information about compatibility and usage, please refer to the user documentation provided with the software._

### Trademark Notice

_All other product names, logos, and brands are the property of their respective owners and are used for identification purposes only. Use of these names, logos, and brands does not imply endorsement._

### Contact Information

_For inquiries, please contact the virtual assistant at va@fluids.ai._
