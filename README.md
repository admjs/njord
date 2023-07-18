# Njord Python Package
## Overview
The njord python package provides a convenient wrapper to programmatically working with NordVPN servers on Mac/Linux via OpenVPN.

## Prerequisites
- `sudo`
- `openvpn`

Because njord relies on `sudo` and `openvpn`, it only works on OSX (including Apple silicone) and Linux. Linux is currently untested. Nord has an [official client](https://support.nordvpn.com/Connectivity/Linux/) that may better serve your needs on Linux. Windows isn't supported.

### Installing OpenVPN
#### OSX
`$ brew install openvpn`

#### Ubuntu
`$ sudo apt-get install openvpn`

## Installation

`$ pip install njord`

## Usage
#### Authentication
Authentication is handled via *service credentials*. Generate these via your Nord account at `Services > NordVPN > Manual Setup`

Copy the service credentials username and password. It's reccomended that you use a .env file for storing them. Njord will check for a .env file on initialization as well as os env variables. Authentication can also be done explicitly during init.



```
# .env
NORD_USER=xxxxxxxxxxxxx
NORD_PASSSWORD=xxxxxxxxxxx
```

```python
from njord import VPN

# Using .env file or os env
vpn = VPN()

# Explicit
vpn = VPN(user="xxxxxxxx", password="xxxxxxxxx")
```

#### Connecting & Disconnecting
``` python
from njord import VPN
vpn = VPN()
vpn.connect()
vpn.protected()
>> True
vpn.disconnect()
vpn.protected()
>> False
```

