#!/bin/sh

python3 -m coverage run ./ssh-authmanager.py
python3 -m coverage run -a ./ssh-authmanager.py --pull=yes test hosts/test.conf
python3 -m coverage html
