# SSH Authmanager
The SSH Authmanager is a tool to dynamically create authorized\_keys in the
OpenSSH format. It is suitable for static file generation or use as an
AuthorizedKeysCommand for dynamic access control.

It provides a simple configuration file syntax to generate the various options
that can be provided on a per public key basis. It allows for wildcard matching
and merging of configuration based on public key file path and naming structure
to compose the final options.

Please see the fully commented [example configuration](test/hosts/test.conf) for
documentation of all supported options and pattern matching. For further details
on authorized\_keys options and their restrictions see the respective section in
[the sshd man page](https://man.openbsd.org/sshd#AUTHORIZED_KEYS_FILE_FORMAT).

# Configuration repository
The configuration is held in a repository with the following layout:
```
hosts/host-a.conf
hosts/host-b.conf
hosts/nested/host-c.conf
...
keys/key-a.pub
keys/key-b.pub
keys/nested/key-c.pub
...
```

Host configurations may be organized in arbitrary subdirectories inside the
"host" directory. The relative path to the configuration is supplied as a
command line argument.

The public key files may also be organized in arbitrary subdirectories to
facilitate more elaborate pattern matching and option composition.

# Usage
```
./ssh-authmanager.py [...] <configRepo> <config>
```

## Standalone
The SSH Authmanager can be used statically for generating authorized\_keys files
based on a configuration without installing anything. This usage is also a good
way to validate the configuration and audit the generated authorized\_keys.

```
$ ./ssh-authmanager.py my-config-repo hosts/my-host.conf > authorized_keys
```

The produced authorized\_keys file then contains the rendered output of the
configuration. Any warnings, errors and exceptions are reported to stderr and
show up in the shell.

## As AuthorizedKeysCommand
To provide dynamic generation of authorized\_keys at every login attempt, the
SSH Authmanager can be configured as an AuthorizedKeysCommand for sshd. For this
to work, the SSH Authmanager has to be installed and a dedicated user should be
created for use as the AuthorizedKeysCommandUser.

Two convenience scripts are provided. The `install.sh` script can be used to
install the SSH Authmanager system wide with the proper ownership and create a
dedicated "ssh-authmanager" system user for use as AuthorizedKeysCommandUser.
This script can be run multiple times to update the SSH Authmanager. User
creation will simply fail on further runs.

The `create-managed-user.sh` script is used for creating a user on the system
to be access managed by the SSH Authmanager and adding the corresponding
configuration to "/etc/ssh/sshd\_config". Running this script multiple times
will cause duplicate configuration to be added to sshd\_config (which is
non-fatal).

Note that prior to OpenSSH 8.8 there was a bug that prevented "Match" stanzas in
included files from working properly. The configuration therefore has to happen
inside the main sshd\_config on such versions.

Please review both scripts before running them to understand what they will do
to your system.

## Repository Pull
If the configuration repo is managed via git, the SSH Authmanager can be
instructed to automatically do a `git pull` prior to evaluating the specified
configuration with the optional `pull` or `pull-required` argument. In the
`pull` case a failed `git pull` is treated as non-fatal, in the `pull-required`
case a failure causes the program to exit without rendering any
authorized\_keys.

The stdout and stderr of the git process are output on stderr for inspection and
logging.
