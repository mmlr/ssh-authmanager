#!/bin/sh

python3 -m coverage run ./ssh-authmanager.py
python3 -m coverage run -a ./ssh-authmanager.py test hosts/test.conf pull
python3 -m coverage html
