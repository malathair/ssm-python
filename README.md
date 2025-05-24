# Simple SSH Manager

SSM is a small Python wrapper to simplify some common SSH use cases. It is essentially just a wrapper around OpenSSH's ssh command that builds and executes the ssh command for you from a simplified set of inputs.

## Gettings Started

### Prerequisites

 - Python3.11 or newer, but Python3.13 is recommended
 - uv or pipx
 - OpenSSH SSH client

### Installation

Install the application with uv or pipx using the following command:

```bash
uv tool install git+https://github.com/malathair/ssm
```

```bash
pipx install git+https://github.com/malathair/ssm
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
