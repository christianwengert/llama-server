import gzip
import os
import tarfile
from typing import List
import magic
import zipfile


def find_files(directory: str, extension: str) -> List[str]:
    result = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(extension):  # Check if file has the specified extension (e.g., ".txt")
                result.append(os.path.join(root, file))  # Add full path to the list of results
    return result


def list_directories(directory: str) -> List[str]:
    result = []
    for file in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, file)):
            result.append(file)
    return result


def is_archive(filename: str) -> bool:
    # Check if the file exists
    if not os.path.isfile(filename):
        return False

    # Create a Magic object
    mime = magic.Magic(mime=True)

    # Get the MIME type of the file
    mime_type = mime.from_file(filename)

    # Check if the MIME type matches the tar, gzip, or zip format
    return mime_type in ['application/x-tar', 'application/gzip', 'application/zip']


def extract_archive(filename: str, destination: str) -> bool:
    # Check if the file exists
    if not os.path.isfile(filename):
        return False

    try:
        # Determine the archive type based on the file extension
        if filename.endswith('.tar'):
            untar(filename, 'r', destination)
        elif filename.endswith('.tgz') or filename.endswith('.tar.gz'):
            untar(filename, 'r:gz', destination)
        elif filename.endswith('.zip'):
            unzip(filename, 'r', destination)
        else:
            return False
    except (zipfile.BadZipFile, tarfile.ReadError, gzip.BadGzipFile) as _e:
        return False


def untar(filename: str, mode: str, destination: str) -> bool:
    with tarfile.open(filename, mode=mode) as archive:
        archive.extractall(path=destination, members=archive.getmembers())


def unzip(filename: str, mode: str, destination: str) -> bool:
    with zipfile.ZipFile(filename, mode=mode) as archive:
        archive.extractall(path=destination)
