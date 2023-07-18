import os
import random
import subprocess
import tempfile
from time import sleep
from typing import Dict, List, Optional, Tuple, Union

import psutil
import requests
from dotenv import load_dotenv

load_dotenv()

from ._templates import OPENVPN_TEMPLATE


class Client:
    BASE_API_URL: str = "https://api.nordvpn.com/v1"
    STATUS_API_URL: str = (
        "https://nordvpn.com/wp-admin/admin-ajax.php?action=get_user_info_data"
    )

    def __init__(self, user: str = "", password: str = "") -> None:
        """
        Initialize the VPN with given user credentials.
        Fall back to OS environment variables or .env file.

        :param user: looks for NORD_USER in env
        :param password: looks for NORD_PASSWORD in env
        """
        self.OPENVPN_PID: Optional[int] = None
        self.auth_user: str = user or os.getenv("NORD_USER", "")
        self.auth_password: str = password or os.getenv("NORD_PASSWORD", "")
        self.config_file: Optional[str] = None
        self.auth_file: Optional[str] = None
        self.connection_retries: int = 0

    def fetch_server_info(self) -> Optional[Tuple[str, str]]:
        """
        Fetch information about a randomly recommended server that supports OpenVPN.
        """
        url = f"{self.BASE_API_URL}/servers/recommendations?filters&limit=30"
        response = requests.get(url)
        response_json = response.json()
        servers = [
            server
            for server in response_json
            if any(tech["name"] == "OpenVPN TCP" for tech in server["technologies"])
        ]
        random_server = random.choice(servers) if servers else None
        return (
            (random_server["hostname"], random_server["station"])
            if random_server
            else None
        )

    def list_countries(self) -> List[Dict[str, Union[str, int]]]:
        """
        Fetch a list of all available server countries from the NordVPN API.
        """
        url = f"{self.BASE_API_URL}/servers/countries"
        response = requests.get(url)
        return response.json()

    def status(self) -> dict:
        response = requests.get(self.STATUS_API_URL)
        return response.json()

    def is_protected(self) -> bool:
        status = self.status()
        return status.get("status", False) is True

    def connect(self, max_retries: int = 5) -> bool:
        """
        Connect to a random recommended NordVPN server.

        :param max_retries: int - the number of times the client will attempt to connect before returning an error
        """
        subprocess.run(["sudo", "-v"])
        self.disconnect()

        server_info = self.fetch_server_info()
        if server_info is None:
            return False
        hostname, ip = server_info

        file_content = OPENVPN_TEMPLATE.format(ip, hostname)
        self.config_file = os.path.join(tempfile.gettempdir(), os.urandom(24).hex())
        self.auth_file = os.path.join(tempfile.gettempdir(), os.urandom(16).hex())

        with open(self.config_file, "w") as file:
            file.write(file_content)

        with open(self.auth_file, "w") as file:
            file.write(f"{self.auth_user}\n{self.auth_password}")

        self.openvpn = subprocess.Popen(
            [
                "sudo",
                "openvpn",
                "--config",
                self.config_file,
                "--auth-user-pass",
                self.auth_file,
            ],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        self.OPENVPN_PID = self.openvpn.pid

        sleep(5)
        if self.is_protected():
            print(f"Connected to {hostname}")
            self.connection_retries = 0
            return True
        elif self.connection_retries < max_retries:
            print(f"Connection failed - retrying")
            self.connection_retries += 1
            self.connect()
        else:
            raise Exception("Couldn't connect, check credentials.")

    def flush(self) -> None:
        """
        Terminate all running OpenVPN processes.
        """
        for proc in psutil.process_iter(attrs=["name", "pid"]):
            if proc.info["name"] == "openvpn":
                os.system("sudo kill -9 " + str(proc.info["pid"]))

    def disconnect(self) -> None:
        """
        Disconnect from the current server and clean up any open connections and temporary files.
        """
        if self.OPENVPN_PID:
            os.system("sudo kill -9 " + str(self.OPENVPN_PID))
            self.OPENVPN_PID = None

        if self.config_file:
            os.remove(self.config_file)
            self.config_file = None

        if self.auth_file:
            os.remove(self.auth_file)
            self.auth_file = None

        self.flush()
