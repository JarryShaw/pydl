#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import getpass
import sys

import requests


def parse():
    parser = argparse.ArgumentParser(prog='dl-add',
                                     usage='dl-add [options] <download links...>',
                                     description='Wrapper script for video downloaders.')
    parser.add_argument('-d', '--ytdl-options', dest='ytdlopts', action='append',
                        nargs=argparse.REMAINDER, metavar='OPT', default=[],
                        help='additional options for youtube-dl')
    parser.add_argument('-u', '--uget-options', dest='ugetopts', action='append',
                        nargs=argparse.REMAINDER, metavar='OPT', default=[],
                        help='additional options for youtube-dl')
    parser.add_argument('link', nargs='+', metavar='LINK',
                        help='download links')
    return parser


def main():
    parser = parse()
    args = parser.parse_args()

    temp_list = list()
    for link in args.link:
        temp_list.extend(filter(None, map(lambda s: s.strip(), link.split())))
    link_list = set(temp_list)

    if not link_list:
        parser.print_usage()

    username = input('Login: ').strip()
    password = getpass.getpass()
    with requests.Session() as session:
        login = session.post('https://jarryshaw.me/_api/v1/user/login',
                             json=dict(username=username, password=password))
        if login.status_code != 200:
            raise RuntimeError(login)
        if login.json()['id'] is None:
            raise PermissionError('incorrect password')

        response = session.post('https://jarryshaw.me/_api/v1/dl',
                                json={
                                    'links': sorted(link_list),
                                    'ytdl-opts': args.ytdlopts,
                                    'uget-opts': args.ugetopts,
                                })
        if response.status_code != 200:
            raise RuntimeError(response)


if __name__ == "__main__":
    sys.exit(main())
