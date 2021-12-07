#!/bin/sh

if [ -z "$3" ]
then
	echo "usage: $0 <username> <configRepository> <configPathRelativeToRepo>"
	exit 1
fi

useradd --system --home-dir /dev/null --shell /usr/sbin/nologin "$1"
usermod -p '*' "$1"

cat >> "/etc/ssh/sshd_config" << EOF

Match User "$1"
	AuthorizedKeysCommand /usr/bin/ssh-authmanager "$2" "$3"
	AuthorizedKeysCommandUser ssh-authmanager
Match All
EOF

echo "Please reload the SSH daemon config"
