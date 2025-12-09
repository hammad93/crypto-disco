# crypto-disco

A repository containing software and resources for archival of data on M-Discs including use cases for cryptocurrency, bioinformatics, artificial intelligence, photos, videos, music, and emergency planning.

## Installation

### Development

These sets of commands on Ubuntu, Linux, or equivalent can be utilized to install the development application.
Please note that _pypy_ is required instead of the standard _python_ interpreter. This is because the error correcting codes (ECC) have significant processing time reductions.

```bash
sudo apt install pypy3
pypy3 -m venv venv
source venv/bin/activate
pip install -r src/requirements.txt
cd src
pypy3 src/app.py
```

#### Compilation

In order to import various files to the application for deployment, it's necessary to compile them into the _QRC_ format. [Click here](https://doc.qt.io/qtforpython-6/tutorials/basictutorial/qrcfiles.html#tutorial-qrcfiles) for details on this file. Verify that the `assets.qrc` XML file is updated and then run this command,

```bash
pyside6-rcc assets.qrc -o src/assets.py
```

There is already an `assets.py` included in the repository but it might not be updated. Recompile it for the latest changes.

## Compliance

### Disclaimer

_This software is released under the CC0 license, which means it is in the public domain and can be used freely. Please review requirements.txt for any packaged software that may be subject to other licenses. Additionally, the software supports various disc formats including M-DISC, BD-R, DVD-R, and BDXL. Users should ensure their hardware is compatible with these formats before use. For more detailed information about compatibility and usage, please refer to the user documentation provided with the software._

### Trademark Notice

_All other product names, logos, and brands are the property of their respective owners and are used for identification purposes only. Use of these names, logos, and brands does not imply endorsement._

### Contact Information

_For inquiries, please contact the virtual assistant at va@fluids.ai._
