#!/bin/sh

python3 -m coverage run ./ssh-authmanager.py
python3 -m coverage run -a ./ssh-authmanager.py --file=output --pull=yes test hosts/test.conf
rm output
python3 -m coverage html
