import gzip
import importlib
import os
import tarfile
from typing import List, Dict, Any, Optional
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


def get_mime_type(filename: str) -> str:
    with open(filename, 'rb') as f:
        mime = magic.from_buffer(f.read(), mime=True)
        return mime


def is_source_code_file(filename: str) -> bool:
    # List of common source code file extensions
    source_code_extensions = {
        '.py', '.java', '.c', '.cpp', '.cs', '.js', '.ts', '.html', '.css',
        '.php', '.rb', '.swift', '.go', '.kt', '.rs', '.lua', '.pl', '.sh',
        '.bat', '.sql', '.r', '.m', '.f', '.fs', '.scala', '.clj', '.hs', '.erl',
        '.xml', '.json', '.jsonl'
    }

    # Extract the file extension
    extension = os.path.splitext(filename)[1].lower()

    # Check if the file extension is in the list
    return extension in source_code_extensions


def is_json(filename: str) -> bool:
    try:
        with open(filename, 'rb') as f:
            mime = magic.from_buffer(f.read(), mime=True)
        return 'application/json' in mime or 'application/javascript' in mime
    except Exception as e:
        print(f"Error occurred while checking file type: {e}")
        return False


def is_sqlite(filename: str) -> bool:
    try:
        with open(filename, 'rb') as f:
            mime = magic.from_buffer(f.read(), mime=True)
        return 'application/vnd.sqlite3' in mime or 'application/x-sqlite3' in mime
    except Exception as e:
        print(f"Error occurred while checking file type: {e}")
        return False


def is_text_file(filename: str) -> bool:
    try:
        with open(filename, 'rb') as f:
            mime = magic.from_buffer(f.read(), mime=True)
        return mime.startswith("text/")
    except Exception as e:
        print(f"Error occurred while checking file type: {e}")
        return False


def is_pdf(filename: str) -> bool:
    try:
        with open(filename, 'rb') as f:
            mime = magic.from_buffer(f.read(), mime=True)
        return "application/pdf" in mime
    except Exception as e:
        print(f"Error occurred while checking file type: {e}")
        return False


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


def extract_archive(filename: str, destination: str) -> Optional[Dict[str, Any]]:
    # Check if the file exists
    if not os.path.isfile(filename):
        return False
    # filename = os.path.basename(filename)
    try:
        # Determine the archive type based on the file extension
        if filename.endswith('.tar'):
            untar(filename, 'r', destination)
            return True
        elif filename.endswith('.tgz') or filename.endswith('.tar.gz'):
            untar(filename, 'r:gz', destination)
            return True
        elif filename.endswith('.zip'):
            unzip(filename, 'r', destination)
            return True
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


def is_importable(module_name):
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False
