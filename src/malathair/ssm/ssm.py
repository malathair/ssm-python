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

    # Override the default max_help_position value. It will now default to 32 instead
    # of 24. Some of the flags are a bit long and this just makes the output a tad nicer
    def __init__(self, prog, indent_increment=2, max_help_position=32, width=None):
        super().__init__(prog, indent_increment, max_help_position, width)

    # Override default format_help() method to fix some capitalization
    def format_help(self):
        return (
            super()
            .format_help()
            .replace("options:", "Options:")
            .replace("positional arguments:", "Positional Arguments:")
        )

    # Override default _format_action() method to force a linebreak between all arguments
    # regardless of section, because walls of text are hard to read
    def _format_action(self, action):
        return super()._format_action(action) + "\n"

    # Backport Python3.13 action formatting behavior to older python versions
    # i.e. use this:   -s, --long ARGS
    # instead of this: -s ARGS, --long ARGS
    def _format_action_invocation(self, action):
        if not action.option_strings:
            return super()._format_action_invocation(action)

        default = self._get_default_metavar_for_optional(action)
        args_string = self._format_args(action, default)
        return ", ".join(action.option_strings) + " " + args_string


# Define CLI arguments for the program
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
        description=(
            "An SSH wrapper to simplify life. Privdes shortcuts for common SSH flags, "
            "dynamic dns name completion based on a configurable list of domains, and "
            "password autofill via sshpass"
        ),
        formatter_class=HelpFormatter,
    )

    jump = parser.add_mutually_exclusive_group()

    parser.add_argument(
        "host",
        type=str,
        help=(
            "The host's IP address or the host portion of it's FQDN. When a value is provided "
            'that does not contain a ".", SSM assumes the host portion of an FQDN was provided '
            "and will attempt to autocomplete the full FQDN using the configured list of domains"
        ),
    )

    parser.add_argument(
        "-c",
        "--command",
        type=str,
        help=(
            "Execute the specified command on the remote system without opening an interactive "
            "shell. The connection will be terminated immediately after command executes. "
            "The [-t, --tunnel] flag will be ignored if this option is used"
        ),
    )

    jump.add_argument(
        "-j",
        "--jump",
        action="store_true",
        help=(
            "SSH's via the jump host specified in the configuration file. Cannot be used with "
            "the [-J, --jumphost] flag"
        ),
    )

    jump.add_argument(
        "-J",
        "--jumphost",
        type=str,
        help=(
            "Overrides the jump host specified in the configuration file. Cannot be used with "
            "the [-j, --jump] flag"
        ),
    )

    parser.add_argument(
        "-o",
        "--nopubkey",
        action="store_true",
        help=(
            "Disables the use of public keys for authentication. Fixes authentication "
            "issues with certain devices that fast fail ssh connection attempts when an "
            'invalid key is tried. Works by setting SSH\'s "PubkeyAuthentication" option to "no"'
        ),
    )

    parser.add_argument(
        "-p",
        "--port",
        default=config.ssh_port,
        type=str,
        help="Specifies the port to use for the SSH session. Defaults to 22",
    )

    parser.add_argument(
        "-t",
        "--tunnel",
        action="store_true",
        help=(
            "Start a SOCKS5 tunnel on the port defined in the configuration file. You may then "
            "use a SOCKS5 proxy config in your browser, or a SOCKS5 proxy client like tsocks or "
            "proxychains to proxy tcp traffic through the SOCKS5 tunnel. This flag has no effect "
            "when using the [-c, --command] flag to execute a remote command over SSH"
        ),
    )

    parser.add_argument("-V", "--version", action="version", version=VERSION)

    parser.add_argument(
        "-v",
        action="count",
        help=(
            "Print verbose debug messages about the SSH connection. Multiple -v"
            "options increase the verbosity up to a maximum of 3 (-vvv)"
        ),
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
            socket.getaddrinfo(host, 0)
            return host_arg
        except socket.gaierror:
            pass

    for domain in config.domains:
        try:
            socket.getaddrinfo(host + "." + domain, 0)
            return host_arg + "." + domain
        except socket.gaierror:
            pass

    raise Exception(f'Host "{host}" is unreachable')


# Initiate the SSH session using the defined parameters
def ssh(args, config, domain):
    alt_user = False if domain.find("@") == -1 else True
    openssh_command = ["ssh", "-p", args.port]

    # Add verbosity levels
    if args.v:
        multiplier = args.v if args.v < 4 else 3
        openssh_command.append("-" + "v" * multiplier)

    # Add SSH options
    openssh_command.extend(["-o", "StrictHostKeyChecking=no"])
    # Disable the use of keys for authentication
    if args.nopubkey:
        openssh_command.extend(["-o", "PubkeyAuthentication=no"])

    # Jumphosting causes problems with sshpass. So only use sshpass if we are not jumphosting
    if args.jump:
        openssh_command.extend(["-J", config.jump_host])
    elif args.jumphost:
        openssh_command.extend(["-J", args.jumphost])
    elif config.sshpass and not alt_user:
        openssh_command[:0] = ["sshpass", "-e"]

    # Open a dynamic port forward for socks5 proxy tunneling
    if args.command:
        openssh_command.extend(["-c", args.command])
    elif args.tunnel:
        openssh_command.extend(["-D", config.tunnel_port])

    openssh_command.append(domain)

    # print(openssh_command)
    return subprocess.run(openssh_command, check=True)


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
