"""
Implement a fancy config interface with remote updates
"""
#pylint: disable=bare-except,broad-except

import json
import http_grab

try:
    from machine import unique_id
    import ubinascii as binascii
except ImportError:
    from unix_machine import unique_id
    import binascii

class ConfigInterface:
    """
    Interface to stored config.

    The config is structured as a dictionary containing different nodes, identified
    by their machine.unique_id() (some kind of MAC)

    This config can be updated from a host, which should be done on startup of
    the node in order to always grab the newest config.

    In order to deploy config use a `p3 -m http.server` on port 8000 or a webserver
    on port 80 to grab the update.
    A list of possible hosts can be supplied.
    These can be for example hardcoded, the network gateway, or DNS hostnames
    (if there is working DNS on the network)

    example config for node id 4242:

    ```
    {"4242":{
        "section1": { "key1": 1 }
    }}
    ```

    access is done like that:

    assert config.config('section1', 'key1') == 1
    """

    URL = "/config.json"
    def __init__(self):
        identifier = binascii.hexlify(unique_id())
        self.client_id = identifier.decode('utf-8')
        self._config = None

    def config(self, section, key, dflt=None):
        """
        Grab a config section/key combination.
        If it does not exist, return dflt.
        """
        if section not in self._config[self.client_id]:
            return dflt
        return self._config[self.client_id][section].get(key, dflt)

    def default_config(self, section, key, dflt):
        """
        Check if there is a config stored on the host, read it, extract the
        requested value and destroy it again
        If the key could not be read or the config does not exist: return dflt
        """
        try:
            with open("config.json", "r") as cfgfile:
                config = json.loads(cfgfile.read())
        except:
            # any error while loading (such as file not found or decoding)
            # will lead to graceful abort
            return dflt

        if section not in config[self.client_id]:
            return dflt
        return config[self.client_id][section].get(key, dflt)

    def ready(self):
        """
        Check if the config has been initialized
        """
        return self._config is not None


    def getconfig(self, known_hosts):
        """
        Try to grab the config from the list of known hosts
        use ports 8000 and 80 for deloyment
        """
        for host in known_hosts:
            try:
                if ":" in host:
                    host, port = host.split(":", 1)
                    if self.getconfig_from_host(host, port):
                        return True
                else:
                    for port in [8000, 80]:
                        if self.getconfig_from_host(host, port):
                            return True
            except ValueError:
                print("Config encoding was bad")

        # we have exhausted remote configs
        try:
            with open("config.json", "r") as cfgfile:
                config = json.loads(cfgfile.read())
        except:
            print("[!] Fallback config failed. will now reset.")
            raise
        if self._check_config(config):
            self._config = config
            print("[*] loading fallback local config was successful")
            return True
        return False


    def getconfig_from_host(self, host, port):
        """
        Request the config from the given host, check if for validity and store
        it locally if it was nice
        """
        config = {}
        try:
            print("[-]    trying http://%s:%i%s"%(host, port, self.URL))

            resp = http_grab.get(host, port, self.URL)

            print(resp)
            if not resp:
                return False

            #decodeError is cought outside
            config = json.loads(resp)
            if config:
                # compare with local config.json
                config_changed = True
                try:
                    with open("config.json", "r") as cfgfile:
                        if cfgfile.read() == resp:
                            config_changed = False
                except OSError:
                    # no config there, so write an update
                    config_changed = True
        except OSError as err:
            print("[!] config host %s:%d is not available: %s"%(host, port, err))
            return False

        if self._check_config(config):
            self._config = config
            self._config[self.client_id]['host'] = {'name': host}
            if config_changed:
                print("[*] config changed, storing it for later use")
                self._write_config(config)
            return True
        return False


    def _write_config(self, config):
        """
        Store the config to the local filesystem
        """
        try:
            with open("config.json", "w+") as cfgfile:
                to_store = {
                    self.client_id: config[self.client_id]
                }
                cfgfile.write(json.dumps(to_store))
        except OSError as err:
            print("[!] Config write failed: ", err)


    def _check_config(self, config):
        """
        check if the config is viable
        """
        # test the config
        if not isinstance(config, dict):
            print("Config is not dict")
            return False

        if self.client_id not in config:
            print("My client id %s is not in config"%self.client_id)
            return False

        return True
