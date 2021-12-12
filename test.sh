#!/bin/sh

COVERAGE="python3 -m coverage"

$COVERAGE run ./ssh-authmanager.py
$COVERAGE run -a ./ssh-authmanager.py --default='x11=no' --force='pty=no' --pull=yes test hosts/test.conf

$COVERAGE run -a ./ssh-authmanager.py --allow=none --file=output --mode=644 test hosts/test.conf
ls -l output
rm output

$COVERAGE html
