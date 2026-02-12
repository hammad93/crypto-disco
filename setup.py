'''
- All additional setup after creating the virtual environment can be scripted in this file.
- Care must be made to ensure development (Python venv) and production (Pyside6 Nuitka) are both considered
'''
import platform
import requests
import zipfile
import io
import os
import stat
import sys
import shutil
import pyzipper

def add_file_assets(input_path):
    # TODO
    filename = os.path.basename(input_path)
    assets_obj = f'<file alias="{filename}">{input_path}</file>'
    with open('assets.qrc', 'r') as f:
        assets = f.read()
    assets_end = assets.find('</qresource>')
    assets = assets[:assets_end] + f'\t{assets_obj}\n\t' + assets[assets_end:]
    with open('assets.qrc', 'w') as f:
        f.write(assets)

def compile_assets():
    print('Compiling assets.qrc . . .')
    os.system('pyside6-rcc assets.qrc -o src/assets.py')

def install_tsmuxer():
    # based on this release, https://github.com/justdan96/tsMuxer/releases/tag/2.7.0 except for Mac Intel
    links = {
        'Linux': 'https://github.com/justdan96/tsMuxer/releases/download/2.7.0/tsMuxer-2.7.0-linux.zip',
        'Darwin arm64': 'https://github.com/justdan96/tsMuxer/releases/download/2.7.0/tsMuxer-2.7.0-mac.zip', # Mac Intel
        'Darwin x86_64': 'https://github.com/justdan96/tsMuxer/releases/download/nightly-2024-04-06-01-50-49/mac.zip', # Mac M-series
        'Windows 64bit': 'https://github.com/justdan96/tsMuxer/releases/download/2.7.0/tsMuxer-2.7.0-win64.zip',
        'Windows 32bit': 'https://github.com/justdan96/tsMuxer/releases/download/2.7.0/tsMuxer-2.7.0-win32.zip',
    }
    if platform.system() == 'Linux':
        link = links['Linux']
        name = 'tsMuxeR'
    elif platform.system() == 'Darwin':
        link = links[f'Darwin {platform.machine()}']
        name = 'tsMuxeR'
    elif platform.system() == 'Windows':
        link = links[f'Windows {platform.architecture()[0]}']
        name = 'tsMuxeR.exe'
    else:
        print('Unknown OS')
        return False
    # download compressed binary, extract it, and get the path of the executable
    compressed_data = requests.get(link) # download
    out_dir = 'output_setup' # folder name to put extracted files
    with zipfile.ZipFile(io.BytesIO(compressed_data.content)) as zip_file:
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        zip_file.extractall(path=out_dir)
    binary_path = [] # inconsistent binary paths among downloaded ZIP's
    for dirpath, dirnames, filenames in os.walk(out_dir): # find the binary we're looking for
        for filename in filenames:
            if filename == name: # generally, we will use the first matched for processing
                binary_path.append(os.path.abspath(os.path.join(dirpath, filename)))
                print(f"Binary found at {binary_path}")
    if len(binary_path) < 1: # we didn't find it
        print(f"Binary {name} not found")
        return False
    elif platform.system() != "Windows": # Mac and Linux require permissions to run it after downloading
        st = os.stat(binary_path[0])
        os.chmod(binary_path[0], st.st_mode | stat.S_IEXEC)
    # copy binary to appropriate virtual environment folder. sys.prefix gives path of .venv/
    dest_dir = os.path.join(sys.prefix, 'Scripts' if platform.system() == "Windows" else 'bin')
    shutil.copy2(binary_path[0], dest_dir) # copy2() preserved metadata vs copy()
    dest_path = os.path.join(dest_dir, os.path.basename(binary_path[0]))
    print(f"Copied {binary_path[0]} over to {dest_path}")
    # run command to include it in assets.py
    add_file_assets(dest_path)
    return True

def create_archive():
    archive_name = 'crypto-disco.zip'
    crypto_disco_path = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
    crypto_disco_archive = os.path.join(os.path.join(crypto_disco_path, 'assets'), archive_name)
    print(f"Creating Crypto Disco archive at {crypto_disco_archive} . . .")
    with pyzipper.AESZipFile(crypto_disco_archive, 'w', compression=pyzipper.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(crypto_disco_path):
            for file in files:
                file_path = os.path.join(root, file)
                # ignore certain files
                if any([f in file_path for f in [
                    '.git', # git version history can be quite large
                    'venv', # virtual environments are also large
                    'crypto-disco-ecc-files',
                    'output_',
                    'tests',
                    'dist',
                    'assets.py',
                    '__pycache__',
                    archive_name # avoids recursive archive
                ]]):
                    continue
                # Calculate relative path to keep directory structure inside the zip
                relative_path = os.path.relpath(file_path, crypto_disco_path)
                print(f"\tCompressing {file_path} . . .")
                zipf.write(file_path, arcname=relative_path)
    print("Done")
    return True

if __name__ == "__main__":
    install_tsmuxer_result = install_tsmuxer()
    print("Installed txMuxeR: ", install_tsmuxer_result)
    zip_crypto_disco_result = create_archive()
    print("Zipped crypto-disco: ", zip_crypto_disco_result)
    compile_assets()
