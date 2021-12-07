#!/bin/sh

INSTALL_PATH=/usr/bin/ssh-authmanager

cp ssh-authmanager.py $INSTALL_PATH
chown root:root $INSTALL_PATH
chmod 555 $INSTALL_PATH

useradd --system --home-dir /dev/null --shell /usr/sbin/nologin ssh-authmanager
