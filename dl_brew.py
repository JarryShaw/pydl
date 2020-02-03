# -*- coding: utf-8 -*-

import contextlib
import getpass
import hashlib
import multiprocessing
import os
import subprocess
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
    if type_ == 'brew':
        dst = subprocess.check_output(['brew', '--cache', name]).strip().decode()
    elif type_ == 'cask':
        dst = subprocess.check_output(['brew', 'cask', '--cache', name]).strip().decode()
    else:
        raise TypeError(f'invalid package type: {type_} (must be `brew` or `cask`)')

    with requests.Session() as session:
        login = session.post('https://jarryshaw.me/_api/v1/user/login',
                             json=dict(username=username, password=password))
        if login.status_code != 200:
            raise RuntimeError(login)
        if login.json()['id'] is None:
            raise PermissionError('incorrect password')

        while True:
            with contextlib.suppress(requests.exceptions.RequestException):
                response = session.post('https://jarryshaw.me/_api/v1/brew', data=link)
                if response.status_code == 200:
                    break

                if response.status_code == 401:
                    session.post('https://jarryshaw.me/_api/v1/user/login',
                                 json=dict(username=username, password=password))
            time.sleep(60)
        link = response.text

    name = hashlib.sha256(response.content).hexdigest()
    with tempfile.TemporaryDirectory(prefix='homebrew-') as tempdir:
        while True:
            with contextlib.suppress(subprocess.CalledProcessError):
                subprocess.check_call(['aria2c',
                                       '--max-connection-per-server=12',
                                       '--min-split-size=1M',
                                       '--out', name,
                                       link], cwd=tempdir)
                break
        src = os.path.join(tempdir, name)
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


def main():
    temp_list = set(sys.argv[1:])
    if not temp_list:
        print(f'usage: {sys.argv[0]} <type>:<name>:<link> ...')
        return EXIT_FAILURE

    username = input('Login: ').strip()
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
