#!/usr/bin/env python3

import configparser
import glob
import itertools
import logging
import os
import sys


if len(sys.argv) < 3:
	logging.error(
		f'usage: {sys.argv[0]} <configRepo> <config> [pull[-required]]')
	sys.exit(1)

logging.basicConfig(level=logging.INFO)

os.chdir(sys.argv[1])

if len(sys.argv) > 3 and sys.argv[3] in ('pull', 'pull-required'):
	import subprocess
	logging.info('pull specified, doing git pull on configuration repo')
	subprocess.run(['git', 'pull'], stdout=sys.stderr, stderr=sys.stderr,
		check=sys.argv[3] == 'pull-required')

config = configparser.ConfigParser()
config.read(sys.argv[2])

basePath = os.path.realpath('keys')

keys = {}

for section in config.sections():
	normalized = os.path.normpath(section)
	matches = glob.glob(os.path.join(basePath, normalized), recursive=True)
	if not matches:
		logging.warning(f'unmatched pattern {section}')
		continue

	for path in matches:
		logging.debug(f'path {path} from {section} normalized {normalized}')

		realPath = os.path.realpath(path)
		if not realPath.startswith(basePath):
			logging.warning(f'skip outside path {realPath} from {normalized}')
			continue

		if not os.path.isfile(realPath):
			continue

		if realPath not in keys:
			keys[realPath] = {}

		keys[realPath].update(config[section].items())

def parseSpec(spec, which):
	restrict = [f'permit{which}="null:1"']
	permit = []

	for line in spec.splitlines():
		if not line:
			continue

		hosts = ['localhost']
		portSpecs = line
		if ':' in line:
			hosts, portSpecs = line.split(':')
			hosts = hosts.split(',')

		ports = []
		for portSpec in portSpecs.split(','):
			try:
				if '-' in portSpec:
					fromPort, toPort = [int(x) for x in portSpec.split('-', 2)]
					if not 0 < fromPort <= 0xffff or not 0 < toPort <= 0xffff:
						logging.error(
							f'invalid from or to port in range {portSpec}')

					ports += list(range(fromPort, toPort + 1))
				elif portSpec == '*':
					ports.append(portSpec)
				else:
					port = int(portSpec)
					if not 0 < port <= 0xffff:
						logging.error(f'invalid port number {portSpec}')

					ports.append(int(portSpec))

			except ValueError as exception:
				logging.error(
					f'unparsed port specification "{portSpec}": {exception}')

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

	options = ['restrict']
	if 'open' in section or 'listen' in section:
		options.append('port-forwarding')
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
