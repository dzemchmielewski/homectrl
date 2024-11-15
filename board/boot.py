import webrepl, time, machine
from board.configuration import Configuration


class Boot:

    loaded = {
        'wifi': False,
        'time': False,
        'webrepl': False
    }
    led_pattern = [0.5, 0.3, 0.2, 0.2, 0.1, 0.1, 0.1, 0.05, 0.05]
    instance = None

    @classmethod
    def get_instance(cls, led_notify=True):
        if not cls.instance:
            cls.instance = Boot(led_notify)
        return cls.instance

    def __init__(self, led_notify=True):
        self.led_notify = led_notify
        self.wifi = None
        self.led_pin = machine.Pin(8, machine.Pin.OUT) if self.led_notify else None

    def led_notification(self, reverse=False, turn_off = None):
        if self.led_notify:
            if turn_off:
                self.led_pin.value(1)
            else:
                for sleep in (self.led_pattern[::-1] if reverse else self.led_pattern):
                    for signal in [1, 0]:
                        self.led_pin.value(signal)
                        time.sleep(sleep)

    def setup_wifi(self):
        if not self.wifi:
            import network
            network.country("PL")
            self.wifi = network.WLAN(network.STA_IF)

        self.wifi.active(True)
        self.wifi.disconnect()

        while not self.wifi.isconnected():
            timeout = 30000
            self.led_notification()
            self.wifi.connect(Configuration.WIFI_SSID, Configuration.WIFI_PASSWORD)
            while timeout > 0:
                if not self.wifi.isconnected():
                    time.sleep_ms(200)
                    timeout = timeout - 200
                else:
                    break
            if timeout <= 0:
                self.led_notification(reverse=True)

        self.led_notification(turn_off=True)
        print("Connected! ifconfig: {}".format(self.wifi.ifconfig()))

    @staticmethod
    def setup_webrepl():
        webrepl.start(password=Configuration.WEBREPL_PASSWORD)

    @staticmethod
    def setup_time():
        import ntptime
        ntptime.host='status.home'

        now = ntptime.time()

        year = time.gmtime(now)[0]       #get current year
        hh_march   = time.mktime((year,3 ,(31-(int(5*year/4+4))%7),1,0,0,0,0,0)) # Time of March change to CEST
        hh_october = time.mktime((year,10,(31-(int(5*year/4+1))%7),1,0,0,0,0,0)) # Time of October change to CET

        if now < hh_march :               # we are before last sunday of march
            cet = time.localtime(now+3600) # CET:  UTC+1H
        elif now < hh_october :           # we are before last sunday of october
            cet = time.localtime(now+7200) # CEST: UTC+2H
        else:                            # we are after last sunday of october
            cet = time.localtime(now+3600) # CET:  UTC+1H

        (year, month, mday, hour, minute, second, weekday, yearday) = cet
        machine.RTC().datetime((year, month, mday, 0, hour, minute, second, 0))

    def load(self):
        if not self.loaded['wifi']:
            try:
                self.setup_wifi()
                self.loaded['wifi'] = True
            except Exception as e:
                print("FAILED to load wifi: {}".format(e))

        if not self.loaded['webrepl']:
            try:
                self.setup_webrepl()
                self.loaded['webrepl'] = True
            except Exception as e:
                print("FAILED to load webrepl: {}".format(e))

        if not self.loaded['time']:
            try:
                self.setup_time()
                self.loaded['time'] = True
            except Exception as e:
                print("FAILED to load time: {}".format(e))

    @staticmethod
    def start_server(worker):
        from board.worker import WorkerServer
        from common.communication import SocketCommunication
        try:
            connection = SocketCommunication("SOCKET", "", 8123, is_server=True, debug=False)
            # connection = SerialCommunication("SERIAL", CommonSerial(0, 76800, tx=0, rx=1, timeout=2), debug=False)
            WorkerServer("{}_srv".format(worker.name), communication=connection, worker=worker).start()
        except KeyboardInterrupt:
            pass

# boot = Boot.get_instance(led_notify=True)
# boot.load()
