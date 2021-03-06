#!/usr/bin/env python
"""
Download and install a C++ toolchain.
Currently implemented platforms (platform.system)
    Windows: RTools 3.5 (default), 4.0
    Darwin (macOS): Not implemented
    Linux: Not implemented
Optional command line arguments:
   -v, --version : version, defaults to latest
   -d, --dir : install directory, defaults to '~/.cmdstanpy
   -s (--silent) : install with /VERYSILENT instead of /SILENT for RTools
"""
import argparse
import contextlib
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from time import sleep

EXTENSION = '.exe' if platform.system() == 'Windows' else ''
IS_64BITS = sys.maxsize > 2 ** 32


@contextlib.contextmanager
def pushd(new_dir):
    """Acts like pushd/popd."""
    previous_dir = os.getcwd()
    os.chdir(new_dir)
    yield
    os.chdir(previous_dir)


def usage():
    """Print usage."""
    print(
        """Arguments:
        -v (--version) :CmdStan version
        -d (--dir) : install directory
        -s (--silent) : install with /VERYSILENT instead of /SILENT for RTools
        -h (--help) : this message
        """
    )


def get_config(dir, silent):
    """Assemble config info."""
    config = []
    if platform.system() == 'Windows':
        _, dir = os.path.splitdrive(os.path.abspath(dir))
        if dir.startswith('\\'):
            dir = dir[1:]
        config = [
            '/SP-',
            '/VERYSILENT' if silent else '/SILENT',
            '/SUPPRESSMSGBOXES',
            '/CURRENTUSER',
            'LANG="English"',
            '/DIR="{}"'.format(dir),
            '/NOICONS',
            '/NORESTART',
        ]
    return config


def install_version(installation_dir, installation_file, version, silent):
    """Install specified toolchain version."""
    with pushd('.'):
        print(
            'Installing the C++ toolchain: {}'.format(
                os.path.splitext(installation_file)[0]
            )
        )
        cmd = [installation_file]
        cmd.extend(get_config(installation_dir, silent))
        print(' '.join(cmd))
        proc = subprocess.Popen(
            cmd,
            cwd=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ,
        )
        while proc.poll() is None:
            output = proc.stdout.readline().decode('utf-8').strip()
            if output:
                print(output, flush=True)
        _, stderr = proc.communicate()
        if proc.returncode:
            print('Installation failed: returncode={}'.format(proc.returncode))
            if stderr:
                print(stderr.decode('utf-8').strip())
            if is_installed(installation_dir, version):
                print('Installation files found at the installation location.')
            sys.exit(3)
    # check installation
    if is_installed(installation_dir, version):
        os.remove(installation_file)
    print('Installed {}'.format(os.path.splitext(installation_file)[0]))


def is_installed(toolchain_loc, version):
    """Returns True is toolchain is installed."""
    if platform.system() == 'Windows':
        if version == '3.5':
            if not os.path.exists(os.path.join(toolchain_loc, 'bin')):
                return False
            return os.path.exists(
                os.path.join(
                    toolchain_loc,
                    'mingw_64' if IS_64BITS else 'mingw_32',
                    'bin',
                    'g++' + EXTENSION,
                )
            )
        elif version == '4.0':
            return os.path.exists(
                os.path.join(
                    toolchain_loc,
                    'mingw64' if IS_64BITS else 'mingw32',
                    'bin',
                    'g++' + EXTENSION,
                )
            )
        else:
            return False
    return False


def latest_version():
    """Windows version hardcoded to 3.5."""
    if platform.system() == 'Windows':
        return '3.5'
    return ''


def retrieve_toolchain(filename, url):
    """Download toolchain from URL."""
    print('Downloading C++ toolchain: {}'.format(filename))
    for i in range(6):
        try:
            _ = urllib.request.urlretrieve(url, filename=filename)
            break
        except urllib.error.URLError as err:
            print('Failed to download C++ toolchain')
            print(err)
            if i < 5:
                print('retry ({}/5)'.format(i + 1))
                sleep(1)
                continue
            sys.exit(3)
    print('Download successful, file: {}'.format(filename))


def validate_dir(install_dir):
    """Check that specified install directory exists, can write."""
    if not os.path.exists(install_dir):
        try:
            os.makedirs(install_dir)
        except OSError as e:
            raise ValueError(
                'Cannot create directory: {}'.format(install_dir)
            ) from e
    else:
        if not os.path.isdir(install_dir):
            raise ValueError(
                'File exists, should be a directory: {}'.format(install_dir)
            )
        try:
            with open('tmp_test_w', 'w') as fd:
                pass
            os.remove('tmp_test_w')  # cleanup
        except OSError as e:
            raise ValueError(
                'Cannot write files to directory {}'.format(install_dir)
            ) from e


def normalize_version(version):
    """Return maj.min part of version string."""
    if platform.system() == 'Windows':
        if version in ['4', '40']:
            version = '4.0'
        elif version == '35':
            version = '3.5'
    return version


def get_toolchain_name():
    """Return toolchain name."""
    if platform.system() == 'Windows':
        return 'RTools'
    return ''


def get_url(version):
    """Return URL for toolchain."""
    if platform.system() == 'Windows':
        if version == '4.0':
            # pylint: disable=line-too-long
            if IS_64BITS:
                url = 'https://cran.r-project.org/bin/windows/testing/rtools40-x86_64.exe'  # noqa: disable=E501
            else:
                url = 'https://cran.r-project.org/bin/windows/testing/rtools40-i686.exe'  # noqa: disable=E501
        elif version == '3.5':
            url = 'https://cran.r-project.org/bin/windows/Rtools/Rtools35.exe'
    return url


def get_toolchain_version(name, version):
    """Toolchain version."""
    root_folder = None
    toolchain_folder = None
    if platform.system() == 'Windows':
        root_folder = 'RTools'
        toolchain_folder = '{}{}'.format(name, version.replace('.', ''))

    return root_folder, toolchain_folder


def main():
    """Main."""
    if platform.system() not in {'Windows'}:
        msg = (
            'Download for the C++ toolchain'
            ' on the current platform has not been implemented: %s'
        )
        raise NotImplementedError(msg % platform.system())

    parser = argparse.ArgumentParser()
    parser.add_argument('--version', '-v')
    parser.add_argument('--dir', '-d')
    parser.add_argument('--silent', '-s', action='store_true')
    args = parser.parse_args(sys.argv[1:])

    toolchain = get_toolchain_name()
    version = vars(args)['version']
    if version is None:
        version = latest_version()
    version = normalize_version(version)
    print("C++ toolchain '{}' version: {}".format(toolchain, version))

    url = get_url(version)

    install_dir = vars(args)['dir']
    if install_dir is None:
        install_dir = os.path.expanduser(os.path.join('~', '.cmdstanpy'))
    validate_dir(install_dir)
    print('Install directory: {}'.format(install_dir))

    if platform.system() == 'Windows':
        silent = 'silent' in vars(args)
        # force silent == False for 4.0 version
        if 'silent' not in vars(args) and version in ('4.0', '4', '40'):
            silent = False
    else:
        silent = False

    root_folder, toolchain_version = get_toolchain_version(toolchain, version)
    toolchain_loc = os.path.join(root_folder, toolchain_version)
    with pushd(install_dir):
        if is_installed(toolchain_loc, version):
            print(
                'C++ toolchain {} already installed'.format(toolchain_version)
            )
        else:
            if os.path.exists(toolchain_loc):
                shutil.rmtree(toolchain_loc, ignore_errors=False)
            retrieve_toolchain(toolchain_version + EXTENSION, url)
            install_version(
                toolchain_loc, toolchain_version + EXTENSION, version, silent
            )


if __name__ == '__main__':
    main()
