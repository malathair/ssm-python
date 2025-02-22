# Simple SSH Manager

SSM is a small Python wrapper to simplify some common SSH use cases. It is essentially just a wrapper around OpenSSH's ssh command that builds and executes the ssh command for you from a simplified set of inputs.

## Gettings Started

### Prerequisites

 - Python3.11 or newer
 - uv or pipx
 - OpenSSH SSH client

### Installation

Install the application with uv or pipx using the following command:

```bash
uv tool install https://github.com/malathair/ssm/releases/download/v1.3.0/malathair_ssm-1.3.0-py3-none-any.whl
```

```bash
pipx install https://github.com/malathair/ssm/releases/download/v1.3.0/malathair_ssm-1.3.0-py3-none-any.whl
```

### Updating

To update, just run the uninstall command below and then re-install the most recent version. Any existing configuration files on the system will not be affected by this process.

If for some reason the format of the config changes in a breaking way, the new version will include a converter that will run the first time ssm is run on the system. The user will be notified if there are any current settings that are unable to be preserved duringt this process

### Configuration

ssm expects configuration files to exist at one of the following locations:

```bash
/usr/local/etc/ssm.conf

or

~/.config/ssm.conf
```

As of version 1.2.0, ssm now has it's default configuration hard coded into the application and will fall back to the defaults if no valid configuration files are found on the system.

If you would like to modify the configuration, you can either use the configuration utility provided by the package (recommended) or you can edit the config files manually (not recommended).

You can use the provided configuration utility by running:

```bash
ssmconf
```

### Uninstalling

Run one of the following to uninstall SSM (depending on which was used to install it):

```bash
uv tool uninstall malathair-ssm
```

```bash
pipx uninstall malathair-ssm
```


## Usage

### Basic

SSM’s main purpose is to eliminate the need to type out full URLs when accessing into remote systems. To that end, SSM implements a system to automatically detect and build valid URLs for you from minimal input.

SSM will detect if an IP was entered as the destination host rather than a URL. If so, it will attempt to connect to that IP directly with no further adjustments

If an IP is not detected, SSM will check to see if a valid URL was entered as the destination host

If the destination host is not an IP and does not resolve, then SSM assumes that it is a partial URL and will try to find a domain that resolves using the domains listed in the in the config file. It does this by combining the destination host with each domain in turn and then doing a DNS lookup to see if it resolves

As soon as a valid destination host is found, it then initiates an SSH connection to the destination. Domains are evaluated in the order they are listed in the config file so if the partial url provided would resolve on multiple domains, only the first will be used.

<details>
    <summary>Examples</summary>

    ssm 192.168.0.1: Connects directly to an IP (On the local network in this case, but public destinations work too)

    ssm user@192.168.0.1: Same as the pervious example but with an alternate username

    ssm fake.example.net: Connects directly to fake.example.net (bogus example domain) assuming it resolves

    ssm fake: Connects to fake.example.net again if the "example.net" domain is listed in the config file

    ssm user@fake: Same as the previous example but with an alternate user name

</details>

### Extended

SSM also provides a few additional argument flags for dealing with use cases that are a bit more niche but still happen on occasion. Each argument has a short and long version of the flag and you can use either. The flags SSM implements are as follows:

##### -h or --help

Prints the usage information of the program on the CLI for a quick reference if you need it. If used, SSM will only print the usage information of the program and exit ignoring all other provided arguments.

<details>
    <summary>Help Example</summary>

    ssm [-h] [-v] [-j | -J JUMPHOST] [-o] [-p PORT] [-t] host

    An SSH wrapper to simplify life

    positional arguments:
    host            Subdomain of the host's url or the host's IP address

    options:
    -h, --help      show this help message and exit
    -v, --version   show program's version number and exit

    -j, --jump      SSHs via the jump host specified in the configuration file
    -J, --jumphost  Overrides the jump host specified in the configuration file
    -o, --nopubkey  Disables the use of public keys for authentication. (Fixes authentication issues with certain devices)
    -p, --port      Specifies the port to use for the SSH session

    -t, --tunnel    Start a SOCKS5 tunnel on the port defined in the configuration file

</details>

##### -v or --version

Prints the version number of the currently installed SSM utility

##### -j or --jump

Routes the SSH connection to the destination host through an intermediate secondary host defined in the configuration file. This is useful for the odd situation where you need to access a site router that can’t be reached by the VPN for some reason. By default, the intermediate host is the Logan office router.

-J or --jumphost: This option allows you to override the intermediary host defined in the configuration file for a specific connection. This is useful for SSH’ing into equipment behind a site router without needing to interact with the CLI of said site router.

<details>
    <summary>Jumphost Examples</summary>

    Example command(s) using the default jumphost:

    ssm -j fake: Connects to fake.example.net by routing the connection through the jumphost defined in the configuration file

    ssm -j user@fake: Same as the previous command but with an alternate user

    Example command(s) using an alternate jumphost:

    ssm -J jump.example.net fake: Connects to fake.example.net by routing the connection through jump.example.net instead of the default jumphost

</details>

##### -o or --nopubkey

Disables the use of keys for the current command and forces the use of password authentication.

This fixes an issue that appears when logging in to certain devices where the use of password authentication is required but the underlying ssh command hangs after public keys are tried. This appears to stem from a compatilibity issue between newer versions of the openssh client and some ssh daemons that causes the openssh client to not fall back to password authentication after key authentication fails.

##### -p or --port

This option allows you to override the default SSH port defined in the configuration file for a specific connection. This is useful for infrequent situations where the port differs from the norm.

##### -t or --tunnel

This option creates a SOCKS tunnel on the SSH connection which allows you to forward TCP connections & traffic to a remote network as though you were on a local machine. This is useful for accessing services (like a web UI) on a device that would not normally not be accessible. It can also be leveraged to run scripts on remote networks where it would normally be impossible to do so. Running scripts over the SOCKS tunnel requires additional tools (like proxychains or tsocks) to redirect the traffic over the SOCKS tunnel as SSM does not handle that for you.

<details>
    <summary>Tunnel Examples</summary>

    Example command(s):

    ssm -t fake: Connects to fake.example.net and binds a SOCKS5 proxy server to port 6060 on localhost. By configuring your browser to use this proxy server you can access the Web UI of resources on the network behind the destination host. Additionally you can run commands as though you were using a machine on the remote network via a 3rd party command line tool like tsocks or proxychains which will redirect tcp traffic over the proxy tunnel.

</details>
