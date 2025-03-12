import base64
import hashlib
import requests
import json

config = pyscript.config.get('apps').get('airfryer')
if config == None:
    log.error("############### Airfryer: No config found. Please check the documentation! ###############")
    airfryer_ip        = ""
    client_id          = ""
    client_secret      = ""
    command_url        = '/di/v1/products/1/airfryer'
    update_interval    = '86400sec'
else:
    airfryer_ip        = config.get('airfryer_ip')
    client_id          = config.get('client_id')
    client_secret      = config.get('client_secret')
    command_url        = config.get('command_url', '/di/v1/products/1/airfryer')
    update_interval    = config.get('update_interval', '20sec')

state.persist('pyscript.airfryer_time', 0, default_attributes={'unit_of_measurement':'S'})
state.persist('pyscript.airfryer_time_min', 0, default_attributes={'unit_of_measurement':'Min'})
state.persist('pyscript.airfryer_cur_time', 0, default_attributes={'unit_of_measurement':'S'})
state.persist('pyscript.airfryer_cur_time_min', 0, default_attributes={'unit_of_measurement':'Min'})
state.persist('pyscript.airfryer_temp', 0, default_attributes={'unit_of_measurement':'°C'})
state.persist('pyscript.airfryer_temp_unit', False)
state.persist('pyscript.airfryer_drawer_open', "Closed")
state.persist('pyscript.airfryer_preset', 0)
state.persist('pyscript.airfryer_error', 0)
state.persist('pyscript.airfryer_prev_status', 'Offline')
state.persist('pyscript.airfryer_status', 'Offline')
state.persist('pyscript.airfryer_step_id', '')
state.persist('pyscript.airfryer_recipe_id', '')
state.persist('pyscript.airfryer_shaker_reminder_active', False)


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
            response = task.executor(self.session.get, f'https://{self.ip}{self.command_url}', headers={"User-Agent":"cml","Content-Type":"application/json"}, verify=False, timeout=10)
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
            response = task.executor(self.session.put, f'https://{self.ip}{self.command_url}', headers=headers, data=json_data, verify=False, timeout=10)
            # response = self.session.put(f'https://{self.ip}{self.command_url}', headers=headers, data=json_data, verify=False, timeout=10)
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
            response = task.executor(self.session.get, f'https://{self.ip}{self.command_url}', headers={"User-Agent":"cml","Content-Type":"application/json","Authorization":"PHILIPS-Condor "+self.token}, verify=False, timeout=10)
            # response = self.session.get(f'https://{self.ip}{self.command_url}', headers={"User-Agent":"cml","Content-Type":"application/json","Authorization":"PHILIPS-Condor "+self.token}, verify=False, timeout=10)
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
            4: Airfryer drawer is open.
        """
        cur_status = self.get_status()
        if cur_status == 0:
            return 0
        elif cur_status['status'] == 'standby':
            return 1
        elif cur_status['status'] == 'cooking':
            return 2
        elif cur_status['drawer_open'] == True:
            return 4
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

def set_entities(response):
    if response == "offline":
        pyscript.airfryer_time = 0
        pyscript.airfryer_time_min = 0
        pyscript.airfryer_cur_time = 0
        pyscript.airfryer_cur_time_min = 0
        pyscript.airfryer_temp = 0
        pyscript.airfryer_temp_unit = False
        pyscript.airfryer_drawer_open = "Closed"
        pyscript.airfryer_preset = 0
        pyscript.airfryer_error = 0
        pyscript.airfryer_prev_status = 'Offline'
        pyscript.airfryer_status = 'Offline'
        pyscript.airfryer_step_id = ''
        pyscript.airfryer_recipe_id = ''
        pyscript.airfryer_shaker_reminder_active = False

    else:
        pyscript.airfryer_time = response.get('time', 0) if response.get('status', '') in ['cooking', 'pause', 'finish', 'setting'] else 0
        pyscript.airfryer_time_min = -(-response.get('time', 0) // 60) if response.get('status', '') in ['cooking', 'pause', 'finish', 'setting'] else 0
        pyscript.airfryer_cur_time = response.get('cur_time', 0) if response.get('status', '') in ['cooking', 'pause'] else 0
        pyscript.airfryer_cur_time_min = -(-response.get('cur_time', 0) // 60) if response.get('status', '') in ['cooking', 'pause'] else 0
        pyscript.airfryer_temp = response.get('temp', 0) if response.get('status', '') in ['cooking', 'pause', 'finish', 'setting'] else 0
        pyscript.airfryer_temp_unit = response.get('temp_unit', False)
        pyscript.airfryer_drawer_open = "Open" if bool(response.get('drawer_open', False)) == True else "Closed"
        pyscript.airfryer_preset = response.get('preset', 0)
        pyscript.airfryer_error = response.get('error', 0)
        pyscript.airfryer_prev_status = str(response.get('prev_status', '')).title()
        pyscript.airfryer_status = str(response.get('status', '')).title()
        pyscript.airfryer_step_id = response.get('step_id', '')
        pyscript.airfryer_recipe_id = response.get('recipe_id', '')
        pyscript.airfryer_shaker_reminder_active = response.get('shaker_reminder_active', False)

try:
    af = Airfryer(airfryer_ip, client_id, client_secret, command_url)
except ConnectionError as e:
    log.error(f"Failed to initialize Airfryer: {e}")
    set_entities("offline")
    af = None
requests.packages.urllib3.disable_warnings()

@service
@time_trigger("startup", f"period(now, {update_interval})")
def airfryer_sensors_update():
    """yaml
    name: Airfryer Sensors Update
    description: Updates the Airfryer sensors.
    """
    global af
    if af is None:
        try:
            af = Airfryer(airfryer_ip, client_id, client_secret, command_url)
        except ConnectionError as e:
            log.error(f"Failed to initialize Airfryer: {e}")
            set_entities("offline")
            af = None
    else:
        response = af.get_status()
        if not isinstance(response, int):
            set_entities(response)
        elif response == 0:
            set_entities("offline")


@service
def airfryer_turn_on():
    """yaml
    name: Airfryer Turn On
    description: Turns the Airfryer on (into settings).
    """
    global af
    if af is not None:
        response = af.turn_on()
        if not isinstance(response, int):
            set_entities(response)
        elif response == 0:
            set_entities("offline")
        elif response == 1:
            log.info("Airfryer is not in standby mode.")


@service
def airfryer_turn_off():
    """yaml
    name: Airfryer Turn Off
    description: Turns the Airfryer off (and stops it before if needed).
    """
    global af
    if af is not None:
        response = af.turn_off()
        if not isinstance(response, int):
            set_entities(response)
        elif response == 0:
            set_entities("offline")
        elif response == 1:
            log.info("Airfryer is already in standby mode.")
            set_entities(response)


@service
def airfryer_settings(temp_c, time_min):
    """yaml
    name: Airfryer Settings
    description: Sets the temperature and time for the Airfryer (if not cooking).
    fields:
        temp_c:
            description: Cooking temperature (steps of 5 degrees C)
            name: Temperature
            example: 180
            required: true
            selector:
                number:
                    min: 40
                    max: 200
                    mode: box
                    unit_of_measurement: "°C"
        time_min:
            description: Cooking duration in minutes
            name: Total Time
            example: 600
            required: true
            selector:
                number:
                    min: 1
                    max: 180
                    mode: box
                    unit_of_measurement: min
    """
    global af
    if af is not None:
        response = af.settings(temp_c, time_min*60)
        if not isinstance(response, int):
            set_entities(response)
        elif response == 0:
            set_entities("offline")
        elif response == 1:
            log.info("Airfryer is in standby mode.")
            set_entities(response)

@service
def airfryer_pause():
    """yaml
    name: Airfryer Pause
    description: Pauses the Airspeed.
    """
    global af
    if af is not None:
        response = af.pause_cooking()
        if not isinstance(response, int):
            set_entities(response)
        elif response == 0:
            set_entities("offline")
        elif response == 1:
            log.info("Airfryer is not cooking.")
            set_entities(response)


@service
def airfryer_start_resume():
    """yaml
    name: Airfryer Start/Resume
    description: Startes the Airfryer if everything is set up or resumes if paused.
    """
    global af
    if af is not None:
        response = af.start_cooking()
        if not isinstance(response, int):
            set_entities(response)
        elif response == 0:
            set_entities("offline")
        elif response == 1:
            log.info("Airfryer is in standby mode.")
            set_entities(response)
        elif response == 2:
            log.info("Airfryer is already cooking.")
            set_entities(response)
        elif response == 3:
            log.info("Airfryer is in an unknown state.")
            set_entities(response)
        elif response == 4:
            log.info("Airfryer drawer is open.")
            set_entities(response)


@service
def airfryer_stop():
    """yaml
    name: Airfryer Stop
    description: Stops the Airfryer and returns to main menu.
    """
    global af
    if af is not None:
        response = af.finish_cooking()
        if not isinstance(response, int):
            set_entities(response)
        elif response == 0:
            set_entities("offline")
        elif response == 1:
            log.info("Airfryer is not cooking nor paused.")
            set_entities(response)

@service
def airfryer_keep_warm(time_min):
    """yaml
    name: Airfryer Keep Warm
    description: Keeps the Airfryer warm for a given time.
    fields:
        time_min:
            description: Time in minutes
            name: Time
            example: 10
            selector:
                number:
                    min: 1
                    max: 180
                    mode: box
                    unit_of_measurement: min
    """
    global af
    if af is not None:
        response = af.keep_warm(time_min*60)
        if not isinstance(response, int):
            set_entities(response)
        elif response == 0:
            set_entities("offline")
        elif response == 1:
            log.info("Airfryer is not in a suitable state.")
            set_entities(response)