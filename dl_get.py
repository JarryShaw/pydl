#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import contextlib
import getpass
import os
import subprocess  # nosec
import sys

import requests

# download destination path
WORKDIR = os.path.abspath(os.getenv('PATH_DOWNLOADS', os.curdir))
os.makedirs(WORKDIR, exist_ok=True)
os.chdir(WORKDIR)


def main():
    username = input('Login: ').strip()  # nosec
    password = getpass.getpass()
    with requests.Session() as session:
        login = session.post('https://jarryshaw.me/_api/v1/user/login',
                             json=dict(username=username, password=password))
        if login.status_code != 200:
            raise RuntimeError(login)
        if login.json()['id'] is None:
            raise PermissionError('incorrect password')

        response = session.get('https://jarryshaw.me/_api/v1/dl')
        if response.status_code != 200:
            raise RuntimeError(response)
        link = response.text

    while True:
        with contextlib.suppress(subprocess.CalledProcessError):
            subprocess.check_call(  # nosec
                ['aria2c', '--max-connection-per-server=12', '--min-split-size=1M', link]
            )
            break
    subprocess.run(['open', WORKDIR])  # pylint: disable=subprocess-run-check  # nosec

    with requests.Session() as session:
        login = session.post('https://jarryshaw.me/_api/v1/user/login',
                             json=dict(username=username, password=password))
        if login.status_code != 200:
            raise RuntimeError(login)
        if login.json()['id'] is None:
            raise PermissionError('incorrect password')

        response = session.delete('https://jarryshaw.me/_api/v1/dl', data=link)
        if response.status_code != 200:
            raise RuntimeError(response)


if __name__ == "__main__":
    sys.exit(main())
