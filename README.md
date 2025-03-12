# PhilipsAirfryer
Python code I wrote to interact with my Philips 5000XXL Airfryer

> ### :warning: **I am not responsible for any damage caused by this program. For safe useage I recommend sending temperatures within the range of the device, and having the seconds parameter always be a multiple of 60.** :warning:

Airfryer_Loneclass.py is a file which has just the airfryer class, and does not need to be copied over to home assistant.
airfryer.py can be copied over to home assistant to use with your airfryer.

## Setup
- Get your `client_id` & `client_secret` by using a proxy
- Set up your router to give the Airfryer a static IP
- Install pyscript, add your settings (see example below) to Home Assistant's configuration.yaml and restart Home Assistant
  ```
  pyscript:
    allow_all_imports: true
    apps:
      airfryer:
        airfryer_ip: '192.168.29.94'
        client_id: 'JSm/eO5J8Mt0Q6MLiSqbYw=='
        client_secret: '0+QSOJzQEcj85/m31xaIeQ=='

  # NOT REQUIRED, but strongly reccomend so that the logbook is not filled with a refresh message every 20 sec
  logbook:
    exclude:
      domains:
        - pyscript
  ```
- airfryer.py => Download and move to /config/pyscript/
  
Basics based on https://github.com/noxhirsch/Pyscript-Philips-Airfryer
