# crypto-disco

A repository containing software and resources for archival of data on M-Discs including use cases for cryptocurrency,
bioinformatics, artificial intelligence, photos, videos, music, and emergency planning.

## Table of Contents

1. [Features](#features)
2. [FAQ](#faq)
3. [Installation](#installation)
   - [App Download](#app-download)
   - [Development](#development)
       - [GUI](#gui)
       - [Unit Tests](#unit-tests)
       - [Compilation](#compilation)
4. [Compliance](#compliance)
   - [Disclaimer](#disclaimer)
   - [Trademark Notice](#trademark-notice)
   - [Contact Information](#contact-information)

## Features

- All-in-one data/media archival image creation + M-Disc Blu-ray/DVD burner compatible with Linux, Windows, and Mac
- Error Correcting Code (ECC) standalone file generator for data images
- Redundant clones of files for archival purposes
- Built-in repair tool of corrupted files based on error correcting codes.
- Open sourced code base with minimal to no restrictive licenses such as GPL
- Media image generator compatible with playback devices including DVD or Blu-ray players
- ZIP creation tool to split large archives between multiple M-Disc's with password options
- Cybersecurity features including air-gapped capable runtime and side-channel attack considerations for ECC
- Write Once, Read Many (WORM) data archival support

## FAQ

> What is the use case?

How do we store data for as long as possible? USB, HDD, and SSD technologies are prone
to failure with lifespans ranging from 5 to 15 years; often less. Crypto Disco leverages M-Disc technology that engraves
1's and 0's (data) onto optical discs with some claims of 1000 year longevity. According to our approximations from
peer-reviewed data in scientific literature, Crypto Disco can confidently extend the lifespan of data to 100+ years
with proper care (_no warranties provided_).

> What are some example use cases?

Crypto Disco has support for all video, audio, images, or data in binary form (any file stored on a computer). Example
data for use cases range from cryptocurrency, bioinformatics, legal documents, audio, video, photos, and many more.
Specifically, hardware wallet implementations for cryptocurrency, genomic data, and media playback of precious memories
have been successful.

> How can I use Crypto Disco?

- A prerequisite for this application is access to M-Disc's and a compatible Blu-ray/DVD burner.

1. [Download](#app-download) and run the binary executable based
on the distribution of your operating system or [run the open-sourced code](#development).
2. Select files or drag-and-drop them to create an ISO image by clicking on the "Generate .ISO Image" button from the 
user interface.
3. Burn the image to an M-Disc with the included tools that leverage OS command line programs by clicking on the
"Burn to M-Disc" button. No extra setup is required with few exceptions because Crypto Disco utilizes commonly included
`.iso` burners from your operating system.

> Is Crypto Disco safe and responsible? Is this code AI generated?

Crypto Disco has all source code available for audit and undergoes testing before releases to ensure safety and
cybersecurity. AI minimally assisted with developing the code because it is necessary to publish it so that it can be
fully configured without AI. Any AI utilized adhered to environmental, moral, and ethical compliance. This requirement
is to support data archival for service far into the future where conditions surrounding AI is uncertain.
[Contact information](#contact-information) is available to communicate with responsible developers for any questions
or concerns.

> Why not use a cloud storage provider?

Cloud backups require dedicated billing, user account risks, and availability risks that maybe less reliable for longer
time scales.

> Does this work with other Blu-ray/DVD/CD formats?

Yes, select the appropriate capacity based on your optical disc. Crypto Disco configures traditional optical disc 
methodologies for M-Disc and doesn't block burning them. However, there may be unexpected behavior.

> How do I create folders and directories inside my data image?

Retaining folder, directory structure, permissions, and metadata across operating and file systems is a challenge.
Please use the included ZIP tools to create a compressed archive with them instead. Select the generated `.zip` file to
create the `.iso` image.

## Installation

### App Download

Please visit [the release page](https://github.com/hammad93/crypto-disco/releases) part of the open source framework and
software development.


### Development

- [Click here](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer) to install _uv_ through the _Standalone installer_
- Python 3.12 is currently supported
- This gives us a streamlined development experience and configure optimizations
- Download this repository. From the command line, `git clone https://github.com/hammad93/crypto-disco.git`
- If you're encountering problems, deactivate the virtual environment, delete the `.venv` folder, run `uv cache clean`,
and restart this process
- Open up a command line and enter these equivalent commands inside the `crypto-disco` folder:

```bash
cd src
uv venv --python 3.12
source .venv/bin/activate # .\.venv\Scripts\activate in Windows
uv pip install -r pyproject.toml
python ../setup.py
```

#### GUI

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

- Please compress the repository into a ZIP file and replace the one in the assets folder for the most current source on
the disc
- In order to import various files to the application for deployment, it's necessary to compile them into the _QRC_
format.
  - [Click here](https://doc.qt.io/qtforpython-6/tutorials/basictutorial/qrcfiles.html#tutorial-qrcfiles) for details on this file. Verify that the `assets.qrc` XML file is updated and then run the
below command
- Utilize `pyside6-deploy` to compile into a binary standalone executable.
  - Reference `pysidedeploy.spec` and `pyproject.toml`

```bash
pyside6-rcc assets.qrc -o src/assets.py # .\src\assets.py in Windows
pyside6-deploy -c pysidedeploy.spec
```

There is already an `assets.py` included in the repository but it might not be updated. Recompile it for the latest
changes.

## Compliance

### Disclaimer

_This software is released under the CC0 license, which means it is in the public domain and can be used freely. Please
review requirements.txt for any packaged software that may be subject to other licenses. Additionally, the software
supports various disc formats including M-DISC, BD-R, DVD-R, and BDXL. Users should ensure their hardware is compatible
with these formats before use. For more detailed information about compatibility and usage, please refer to the user
documentation provided with the software._

### Trademark Notice

_All other product names, logos, and brands are the property of their respective owners and are used for identification
purposes only. Use of these names, logos, and brands does not imply endorsement._

### Contact Information

_For inquiries, please contact the virtual assistant at va@fluids.ai._
