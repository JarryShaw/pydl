# -*- coding: utf-8 -*-

import contextlib
import getpass
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

    if type_ == 'brew':
        dst = subprocess.check_output(['brew', '--cache', name]).strip().decode()
    elif type_ == 'cask':
        dst = subprocess.check_output(['brew', 'cask', '--cache', name]).strip().decode()
    else:
        raise TypeError(f'invalid package type: {type_} (must be `brew` or `cask`)')

    print(f'+ [{type_}] {name} -> {link}')
    with requests.Session() as session:
        login = session.post('https://jarryshaw.me/_api/v1/user/login',
                             json=dict(username=username, password=password))
        if login.json()['id'] is None:
            raise PermissionError('incorrect password')

        while True:
            with contextlib.suppress(requests.exceptions.RequestException):
                response = session.post('https://jarryshaw.me/_api/v1/brew', data=link)
                if response.status_code == 200:
                    break
            time.sleep(60)
        link = response.text

    with tempfile.TemporaryDirectory(prefix='homebrew-') as tempdir:
        while True:
            with contextlib.suppress(subprocess.CalledProcessError):
                subprocess.check_call(['aria2c', '--max-connection-per-server=12',
                                       '--min-split-size=1M', link], cwd=tempdir)
                break
        name = os.listdir(tempdir)[0]

        src = os.path.join(tempdir, name)
        os.rename(src, dst)

    with requests.Session() as session:
        login = session.post('https://jarryshaw.me/_api/v1/user/login',
                             json=dict(username=username, password=password))
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

    link_list = sorted((item, username, password) for item in temp_list)
    with multiprocessing.Pool() as pool:
        pool.map(worker, link_list)
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
