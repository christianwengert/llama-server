import subprocess
from github import Github
import pathlib
import git

g = Github()

max_size_in_kb = 50

query = f'language:c language:cpp size:<{max_size_in_kb}'
repositories = g.search_repositories(query=query, sort='stars')


STORE = pathlib.Path('~/Downloads').expanduser() / 'github'
STORE.mkdir(exist_ok=True)

i = 0

for repo in repositories:

    if repo.fork:
        continue

    outdir = STORE / repo.full_name
    outdir.mkdir(exist_ok=True, parents=True)

    subprocess.run([
        'git',
        'clone',
        '--recurse-submodules',
        '-j8',
        f'{repo.html_url}',
        outdir
    ])

    for build_file in list(outdir.glob('Makefile')):  # makefiles
        print(f'{repo.full_name}  {build_file}')

        subprocess.run([
            'make',
            build_file
        ])

        break

    for build_file in list(outdir.glob('CMakeLists.txt')):  # makefiles
        print(f'{repo.full_name}  {build_file}')
        break

    for build_file in list(outdir.glob('configure')):  # makefiles
        print(f'{repo.full_name}  {build_file}')
        break

    i += 1
    if i> 10:
        break
    # open local repo
    # local_repo = git.repo.Repo(outdir)

    # check if we have a configure, cmake  or make
