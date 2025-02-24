import base64
import hashlib
import requests
import json

class Airfryer:
    """Airfryer Philips 5000 XXL"""
    def __init__(self, ip: str, client_id: str, client_secret: str, command_url: str = '/di/v1/products/1/airfryer') -> None:
        """Initialize the Airfryer object.
        Args:
            ip (str): IP address of the airfryer.
            client_id (str): Client ID of the airfryer.
            client_secret (str): Client Secret of the airfryer.
            command_url (str): Command URL of the airfryer. [/di/v1/products/1/airfryer]"""
        requests.packages.urllib3.disable_warnings() # Disable Certificate warning for HTTPS
        self.ip = ip
        self.client_id = client_id
        self.client_secret = client_secret
        self.command_url = command_url
        self.session = requests.Session()
        
        try:
            response = self.session.get(f'https://{self.ip}{self.command_url}', headers={"User-Agent":"cml","Content-Type":"application/json"}, verify=False, timeout=10)
        except:
            raise ConnectionError('Could not connect to the airfryer [Probably Offline]')
        
        if response.status_code != 401:
            raise ConnectionError(f'Could not connect to the airfryer [Status code: {response.status_code}]')
        else:
            challenge = response.headers.get("WWW-Authenticate")
            challenge = challenge.replace('PHILIPS-Condor ', '')
            self.token = self._getAuth(challenge)
 
    def __str__(self) -> str:
        return str(self.get_status())
        
    def __repr__(self) -> str:
        return self.__str__() 
        
    def _decode(self, txt: str) -> bytes:
        """Decode base64 string. 
        [Meant for internal use only]
        """
        return base64.standard_b64decode(txt)
    
    def _getAuth(self, challenge: str) -> str:
        """Generate the Authorization header value. 
        [Meant for internal use only]
        """
        vvv = self._decode(challenge) + self._decode(self.client_id) + self._decode(self.client_secret)
        hash = hashlib.sha256(vvv).hexdigest()
        hashhex = bytes.fromhex(hash)
        result = self._decode(self.client_id) + hashhex
        encoded = base64.b64encode(result)
        return encoded.decode('ascii')
    
    def _send_command(self, command: dict) -> dict | int:
        """Send a command to the airfryer.
        Args:
            command (str): Command to send.
        Returns:
            tuple: Response from the airfryer.
            0: Airfryer is offline.
        [Meant for internal use only]
        """
        
        json_data = json.dumps(command, separators=(',', ':'))
        headers = {"User-Agent":"okhttp/4.12.0","Content-Type":"application/json; charset=utf-8","Content-Length":str(len(json_data)),"Authorization":"PHILIPS-Condor "+self.token}

        try:
            response = self.session.put(f'https://{self.ip}{self.command_url}', headers=headers, data=json_data, verify=False, timeout=10)
        except requests.exceptions.RequestException as e:
            return 0
        
        if response.status_code != 200:
            return 0
        else:
            return response.json()

    def get_status(self) -> dict | int:
        """Get the status of the airfryer.
        Returns:
            dict: Status of the airfryer.
            0: Airfryer is offline.
        """
        try:
            response = self.session.get(f'https://{self.ip}{self.command_url}', headers={"User-Agent":"cml","Content-Type":"application/json","Authorization":"PHILIPS-Condor "+self.token}, verify=False, timeout=10)
        except requests.exceptions.RequestException as e:
            return 0
        
        if response.status_code == 401:
            """Since get_status is meant to be called every so often,
            this is a recovery function.
            
            Where the device to get disconnected,
            this will re-find and set the token.
            """
            challenge = response.headers.get("WWW-Authenticate")
            challenge = challenge.replace('PHILIPS-Condor ', '')
            self.token = self._getAuth(challenge)
            return self.get_status()
        elif response.status_code != 200:
            return 0
        else:
            return response.json()

    def turn_on(self) -> dict | int:
        """Turn on the airfryer.
        Returns:
            dict: Status of the airfryer.
            0: Airfryer is offline.
            1: Airfryer is not in standby mode.
        """
        cur_status = self.get_status()
        if cur_status == 0:
            return 0
        elif cur_status['status'] == 'standby':
            status = self._send_command({"status":"setting"})
            return status
        else:
            return 1
    
    def turn_off(self) -> dict | int:
        """Turn off the airfryer.
        Returns:
            dict: Status of the airfryer.
            0: Airfryer is offline.
            1: Airfryer already in standby mode.
        """
        cur_status = self.get_status()
        if cur_status == 0:
            return 0
        elif cur_status['status'] == 'standby':
            return 1
        elif cur_status['status'] == 'cooking':
            self._send_command({"status":"pause"})
        
        status = self._send_command({"status":"standby"})
        return status
    
    def settings(self, temp_c: int, time_sec: int) -> dict | int:
        """Set the temperature and time of the airfryer.
        Args:
            temp_c (int): Temperature in Celsius.
            time_sec (int): Time in seconds.
        Returns:
            dict: Status of the airfryer.
            0: Airfryer is offline.
            1: Airfryer is in standby mode.
        """
        cur_status = self.get_status()
        if cur_status == 0:
            return 0
        elif cur_status['status'] == 'standby':
            return 1
        elif cur_status['status'] == 'cooking':
            self._send_command({"status":"pause"})
        status = self._send_command({"temp": temp_c ,"preset": 0, "time": time_sec, "status":"setting","temp_unit":False})
        return status
    
    def start_cooking(self) -> dict | int:
        """Start cooking in the airfryer.
        Returns:
            dict: Status of the airfryer.
            0: Airfryer is offline.
            1: Airfryer is in standby mode.
            2: Airfryer is already cooking.
            3: Airfryer is in an unknown state.
        """
        cur_status = self.get_status()
        if cur_status == 0:
            return 0
        elif cur_status['status'] == 'standby':
            return 1
        elif cur_status['status'] == 'cooking':
            return 2
        elif cur_status['status'] in ['setting', 'pause', 'idle']:
            status = self._send_command({"status":"cooking"})
            return status
        else:
            return 3
        
    def pause_cooking(self) -> dict | int:
        """Pause cooking in the airfryer.
        Returns:
            dict: Status of the airfryer.
            0: Airfryer is offline.
            1: Airfryer is not cooking.
        """
        cur_status = self.get_status()
        if cur_status == 0:
            return 0
        elif cur_status['status'] == 'cooking':
            status = self._send_command({"status":"pause"})
            return status
        else:
            return 1
    
    def finish_cooking(self) -> dict | int:
        """Finish cooking in the airfryer.
        Returns:
            dict: Status of the airfryer.
            0: Airfryer is offline.
            1: Airfryer is not cooking nor paused.
        """
        cur_status = self.get_status()
        if cur_status == 0:
            return 0
        elif cur_status['status'] == 'cooking':
            self._send_command({"status":"pause"})
            status = self._send_command({"status":"finish"})
            return status
        elif cur_status['status'] == 'pause':
            status = self._send_command({"status":"finish"})
            return status
        else:
            return 1
        
    def keep_warm(self, time_sec: int) -> dict | int:
        """Keep the airfryer warm.
        Args:
            time_sec (int): Time in seconds.
        Returns:
            dict: Status of the airfryer.
            0: Airfryer is offline.
            1: Airfryer is not in a suitable state.
        """
        cur_status = self.get_status()
        if cur_status == 0:
            return 0
        elif cur_status['status'] in ['finish', 'setting', 'idle']:
            self._send_command({"preset": 8, "status":"setting", "temp_unit": False})
            self._send_command({"temp": 80, "temp_unit": False, "time": time_sec})
            status = self._send_command({"temp": 80, "preset": 8, "time": time_sec, "status":"cooking"})
            return status
        else:
            return 1

# Please give your airfryer a static IP address.
# af = Airfryer('192.168.XXX.YYY', 'XXXXXXXXXXXXXXXXXXXXXX==', 'XXXXXXXXXXXXXXXXXXXXXX==')