#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple SSH Manager (SSM) is a program to simplify the act of SSH'ing into remote hosts

SSM does this by providing a wrapper interface to the underlying OpenSSH command. This allows
shorthand specification for options that are frequently used but can otherwise be quite verbose
when using OpenSSH directly. Where possible, an OpenSSH config file should be used, and this
tool aims to provide a simplified interface for options that need to be dynamic, or are not
supported by the OpenSSH config file.
"""

import argparse
import ipaddress
import importlib.metadata
import socket
import subprocess

from .config import Config


VERSION = importlib.metadata.version("malathair_ssm")


class HelpFormatter(argparse.HelpFormatter):
    """Class to override the default argparse help formatter"""

    # Override the default max_help_position. It will now default to 32 instead of 24
    # Some of the flags are a bit long and this just makes the output a tad nicer
    def __init__(self, prog, indent_increment=2, max_help_position=32, width=None):
        super().__init__(prog, indent_increment, max_help_position, width)

    # Backport Python3.13 action formatting behavior to older python versions
    # i.e. use this:   -s, --long ARGS
    # instead of this: -s ARGS, --long ARGS
    def _format_action_invocation(self, action):
        if not action.option_strings:
            return super()._format_action_invocation(action)

        default = self._get_default_metavar_for_optional(action)
        args_string = self._format_args(action, default)
        return ", ".join(action.option_strings) + " " + args_string


def arg_parser(config) -> argparse.Namespace:
    """
    Defines and parses CLI arguments for the program

    Parameters
    ----------
    config : Config
        An instance of SSM's Config class which holds the working copy of the configuration

    Returns
    -------
    argparse.Namespace
        An argparse Namespace object containing all program arguments intuitively accessible
        as attributes. Each attribute stores the user provided value, the default value, or None
    """
    parser = argparse.ArgumentParser(
        description="An SSH wrapper to simplify life",
        formatter_class=HelpFormatter,
    )

    session = parser.add_argument_group()
    jump = session.add_mutually_exclusive_group()
    tunnels = parser.add_argument_group()

    parser.add_argument(
        "host", type=str, help="Subdomain of the host's url or the host's IP address"
    )

    parser.add_argument("-v", "--version", action="version", version=VERSION)

    jump.add_argument(
        "-j",
        "--jump",
        action="store_true",
        help="SSHs via the jump host specified in the configuration file",
    )
    jump.add_argument(
        "-J",
        "--jumphost",
        default=config.jump_host,
        type=str,
        help="Overrides the jump host specified in the configuration file",
    )

    session.add_argument(
        "-c",
        "--command",
        type=str,
        help=(
            "Execute the specified command on the remote system without opening an interactive "
            "shell. The connection will be terminated immediately after command executes. "
            "Additionally, all other arguments supplied will be ignored with the exception of "
            "--jump and --jumphost"
        ),
    )
    session.add_argument(
        "-o",
        "--options",
        action="store_true",
        help="Use the set of SSH options specified in the configuration file",
    )
    session.add_argument(
        "-O, --option",
        type=str,
        help="Specify a set of SSH options for this connection",
    )
    session.add_argument(
        "-p",
        "--port",
        default=config.ssh_port,
        type=str,
        help="Specifies the port to use for the SSH session",
    )

    tunnels.add_argument(
        "-t",
        "--tunnel",
        action="store_true",
        help="Start a SOCKS5 tunnel on the port defined in the configuration file",
    )

    return parser.parse_args()


# Return a valid IP address or hostname to connect to
def build_domain(host_arg, config):
    host_index = host_arg.find("@") + 1
    host = host_arg[host_index::]

    try:
        ipaddress.IPv4Network(host)
        return host_arg
    except ipaddress.AddressValueError:
        pass

    # If we are confident the host is not an FQDN skip this test. DNS lookups are incredibly slow
    # if the lookup value isn't an FQDN. This optimization only works with public DNS servers. If
    # using a private DNS server that contains records that are just the host portion of the FQDN
    # then this will make it impossible to resolve those
    if "." in host:
        try:
            socket.gethostbyname(host)
            return host_arg
        except socket.gaierror:
            pass

    for domain in config.domains:
        try:
            socket.gethostbyname(host + "." + domain)
            return host_arg + "." + domain
        except socket.gaierror:
            pass

    raise Exception(f'Host "{host}" is unreachable')


# Initiate the SSH session using the defined parameters
def ssh(args, config, domain):
    alt_user = False if domain.find("@") == -1 else True
    command = "ssh -o StrictHostKeyChecking=no -p " + args.port + " " + domain

    # Disable the use of keys for authentication
    if args.nopubkey:
        command = command + " -o PubkeyAuthentication=no"

    # Jumphosting causes problems with sshpass. So only use sshpass
    # if we are not jumphosting
    if args.jump or (args.jumphost != config.jump_host):
        command = command + " -J " + args.jumphost
    elif config.sshpass and not alt_user:
        command = "sshpass -e " + command

    # Open a dynamic port forward for socks5 proxy tunneling
    if args.tunnel:
        command = command + " -D " + config.tunnel_port

    return subprocess.run(command.split(), check=True)


def main():
    config = Config()
    args = arg_parser(config)

    try:
        domain = build_domain(args.host, config)
        ssh(args, config, domain)
    except KeyboardInterrupt:
        pass
    except subprocess.CalledProcessError:
        # print(e.returncode)
        pass
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
