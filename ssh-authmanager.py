#!/usr/bin/env python3

import configparser
import glob
import itertools
import logging
import os
import sys
import argparse


allOptions = ['open', 'listen', 'command', 'from', 'environment', 'agent',
	'pty', 'rc', 'x11', 'expiry', 'none']

parser = argparse.ArgumentParser()
parser.add_argument('repository',
	help='Path of the configuration repository to work in.')
parser.add_argument('config',
	help='Path of the configuration file to use, relative to repository.')
parser.add_argument('-f', '--file', dest='filename',
	help='Write to FILE instead of stdout. The output is first written to a '
		'new file and the named file is then replaced.', metavar='FILE')
parser.add_argument('-p', '--pull', dest='pull',
	choices=['no', 'yes', 'require'], default='no',
	help='Run "git pull" inside of the config repo. Defaults to "no", aborts '
		'when set to "require" and the pull fails.')
parser.add_argument('-a', '--allow', choices=allOptions, dest='allowed',
	action='append', help='Only allow the specified options to be generated '
		'from the config.')
parser.add_argument('-d', '--default', action='append', dest='defaults',
	help='Add default options to all rendered output which can be overridden '
		'by the configuration.')
parser.add_argument('-x', '--force', action='append', dest='forced',
	help='Add forced options to all rendered output which can not be '
		'overridden by the configuration.')
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
	help='Set log level to debug.')

args = parser.parse_args()

logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

if args.filename is not None:
	args.filename = os.path.realpath(args.filename)

os.chdir(args.repository)

if args.pull != 'no':
	import subprocess
	logging.info('pull specified, doing git pull on configuration repo')
	subprocess.run(['git', 'pull'], stdout=sys.stderr, stderr=sys.stderr,
		check=args.pull == 'require')

config = configparser.ConfigParser()
config.read(args.config)

defaults = {}
forced = {}

static = configparser.ConfigParser()
for which in ('defaults', 'forced'):
	values = getattr(args, which)
	if not values:
		continue

	static.read_string('\n'.join([f'[{which}]'] + values))
	{
		'defaults': defaults,
		'forced': forced
	}[which].update(static[which].items())

basePath = os.path.realpath('keys')

outputFile = sys.stdout
if args.filename is not None:
	temporaryFilename = f'{args.filename}.ssh-authmanager-new'
	outputFile = open(temporaryFilename, 'w')
	os.fchmod(outputFile.fileno(), 0o0600)

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
			keys[realPath] = defaults.copy()

		keys[realPath].update(config[section].items())

if forced:
	for key in keys:
		keys[key].update(forced)

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
						continue

					ports += list(range(fromPort, toPort + 1))
				elif portSpec == '*':
					ports.append(portSpec)
				else:
					port = int(portSpec)
					if not 0 < port <= 0xffff:
						logging.error(f'invalid port number {portSpec}')
						continue

					ports.append(int(portSpec))

			except ValueError as exception:
				logging.error(
					f'unparsed port specification "{portSpec}": {exception}')

		for host, port in itertools.product(hosts, ports):
			if which == 'open' and host == '*' and port != '*':
				logging.warning('wildcard host with port not supported in open')
				continue

			restrict = []
			permit.append(f'permit{which}="{f"{host}:" if host else ""}{port}"')

	return restrict + permit, len(permit) > 0

def escape(value):
	return value.replace('"', '\\"')

def escaped(which, value):
	return f'{which}="{escape(value)}"'

allowed = allOptions if args.allowed is None else args.allowed

for path, section in keys.items():
	logging.debug(f'{path} merged config {section}')

	options = ['restrict']

	portOptions = ['open', 'listen']
	forwarding = ['port-forwarding']
	needed = False
	for which in portOptions:
		portSpecs = section.get(which, '') if which in allowed else ''
		portOptions, hasPermit = parseSpec(portSpecs, which)
		forwarding += portOptions
		needed |= hasPermit

	if needed:
		options += forwarding

	singleLineOptions = ['command', 'from']
	for which in singleLineOptions:
		if which not in allowed:
			continue

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
		if which not in allowed:
			continue

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
		if which not in allowed:
			continue

		value = section.get(which)
		if value is None:
			continue

		options.append(f'{"" if value == "yes" else "no-"}{option}')

	if 'expiry' in allowed:
		expiry = section.get('expiry')
		if expiry is not None:
			if not expiry.isnumeric() or len(expiry) not in (8, 12, 14):
				logging.error(f'invalid expiry format: {expiry}')
			else:
				options.append(f'expiry-time="{expiry}"')

	with open(path, 'r') as publicKeyFile:
		publicKey = publicKeyFile.read().strip()

	print(f'{",".join(options)} {publicKey}', file=outputFile)

if args.filename is not None:
	os.rename(temporaryFilename, args.filename)
