import requests
import subprocess
import tempfile
import signal
import os
import random
import psutil
from time import sleep
from typing import Optional, Tuple, List, Dict, Union
from ._templates import OPENVPN_TEMPLATE
from dotenv import load_dotenv

load_dotenv()

class VPN:
    """
    A Python class for programmatically controlling and managing connections to NordVPN.
    """
    def __init__(self, user: str="", password: str=""):
        """
        Initialize the VPN with given user credentials or read those set in the OS env or .env file.

        user: looks for NORD_USER in env
        password: looks for NORD_PASSWORD in env
        """
        self.OPENVPN_PID: Optional[int] = None
        self.auth_user: str = user if user else os.getenv("NORD_USER")
        self.auth_password: str = password if password else os.getenv("NORD_PASSWORD")
        self.config_file: Optional[str] = None
        self.auth_file: Optional[str] = None


    def fetch_server_info(self) -> Optional[Tuple[str, str]]:
        """
        Fetch information about a randomly recommended server that supports OpenVPN.
        """

        url = "https://api.nordvpn.com/v1/servers/recommendations?filters&limit=30"
        response = requests.get(url)
        response_json = response.json()
        servers = [server for server in response_json if any(tech["name"] == "OpenVPN TCP" for tech in server["technologies"])]
        random_server = random.choice(servers) if servers else None
        return (random_server["hostname"], random_server["station"]) if random_server else None

    def list_countries(self) -> List[Dict[str, Union[str, int]]]:
        """
        Fetch a list of all available server countries from the NordVPN API.
        """
        url = "https://api.nordvpn.com/v1/servers/countries"
        response = requests.get(url)
        return response.json()
        
    
    def status(self) -> dict:
        url = "https://nordvpn.com/wp-admin/admin-ajax.php?action=get_user_info_data"
        response = requests.get(url)
        return response.json()
    
    def protected(self) -> bool:
        status = self.status()
        if status.get("status") == True:
            return True
        else:
            return False

    def connect(self) -> None:
        """
        Connect to a random reccomended NordVPN server.
        """
        if self.OPENVPN_PID:
            self.disconnect()

        hostname, ip = self.fetch_server_info()

        file_content = OPENVPN_TEMPLATE.format(ip, hostname)
        self.config_file = os.path.join(tempfile.gettempdir(), os.urandom(24).hex())

        with open(self.config_file, "w") as file:
            file.write(file_content)

        self.auth_file = os.path.join(tempfile.gettempdir(), os.urandom(16).hex())

        with open(self.auth_file, "w") as file:
            file.write(f"{self.auth_user}\n{self.auth_password}")
        
        self.openvpn = subprocess.Popen(
            ["openvpn","--config", self.config_file,"--auth-user-pass", self.auth_file], 
            shell=False, 
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT
            )
        self.OPENVPN_PID = self.openvpn.pid

        count = 0
        while count < 5:
            if self.protected():
                print(f"Protected and connected to {hostname}")
                return
            else:
                # Check that the process is still running
                if self.openvpn.poll() is None:
                    print(f"Connecting to {hostname}...")
                    count+=1
                    sleep(5)
                else:
                    break

        self.connect()

    def flush(self) -> None:
        """Terminate all running OpenVPN processes."""
        for proc in psutil.process_iter(attrs=["name", "pid"]):
            if proc.info["name"] == "openvpn":
                os.kill(proc.info["pid"], 9)

    def disconnect(self) -> None:
        """
        Disconnect from the current server and clean up any open connections and temporary files.
        """
        if self.OPENVPN_PID:
            os.kill(self.OPENVPN_PID, signal.SIGTERM)
            self.OPENVPN_PID = None

        if self.config_file:
            os.remove(self.config_file)
            self.config_file = None

        if self.auth_file:
            os.remove(self.auth_file)
            self.auth_file = None

        self.flush()