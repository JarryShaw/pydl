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

homebrew = os.path.join(subprocess.check_output(['brew', '--cache']).strip().decode(), 'downloads')
username = input('Login: ').strip()
password = getpass.getpass()


def worker(link):
    print(f'+ {link}')
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
        with open(src, 'rb') as file:
            hash_val = hashlib.sha256(file.read()).hexdigest()
        dst = os.path.join(homebrew, f'{hash_val}--{name}')
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
    link_list = set(sys.argv[1:])
    if not link_list:
        return

    with multiprocessing.Pool() as pool:
        pool.map(worker, link_list)


if __name__ == "__main__":
    sys.exit(main())
