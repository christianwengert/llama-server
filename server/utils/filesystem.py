import os


def find_files(directory, extension):
    result = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(extension):  # Check if file has the specified extension (e.g., ".txt")
                result.append(os.path.join(root, file))  # Add full path to the list of results
    return result


def list_directories(directory):
    result = []
    for file in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, file)):
            result.append(file)
    return result
