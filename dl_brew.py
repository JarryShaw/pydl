# -*- coding: utf-8 -*-

import contextlib
import getpass
import hashlib
import multiprocessing
import os
import subprocess  # nosec
import sys
import tempfile
import time

import requests

EXIT_SUCCESS = 0
EXIT_FAILURE = 1


def worker(entry):
    item, username, password = entry
    type_, name, link = item.casefold().split(':', maxsplit=2)

    print(f'+ [{type_}] {name} -> {link}')
    if type_ in ('brew', 'cask'):
        dst = subprocess.check_output(['brew', '--cache', name]).strip().decode()  # nosec
    # elif type_ == 'cask':  # deprecated by Homebrew
    #     dst = subprocess.check_output(['brew', 'cask', '--cache', name]).strip().decode()  # nosec
    else:
        raise TypeError(f'invalid package type: {type_} (must be `brew` or `cask`)')

    with requests.Session() as session:
        login = session.post('https://jarryshaw.me/_api/v1/user/login',
                             json=dict(username=username, password=password))
        if login.status_code != 200:
            raise RuntimeError(login)
        if login.json()['id'] is None:
            raise PermissionError('incorrect password')
        print(f'successfully login as {username}', file=sys.stderr)

        while True:
            try:
                response = session.post('https://jarryshaw.me/_api/v1/brew', data=link)
                if response.status_code == 200:
                    print('successfully downloaded on remote', file=sys.stderr)
                    break

                if response.status_code == 408:
                    print(f'download failed: {link}', file=sys.stderr)
                    return
                if response.status_code == 401:
                    print('login expired; try again', file=sys.stderr)
                    session.post('https://jarryshaw.me/_api/v1/user/login',
                                 json=dict(username=username, password=password))
            except requests.exceptions.RequestException as error:
                print(f'download failed with {error!r}', file=sys.stderr)
                time.sleep(10)
        remote_link = response.text

    hash_name = hashlib.sha256(response.content).hexdigest()
    with tempfile.TemporaryDirectory(prefix='homebrew-') as tempdir:
        while True:
            print(f'+ aria2c {remote_link}')
            with contextlib.suppress(subprocess.CalledProcessError):
                subprocess.check_call(['aria2c',  # nosec
                                       '--max-connection-per-server=12',
                                       '--min-split-size=1M',
                                       '--out', hash_name,
                                       remote_link], cwd=tempdir)
                break
        src = os.path.join(tempdir, hash_name)
        os.rename(src, dst)

    with requests.Session() as session:
        login = session.post('https://jarryshaw.me/_api/v1/user/login',
                             json=dict(username=username, password=password))
        if login.status_code != 200:
            raise RuntimeError(login)
        if login.json()['id'] is None:
            raise PermissionError('incorrect password')

        response = session.delete('https://jarryshaw.me/_api/v1/brew', data=link)
        if response.status_code != 200:
            raise RuntimeError(response)

    caches = subprocess.check_output(['brew', '--cache']).strip().decode()  # nosec
    if type_ == 'cask':
        caches = os.path.join(caches, 'Cask')

    filename = os.path.split(dst)[1].split('--', maxsplit=1)[1]
    lnk = os.path.join(caches, filename)
    os.symlink(dst, lnk)


def main():
    temp_list = set(sys.argv[1:])
    if not temp_list:
        print(f'usage: {sys.argv[0]} <type>:<name>:<link> ...')
        return EXIT_FAILURE

    username = input('Login: ').strip()  # nosec
    password = getpass.getpass()

    CPU_COUNT = os.getenv('CPU_COUNT')
    if CPU_COUNT is not None:
        CPU_COUNT = int(CPU_COUNT)

    link_list = sorted((item, username, password) for item in temp_list)
    if CPU_COUNT == 1:
        [worker(entry) for entry in link_list]  # pylint: disable=expression-not-assigned
    else:
        with multiprocessing.Pool(processes=CPU_COUNT) as pool:
            pool.map(worker, link_list)
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
