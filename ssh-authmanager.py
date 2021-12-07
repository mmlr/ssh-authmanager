#!/usr/bin/env python3

import configparser
import glob
import itertools
import logging
import os
import subprocess
import sys


if len(sys.argv) < 3:
	logging.error(f'usage: {sys.argv[0]} <repository> <config>')
	sys.exit(1)

logging.basicConfig(level=logging.INFO)

os.chdir(sys.argv[1])

subprocess.run(['git', 'pull'], stdout=subprocess.DEVNULL,
	stderr=subprocess.DEVNULL)

config = configparser.ConfigParser()
config.read(sys.argv[2])

basePath = os.path.realpath('keys')

keys = {}

for section in config.sections():
	normalized = os.path.normpath(section)
	for path in glob.glob(os.path.join(basePath, normalized), recursive=True):
		logging.debug(f'path {path} from {section} normalized {normalized}')

		realPath = os.path.realpath(path)
		if not realPath.startswith(basePath):
			logging.warning(f'skip outside path {realPath} from {normalized}')
			continue

		if not os.path.isfile(realPath):
			continue

		key = (normalized, section)
		if realPath in keys:
			keys[realPath].append(key)
		else:
			keys[realPath] = [key]

def specifity(value):
	return len([x for x in value if x not in '?*'])

for key, sections in keys.items():
	merged = {}
	for normalized, section in sorted(sections, key=specifity):
		merged.update(config[section].items())
	keys[key] = merged

def parseSpec(spec, which):
	restrict = [f'permit{which}="null:1"']
	permit = []

	for line in spec.splitlines():
		if not line:
			continue

		hosts = ['localhost']
		ports = line
		if ':' in line:
			hosts, ports = line.split(':')
			hosts = hosts.split(',')

		ports = ports.split(',')
		for host, port in itertools.product(hosts, ports):
			if which == 'open' and host == '*':
				if port != '*':
					logging.warning('wildcard hosts with port not supported')
					continue
				restrict = []
				continue

			permit.append(f'permit{which}="{f"{host}:" if host else ""}{port}"')

	return restrict + permit

def escape(value):
	return value.replace('"', '\\"')

def escaped(which, value):
	return f'{which}="{escape(value)}"'

for path, section in keys.items():
	logging.debug(f'{path} merged config {section}')

	options = ['restrict', 'port-forwarding']
	for which in ('open', 'listen'):
		options += parseSpec(section.get(which, ''), which)

	singleLineOptions = ['command', 'from']
	for which in singleLineOptions:
		value = section.get(which)
		if value is None:
			continue

		lines = [line for line in value.splitlines() if line]
		if not lines:
			continue

		if len(lines) > 1:
			logging.warning(f'ignoring additional lines in {which}')

		options.append(escaped(which, lines[0]))

	multilineOptions = ['environment']
	for which in multilineOptions:
		value = section.get(which)
		if value is None:
			continue

		for line in value.splitlines():
			if not line:
				continue

			options.append(escaped(which, line))

	booleanOptions = [
		('agent', 'agent-forwarding'),
		('pty', 'pty'),
		('rc', 'user-rc'),
		('x11', 'X11-forwarding')
	]
	for which, option in booleanOptions:
		value = section.get(which)
		if value is None:
			continue

		options.append(f'{"" if value == "yes" else "no-"}{option}')

	expiry = section.get('expiry')
	if expiry is not None:
		if not expiry.isnumeric() or len(expiry) not in (8, 12, 14):
			logging.error(f'invalid expiry format: {expiry}')
		else:
			options.append(f'expiry-time="{expiry}"')

	with open(path, 'r') as publicKeyFile:
		publicKey = publicKeyFile.read().strip()

	print(f'{",".join(options)} {publicKey}')
