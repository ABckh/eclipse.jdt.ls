###############################################################################
# Copyright (c) 2022 Marc Schreiber and others.
#
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
#
# Contributors:
# Marc Schreiber - initial API and implementation
###############################################################################
import argparse
from hashlib import sha1
import os
import platform
import re
import subprocess
from pathlib import Path
import tempfile

def get_java_executable(validate_java_version):
	java_executable = 'java'

	if 'JAVA_HOME' in os.environ:
		java_exec_to_test = Path(os.environ['JAVA_HOME']) / 'bin' / 'java'
		if java_exec_to_test.is_file():
			java_executable = java_exec_to_test.resolve()

	if not validate_java_version:
		return java_executable

	out = subprocess.check_output([java_executable, '-version'], stderr = subprocess.STDOUT, universal_newlines=True)

	matches = re.finditer(r"(?<=version\s\")(?P<major>\d+)(\.\d+\.\d+(_\d+)?)?", out)
	for match in matches:
		java_major_version = int(match.group("major"))

		if java_major_version < 21:
			raise Exception("jdtls requires at least Java 21")

		return java_executable

	raise Exception("Could not determine Java version")

def find_equinox_launcher(jdtls_base_directory):
	plugins_dir = jdtls_base_directory / "plugins"
	launchers = plugins_dir.glob('org.eclipse.equinox.launcher_*.jar')
	for launcher in launchers:
		return plugins_dir / launcher

	raise Exception("Cannot find equinox launcher")

def get_shared_config_path(jdtls_base_path):
	system = platform.system()

	if system in ['Linux', 'FreeBSD']:
		config_dir = 'config_linux'
	elif system == 'Darwin':
		config_dir = 'config_mac'
	elif system == 'Windows':
		config_dir = 'config_win'
	else:
		raise Exception("Unknown platform {} detected".format(system))

	return jdtls_base_path / config_dir

def main(args):
	cwd_name = os.path.basename(os.getcwd())
	jdtls_data_path = os.path.join(tempfile.gettempdir(), "jdtls-" + sha1(cwd_name.encode()).hexdigest())

	parser = argparse.ArgumentParser()
	parser.add_argument('--validate-java-version', action='store_true', default=True)
	parser.add_argument('--no-validate-java-version', dest='validate_java_version', action='store_false')
	parser.add_argument("-data", default=jdtls_data_path)

	known_args, args = parser.parse_known_args(args)
	java_executable = get_java_executable(known_args.validate_java_version)

	jdtls_base_path = Path(__file__).parent.parent
	shared_config_path = get_shared_config_path(jdtls_base_path)
	jar_path = find_equinox_launcher(jdtls_base_path)

	system = platform.system()
	exec_args = ["-Declipse.application=org.eclipse.jdt.ls.core.id1",
			"-Dosgi.bundles.defaultStartLevel=4",
			"-Declipse.product=org.eclipse.jdt.ls.core.product",
			"-Dosgi.checkConfiguration=true",
			"-Dosgi.sharedConfiguration.area=" + str(shared_config_path),
			"-Dosgi.sharedConfiguration.area.readOnly=true",
			"-Dosgi.configuration.cascaded=true",
			"-Xms1G",
			"--add-modules=ALL-SYSTEM",
			"--add-opens", "java.base/java.util=ALL-UNNAMED",
			"--add-opens", "java.base/java.lang=ALL-UNNAMED", 
			"-javaagent:{}/plugins/lombok-edge.jar".format(jdtls_base_path)] \
			+ ["-jar", jar_path,
			"-data", known_args.data] \
			+ args


	if os.name == 'posix':
		os.execvp(java_executable, exec_args)
	else:
		subprocess.run([java_executable] + exec_args)
