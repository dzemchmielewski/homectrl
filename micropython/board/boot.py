import webrepl, time, machine
from configuration import Configuration


class Boot:

    loaded = {
        'wifi': False,
        'lan': False,
        'time': False,
        'webrepl': False,
    }
    led_pattern = [0.5, 0.3, 0.2, 0.2, 0.1, 0.1, 0.1, 0.05, 0.05]
    version = '20000101_00_00'
    instance = None

    @classmethod
    def get_instance(cls, pin_notify: int = None, pin_notify_on_signal: int | bool = None):
        if not cls.instance:
            cls.instance = Boot(pin_notify, pin_notify_on_signal)
        return cls.instance

    def pin_notify_signal(self, on_off: int | bool):
        if self.pin_notify:
            self.pin_notify.value(int(on_off) == self.pin_notify_on_signal)

    def __init__(self, pin_notify: int = None, pin_notify_on_signal: int | bool = None):
        self.wifi = None
        self.lan = None
        self.pin_notify = machine.Pin(pin_notify, machine.Pin.OUT) if pin_notify else None
        self.pin_notify_on_signal = 0 if pin_notify_on_signal in [None, False, 0] else 1

    def led_notification(self, reverse=False):
        if self.pin_notify:
            for sleep in (self.led_pattern[::-1] if reverse else self.led_pattern):
                for signal in [1, 0]:
                    self.pin_notify_signal(signal)
                    time.sleep(sleep)
            self.pin_notify_signal(1)


    def setup_wifi(self):
        if not self.wifi:
            import network
            network.country("PL")
            self.wifi = network.WLAN(network.STA_IF)

        self.wifi.active(True)
        # self.wifi.disconnect()

        while not self.wifi.isconnected():
            timeout = 30000
            self.led_notification()
            print(f"WIFI connecting to: {Configuration.WIFI_SSID}")
            self.wifi.connect(Configuration.WIFI_SSID, Configuration.WIFI_PASSWORD)
            while timeout > 0:
                if not self.wifi.isconnected():
                    time.sleep_ms(200)
                    timeout = timeout - 200
                else:
                    break
            if timeout <= 0:
                self.led_notification(reverse=True)

        self.pin_notify_signal(0)
        print(f"WIFI connected! ifconfig: {self.wifi.ifconfig()}")
        self.loaded['wifi'] = True

    def setup_lan(self):
        if not self.lan:
            import network

            self.lan = network.LAN(0,
                                   mdc=machine.Pin(23), mdio=machine.Pin(18),
                                   phy_type=network.PHY_LAN8720, phy_addr=1,
                                   power=machine.Pin(16))
            self.lan.active(True)

            while not self.lan.isconnected():
                timeout = 30000
                self.led_notification()
                print("LAN connecting...")

                while timeout > 0:
                    if not self.lan.isconnected():
                        time.sleep_ms(200)
                        timeout = timeout - 200
                    else:
                        break
                if timeout <= 0:
                    self.led_notification(reverse=True)

            self.pin_notify_signal(0)
            print(f"LAN connected! ifconfig: {self.lan.ifconfig()}")
            self.loaded['lan'] = True

    def setup_webrepl(self):
        if self.isconnected():
            webrepl.start(password=Configuration.WEBREPL_PASSWORD)
            self.loaded['webrepl'] = True
            print("SUCCESS webrepl load")

    def setup_time(self):
        if self.isconnected():
            import ntptime
            ntptime.host = 'status.home'

            now = ntptime.time()

            year = time.gmtime(now)[0]       # get current year
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
            self.loaded['time'] = True
            print(f"SUCCESS time load: {time.localtime()}")

    def isconnected(self):
        return (self.wifi and self.wifi.isconnected()) or (self.lan and self.lan.isconnected())

    def ifconfig(self):
        return self.wifi.ifconfig() if self.wifi and self.wifi.isconnected() \
            else self.lan.ifconfig() if self.lan and self.lan.isconnected() \
            else None

    def iftype(self):
        return 'WLAN' if self.wifi and self.wifi.isconnected() \
            else 'LAN' if self.lan and self.lan.isconnected() \
            else None

    def ifnetwork(self):
        return self.wifi if self.wifi and self.wifi.isconnected() \
            else self.lan if self.lan and self.lan.isconnected() \
            else None

    def load(self, wifi=True, lan=False, webrepl=True, time=True):
        if not self.loaded['wifi'] and wifi:
            try:
                self.setup_wifi()
            except Exception as e:
                print(f"FAILED to load wifi: {e}")

        if not self.loaded['lan'] and lan:
            try:
                self.setup_lan()
            except Exception as e:
                print(f"FAILED to load lan: {e}")

        if not self.loaded['webrepl'] and webrepl:
            try:
                self.setup_webrepl()
            except Exception as e:
                print(f"FAILED to load webrepl: {e}")

        if not self.loaded['time'] and time:
            try:
                self.setup_time()
            except Exception as e:
                print(f"FAILED to load time: {e}")

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

# boot = Boot.get_instance(pin_notify=8)
# boot.load()
