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
    print(f"Coped {binary_path[0]} over to {dest_dir}")
    return True

if __name__ == "__main__":
    install_tsmuxer_result = install_tsmuxer()
    print("Installed txMuxeR: ", install_tsmuxer_result)
