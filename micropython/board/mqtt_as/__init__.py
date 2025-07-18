# mqtt_as.py Asynchronous version of umqtt.robust
# (C) Copyright Peter Hinch 2017-2023.
# Released under the MIT licence.

# Pyboard D support added also RP2/default
# Various improvements contributed by Kevin Köck.

# https://github.com/peterhinch/micropython-mqtt.git
# Version: 30447639ea7aa237046d529f4453fe5a00c37206

import gc
import usocket as socket
import ustruct as struct
import utime as time

gc.collect()
from ubinascii import hexlify
import uasyncio as asyncio

gc.collect()
from utime import ticks_ms, ticks_diff
from uerrno import EINPROGRESS, ETIMEDOUT

gc.collect()
from micropython import const
from machine import unique_id
import network

gc.collect()
from sys import platform

VERSION = (0, 8, 2)
# Default initial size for input messge buffer. Increase this if large messages
# are expected, but rarely, to avoid big runtime allocations
IBUFSIZE = 50
# By default the callback interface returns and incoming message as bytes.
# For performance reasons with large messages it may return a memoryview.
MSG_BYTES = True

# Legitimate errors while waiting on a socket. See uasyncio __init__.py open_connection().
ESP32 = platform == "esp32"
RP2 = platform == "rp2"
if ESP32:
    # https://forum.micropython.org/viewtopic.php?f=16&t=3608&p=20942#p20942
    BUSY_ERRORS = [EINPROGRESS, ETIMEDOUT, 118, 119]  # Add in weird ESP32 errors
elif RP2:
    BUSY_ERRORS = [EINPROGRESS, ETIMEDOUT, -110]
else:
    BUSY_ERRORS = [EINPROGRESS, ETIMEDOUT]

ESP8266 = platform == "esp8266"
PYBOARD = platform == "pyboard"

# DZEM: 0 -> non-zero
ZERO_SLEEP_MS = 20

# Default "do little" coro for optional user replacement
async def eliza(*_):  # e.g. via set_wifi_handler(coro): see test program
    await asyncio.sleep_ms(ZERO_SLEEP_MS)


class MsgQueue:
    def __init__(self, size):
        self._q = [0 for _ in range(max(size, 4))]
        self._size = size
        self._wi = 0
        self._ri = 0
        self._evt = asyncio.Event()
        self.discards = 0

    def put(self, *v):
        self._q[self._wi] = v
        self._evt.set()
        self._wi = (self._wi + 1) % self._size
        if self._wi == self._ri:  # Would indicate empty
            self._ri = (self._ri + 1) % self._size  # Discard a message
            self.discards += 1

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._ri == self._wi:  # Empty
            self._evt.clear()
            await self._evt.wait()
        r = self._q[self._ri]
        self._ri = (self._ri + 1) % self._size
        return r


config = {
    "client_id": hexlify(unique_id()),
    "server": None,
    "port": 0,
    "user": "",
    "password": "",
    "keepalive": 60,
    "ping_interval": 0,
    "ssl": False,
    "ssl_params": {},
    "response_time": 10,
    "clean_init": True,
    "clean": True,
    "max_repubs": 4,
    "will": None,
    "subs_cb": lambda *_: None,
    "wifi_coro": eliza,
    "connect_coro": eliza,
    "ssid": None,
    "wifi_pw": None,
    "queue_len": 0,
    "gateway": False,
    "mqttv5": False,
    "mqttv5_con_props": None,
}


class MQTTException(Exception):
    pass


def pid_gen():
    pid = 0
    while True:
        pid = pid + 1 if pid < 65535 else 1
        yield pid


def qos_check(qos):
    if not (qos == 0 or qos == 1):
        raise ValueError("Only qos 0 and 1 are supported.")


encode_properties = None
decode_properties = None


class MQTT_base:
    REPUB_COUNT = 0  # TEST
    DEBUG = False

    def __init__(self, config):
        self._events = config["queue_len"] > 0
        # MQTT config
        self._client_id = config["client_id"]
        self._user = config["user"]
        self._pswd = config["password"]
        self._keepalive = config["keepalive"]
        if self._keepalive >= 65536:
            raise ValueError("invalid keepalive time")
        self._response_time = config["response_time"] * 1000  # Repub if no PUBACK received (ms).
        self._max_repubs = config["max_repubs"]
        self._clean_init = config["clean_init"]  # clean_session state on first connection
        self._clean = config["clean"]  # clean_session state on reconnect
        will = config["will"]
        if will is None:
            self._lw_topic = False
        else:
            self._set_last_will(*will)
        # WiFi config
        self._ssid = config["ssid"]  # Required for ESP32 / Pyboard D. Optional ESP8266
        self._wifi_pw = config["wifi_pw"]
        self._ssl = config["ssl"]
        self._ssl_params = config["ssl_params"]
        # Callbacks and coros
        if self._events:
            self.up = asyncio.Event()
            self.down = asyncio.Event()
            self.queue = MsgQueue(config["queue_len"])
            self._cb = self.queue.put
        else:  # Callbacks
            self._cb = config["subs_cb"]
            self._wifi_handler = config["wifi_coro"]
            self._connect_handler = config["connect_coro"]
        # Network
        self.port = config["port"]
        if self.port == 0:
            self.port = 8883 if self._ssl else 1883
        self.server = config["server"]
        if self.server is None:
            raise ValueError("no server specified.")
        self._sock = None
        self._sta_if = network.WLAN(network.STA_IF)
        self._sta_if.active(True)
        if config["gateway"]:  # Called from gateway (hence ESP32).
            import aioespnow  # Set up ESPNOW

            while not (sta := self._sta_if).active():
                time.sleep(0.1)
            sta.config(pm=sta.PM_NONE)  # No power management
            sta.active(True)
            self._espnow = aioespnow.AIOESPNow()  # Returns AIOESPNow enhanced with async support
            self._espnow.active(True)

        self.newpid = pid_gen()
        self.rcv_pids = set()  # PUBACK and SUBACK pids awaiting ACK response
        self.last_rx = ticks_ms()  # Time of last communication from broker
        self.lock = asyncio.Lock()
        self._ibuf = bytearray(IBUFSIZE)
        self._mvbuf = memoryview(self._ibuf)

        self.mqttv5 = config.get("mqttv5")
        self.mqttv5_con_props = config.get("mqttv5_con_props")
        self.topic_alias_maximum = 0

        if self.mqttv5:
            global encode_properties, decode_properties
            from .mqtt_v5_properties import encode_properties, decode_properties  # noqa

    def _set_last_will(self, topic, msg, retain=False, qos=0):
        qos_check(qos)
        if not topic:
            raise ValueError("Empty topic.")
        self._lw_topic = topic
        self._lw_msg = msg
        self._lw_qos = qos
        self._lw_retain = retain

    def dprint(self, msg, *args):
        if self.DEBUG:
            print(msg % args)

    def _timeout(self, t):
        return ticks_diff(ticks_ms(), t) > self._response_time

    async def _as_read(self, n, sock=None):  # OSError caught by superclass
        if sock is None:
            sock = self._sock
        # Ensure input buffer is big enough to hold data. It keeps the new size
        oflow = n - len(self._ibuf)
        if oflow > 0:  # Grow the buffer and re-create the memoryview
            # Avoid too frequent small allocations by adding some extra bytes
            self._ibuf.extend(bytearray(oflow + 50))
            self._mvbuf = memoryview(self._ibuf)
        buffer = self._mvbuf
        size = 0
        t = ticks_ms()
        while size < n:
            if self._timeout(t) or not self.isconnected():
                raise OSError(-1, "Timeout on socket read")
            try:
                msg_size = sock.readinto(buffer[size:], n - size)
            except OSError as e:  # ESP32 issues weird 119 errors here
                msg_size = None
                if e.args[0] not in BUSY_ERRORS:
                    raise
            if msg_size == 0:  # Connection closed by host
                raise OSError(-1, "Connection closed by host")
            if msg_size is not None:  # data received
                size += msg_size
                t = ticks_ms()
                self.last_rx = ticks_ms()
            await asyncio.sleep_ms(ZERO_SLEEP_MS)
        return buffer[:n]

    async def _as_write(self, bytes_wr, length=0, sock=None):
        if sock is None:
            sock = self._sock

        # Wrap bytes in memoryview to avoid copying during slicing
        bytes_wr = memoryview(bytes_wr)
        if length:
            bytes_wr = bytes_wr[:length]
        t = ticks_ms()
        while bytes_wr:
            if self._timeout(t) or not self.isconnected():
                raise OSError(-1, "Timeout on socket write")
            try:
                n = sock.write(bytes_wr)
            except OSError as e:  # ESP32 issues weird 119 errors here
                n = 0
                if e.args[0] not in BUSY_ERRORS:
                    raise
            if n:
                t = ticks_ms()
                bytes_wr = bytes_wr[n:]
            await asyncio.sleep_ms(ZERO_SLEEP_MS)

    async def _send_str(self, s):
        await self._as_write(struct.pack("!H", len(s)))
        await self._as_write(s)

    async def _recv_len(self):
        n = 0
        sh = 0
        i = 0
        while 1:
            res = await self._as_read(1)
            i += 1
            b = res[0]
            n |= (b & 0x7F) << sh
            if not b & 0x80:
                return n, i
            sh += 7

    async def _connect(self, clean):
        mqttv5 = self.mqttv5  # Cache local
        self._sock = socket.socket()
        self._sock.setblocking(False)
        try:
            self._sock.connect(self._addr)
        except OSError as e:
            if e.args[0] not in BUSY_ERRORS:
                raise
        await asyncio.sleep_ms(ZERO_SLEEP_MS)
        self.dprint("Connecting to broker.")
        if self._ssl:
            try:
                import ssl
            except ImportError:
                import ussl as ssl

            self._sock = ssl.wrap_socket(self._sock, **self._ssl_params)
        premsg = bytearray(b"\x10\0\0\0\0\0")
        msg = bytearray(b"\x04MQTT\x00\0\0\0")
        if mqttv5:
            msg[5] = 0x05
        else:
            msg[5] = 0x04

        sz = 10 + 2 + len(self._client_id)
        msg[6] = clean << 1
        if self._user:
            sz += 2 + len(self._user) + 2 + len(self._pswd)
            msg[6] |= 0xC0
        if self._keepalive:
            msg[7] |= self._keepalive >> 8
            msg[8] |= self._keepalive & 0x00FF
        if self._lw_topic:
            sz += 2 + len(self._lw_topic) + 2 + len(self._lw_msg)
            if mqttv5:
                # Extra for the will properties
                sz += 1
            msg[6] |= 0x4 | (self._lw_qos & 0x1) << 3 | (self._lw_qos & 0x2) << 3
            msg[6] |= self._lw_retain << 5

        if mqttv5:
            properties = encode_properties(self.mqttv5_con_props)
            sz += len(properties)

        i = 1
        while sz > 0x7F:
            premsg[i] = (sz & 0x7F) | 0x80
            sz >>= 7
            i += 1
        premsg[i] = sz
        await self._as_write(premsg, i + 2)
        await self._as_write(msg)
        if mqttv5:
            await self._as_write(properties)

        await self._send_str(self._client_id)
        if self._lw_topic:
            if mqttv5:
                # We don't support will properties, so we send 0x00 for properties length
                await self._as_write(b"\x00")
            await self._send_str(self._lw_topic)
            await self._send_str(self._lw_msg)
        if self._user:
            await self._send_str(self._user)
            await self._send_str(self._pswd)
        # Await CONNACK
        # read causes ECONNABORTED if broker is out; triggers a reconnect.
        del premsg, msg
        packet_type = await self._as_read(1)
        if packet_type[0] != 0x20:
            raise OSError(-1, "CONNACK not received")
        # The connect packet has changed, so size might be different now. But
        # we can still handle it the same for 3.1.1 and v5
        sz, _ = await self._recv_len()
        if not mqttv5 and sz != 2:
            raise OSError(-1, "Invalid CONNACK packet")

        # Only read the first 2 bytes, as properties have their own length
        connack_resp = await self._as_read(2)

        # Connect ack flags
        if connack_resp[0] != 0:
            raise OSError(-1, "CONNACK flags not 0")
        # Reason code
        if connack_resp[1] != 0:
            # On MQTTv5 Reason codes below 128 may need to be handled
            # differently. For now, we just raise an error. Spec is a bit weird
            # on this.
            raise OSError(-1, "CONNACK reason code 0x%x" % connack_resp[1])

        del connack_resp
        if not mqttv5:
            # If we are not on MQTTv5 we can stop here
            self.dprint("Connecting to broker DONE")
            return

        connack_props_length, _ = await self._recv_len()
        if connack_props_length > 0:
            connack_props = await self._as_read(connack_props_length)
            decoded_props = decode_properties(connack_props, connack_props_length)
            self.dprint("CONNACK properties: %s", decoded_props)
            self.topic_alias_maximum = decoded_props.get(0x22, 0)

    async def _ping(self):
        async with self.lock:
            await self._as_write(b"\xc0\0")

    # Check internet connectivity by sending DNS lookup to Google's 8.8.8.8
    async def wan_ok(
        self,
        packet=b"$\x1a\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03www\x06google\x03com\x00\x00\x01\x00\x01",
    ):
        if not self.isconnected():  # WiFi is down
            return False
        length = 32  # DNS query and response packet size
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setblocking(False)
        s.connect(("8.8.8.8", 53))
        await asyncio.sleep(1)
        async with self.lock:
            try:
                await self._as_write(packet, sock=s)
                await asyncio.sleep(2)
                res = await self._as_read(length, s)
                if len(res) == length:
                    return True  # DNS response size OK
            except OSError:  # Timeout on read: no connectivity.
                return False
            finally:
                s.close()
        return False

    async def broker_up(self):  # Test broker connectivity
        if not self.isconnected():
            return False
        tlast = self.last_rx
        if ticks_diff(ticks_ms(), tlast) < 1000:
            return True
        try:
            await self._ping()
        except OSError:
            return False
        t = ticks_ms()
        while not self._timeout(t):
            await asyncio.sleep_ms(100)
            if ticks_diff(self.last_rx, tlast) > 0:  # Response received
                return True
        return False

    async def disconnect(self):
        if self._sock is not None:
            await self._kill_tasks(False)  # Keep socket open
            try:
                async with self.lock:
                    self._sock.write(b"\xe0\0")  # Close broker connection
                    await asyncio.sleep_ms(100)
            except OSError:
                pass
            self._close()
        self._has_connected = False

    def _close(self):
        if self._sock is not None:
            self._sock.close()

    def close(self):  # API. See https://github.com/peterhinch/micropython-mqtt/issues/60
        self._close()
        # try:
        #     self._sta_if.disconnect()  # Disconnect Wi-Fi to avoid errors
        # except OSError:
        #     self.dprint("Wi-Fi not started, unable to disconnect interface")
        # self._sta_if.active(False)

    async def _await_pid(self, pid):
        t = ticks_ms()
        while pid in self.rcv_pids:  # local copy
            if self._timeout(t) or not self.isconnected():
                break  # Must repub or bail out
            await asyncio.sleep_ms(100)
        else:
            return True  # PID received. All done.
        return False

    # qos == 1: coro blocks until wait_msg gets correct PID.
    # If WiFi fails completely subclass re-publishes with new PID.
    async def publish(self, topic, msg, retain, qos=0, properties=None):
        pid = next(self.newpid)
        if qos:
            self.rcv_pids.add(pid)
        async with self.lock:
            await self._publish(topic, msg, retain, qos, 0, pid, properties)
        if qos == 0:
            return

        count = 0
        while 1:  # Await PUBACK, republish on timeout
            if await self._await_pid(pid):
                return
            # No match
            if count >= self._max_repubs or not self.isconnected():
                raise OSError(-1)  # Subclass to re-publish with new PID
            async with self.lock:
                # Add pid
                await self._publish(topic, msg, retain, qos, dup=1, pid=pid, properties=properties)
            count += 1
            self.REPUB_COUNT += 1

    async def _publish(self, topic, msg, retain, qos, dup, pid, properties=None):
        pkt = bytearray(b"\x30\0\0\0")
        pkt[0] |= qos << 1 | retain | dup << 3
        sz = 2 + len(topic) + len(msg)
        if qos > 0:
            sz += 2

        if self.mqttv5:
            properties = encode_properties(properties)
            sz += len(properties)

        if sz >= 2097152:
            raise MQTTException("Strings too long.")
        i = 1
        while sz > 0x7F:
            pkt[i] = (sz & 0x7F) | 0x80
            sz >>= 7
            i += 1
        pkt[i] = sz
        await self._as_write(pkt, i + 1)
        await self._send_str(topic)
        if qos > 0:
            struct.pack_into("!H", pkt, 0, pid)
            await self._as_write(pkt, 2)
        if self.mqttv5:
            await self._as_write(properties)
        await self._as_write(msg)

    # Can raise OSError if WiFi fails. Subclass traps.
    async def subscribe(self, topic, qos, properties=None):
        pkt = bytearray(b"\x82\0\0\0")
        pid = next(self.newpid)
        self.rcv_pids.add(pid)
        sz = 2 + 2 + len(topic) + 1
        if self.mqttv5:
            properties = encode_properties(properties)
            sz += len(properties)

        struct.pack_into("!BH", pkt, 1, sz, pid)
        async with self.lock:
            await self._as_write(pkt)
            if self.mqttv5:
                await self._as_write(properties)
            await self._send_str(topic)
            # Only QoS is supported other features such as:
            # (NL) No Local, (RAP) Retain As Published and Retain Handling.
            # Are not supported.
            await self._as_write(qos.to_bytes(1, "little"))

        if not await self._await_pid(pid):
            raise OSError(-1)

    # Can raise OSError if WiFi fails. Subclass traps.
    async def unsubscribe(self, topic, properties=None):
        pkt = bytearray(b"\xa2\0\0\0")
        pid = next(self.newpid)
        self.rcv_pids.add(pid)
        sz = 2 + 2 + len(topic)
        if self.mqttv5:
            properties = encode_properties(properties)
            sz += len(properties)

        struct.pack_into("!BH", pkt, sz, pid)
        async with self.lock:
            await self._as_write(pkt)
            if self.mqttv5:
                await self._as_write(properties)
            await self._send_str(topic)

        if not await self._await_pid(pid):
            raise OSError(-1)

    # Wait for a single incoming MQTT message and process it.
    # Subscribed messages are delivered to a callback previously
    # set by .setup() method. Other (internal) MQTT
    # messages processed internally.
    # Immediate return if no data available. Called from ._handle_msg().
    async def wait_msg(self):
        mqttv5 = self.mqttv5  # Cache local
        try:
            res = self._sock.read(1)  # Throws OSError on WiFi fail
        except OSError as e:
            if e.args[0] in BUSY_ERRORS:  # Needed by RP2
                await asyncio.sleep_ms(ZERO_SLEEP_MS)
                return
            raise

        if res is None:
            return
        if res == b"":
            raise OSError(-1, "Empty response")

        if res == b"\xd0":  # PINGRESP
            await self._as_read(1)  # Update .last_rx time
            return
        op = res[0]

        if op == 0x40:  # PUBACK: save pid
            sz, _ = await self._recv_len()
            if not mqttv5 and sz != 2:
                raise OSError(-1, "Invalid PUBACK packet")
            rcv_pid = await self._as_read(2)
            pid = rcv_pid[0] << 8 | rcv_pid[1]
            # For some reason even on MQTTv5 reason code is optional
            if sz != 2:
                reason_code = await self._as_read(1)
                reason_code = reason_code[0]
                if reason_code >= 0x80:
                    raise OSError(-1, "PUBACK reason code 0x%x" % reason_code)
            if sz > 3:
                puback_props_sz, _ = await self._recv_len()
                if puback_props_sz > 0:
                    puback_props = await self._as_read(puback_props_sz)
                    decoded_props = decode_properties(puback_props, puback_props_sz)
                    self.dprint("PUBACK properties %s", decoded_props)
            if pid in self.rcv_pids:
                self.rcv_pids.discard(pid)
            else:
                raise OSError(-1, "Invalid pid in PUBACK packet")

        if op == 0x90:  # SUBACK
            sz, _ = await self._recv_len()
            rcv_pid = await self._as_read(2)
            sz -= 2
            pid = rcv_pid[0] << 8 | rcv_pid[1]
            # Handle properties
            if mqttv5:
                suback_props_sz, sz_len = await self._recv_len()
                sz -= sz_len
                sz -= suback_props_sz
                if suback_props_sz > 0:
                    suback_props = await self._as_read(suback_props_sz)
                    decoded_props = decode_properties(suback_props, suback_props_sz)
                    self.dprint("SUBACK properties %s", decoded_props)

            if sz > 1:
                raise OSError(-1, "Got too many bytes")

            reason_code = await self._as_read(sz)
            reason_code = reason_code[0]
            if reason_code >= 0x80:
                raise OSError(-1, "SUBACK reason code 0x%x" % reason_code)

            if pid in self.rcv_pids:
                self.rcv_pids.discard(pid)
            else:
                raise OSError(-1, "Invalid pid in SUBACK packet")

        if op == 0xE0:  # DISCONNECT
            if mqttv5:
                sz, _ = await self._recv_len()
                reason_code = await self._as_read(1)
                reason_code = reason_code[0]

                sz -= 1
                if sz > 0:
                    dis_props_sz, dis_len = await self._recv_len()
                    sz -= dis_len
                    disconnect_props = await self._as_read(dis_props_sz)
                    decoded_props = decode_properties(disconnect_props, dis_props_sz)
                    self.dprint("DISCONNECT properties %s", decoded_props)

                if reason_code >= 0x80:
                    raise OSError(-1, "DISCONNECT reason code 0x%x" % reason_code)

        if op & 0xF0 != 0x30:
            return

        sz, _ = await self._recv_len()
        topic_len = await self._as_read(2)
        topic_len = (topic_len[0] << 8) | topic_len[1]
        topic = await self._as_read(topic_len)
        topic = bytes(topic)  # Copy before re-using the read buffer
        sz -= topic_len + 2
        if op & 6:
            pid = await self._as_read(2)
            pid = pid[0] << 8 | pid[1]
            sz -= 2

        decoded_props = None
        if mqttv5:
            pub_props_sz, pub_props_sz_len = await self._recv_len()
            sz -= pub_props_sz_len
            sz -= pub_props_sz
            if pub_props_sz > 0:
                pub_props = await self._as_read(pub_props_sz)
                decoded_props = decode_properties(pub_props, pub_props_sz)

        msg = await self._as_read(sz)
        # In event mode we must copy the message otherwise .queue contents will be wrong:
        # every entry would contain the same message.
        # In callback mode not copying the message is OK so long as the callback is purely
        # synchronous. Overruns can't occur because of the lock.
        if self._events or MSG_BYTES:
            msg = bytes(msg)
        retained = op & 0x01
        args = [topic, msg, bool(retained)]
        if mqttv5:
            args.append(decoded_props)
        self._cb(*args)

        if op & 6 == 2:  # qos 1
            pkt = bytearray(b"\x40\x02\0\0")  # Send PUBACK
            struct.pack_into("!H", pkt, 2, pid)
            await self._as_write(pkt)
        elif op & 6 == 4:  # qos 2 not supported
            raise OSError(-1, "QoS 2 not supported")


# MQTTClient class. Handles issues relating to connectivity.


class MQTTClient(MQTT_base):
    def __init__(self, config):
        super().__init__(config)
        self._isconnected = False  # Current connection state
        keepalive = 1000 * self._keepalive  # ms
        self._ping_interval = keepalive // 4 if keepalive else 20000
        p_i = config["ping_interval"] * 1000  # Can specify shorter e.g. for subscribe-only
        if p_i and p_i < self._ping_interval:
            self._ping_interval = p_i
        self._in_connect = False
        self._has_connected = False  # Define 'Clean Session' value to use.
        self._tasks = []
        if ESP8266:
            import esp

            esp.sleep_type(0)  # Improve connection integrity at cost of power consumption.

    async def wifi_connect(self, quick=False):
        s = self._sta_if
        if ESP8266:
            if s.isconnected():  # 1st attempt, already connected.
                return
            s.active(True)
            s.connect()  # ESP8266 remembers connection.
            for _ in range(60):
                # Break out on fail or success. Check once per sec.
                if s.status() != network.STAT_CONNECTING:
                    break
                await asyncio.sleep(1)
            # might hang forever awaiting dhcp lease renewal or something else
            if s.status() == network.STAT_CONNECTING:
                s.disconnect()
                await asyncio.sleep(1)
            if not s.isconnected() and self._ssid is not None and self._wifi_pw is not None:
                s.connect(self._ssid, self._wifi_pw)
                # Break out on fail or success. Check once per sec.
                while s.status() == network.STAT_CONNECTING:
                    await asyncio.sleep(1)
        else:
            s.active(True)
            if RP2:  # Disable auto-sleep.
                # https://datasheets.raspberrypi.com/picow/connecting-to-the-internet-with-pico-w.pdf
                # para 3.6.3
                s.config(pm=0xA11140)
            s.connect(self._ssid, self._wifi_pw)
            for _ in range(60):  # Break out on fail or success. Check once per sec.
                await asyncio.sleep(1)
                # Loop while connecting or no IP
                if s.isconnected():
                    break
                if ESP32:
                    # Status values >= STAT_IDLE can occur during connect:
                    # STAT_IDLE 1000, STAT_CONNECTING 1001, STAT_GOT_IP 1010
                    # Error statuses are in range 200..204
                    if s.status() < network.STAT_IDLE:
                        # pause as workaround to avoid persistent reconnect failures
                        # see https://github.com/peterhinch/micropython-mqtt/issues/132 for details
                        await asyncio.sleep(1)
                        break
                elif PYBOARD:  # No symbolic constants in network
                    if not 1 <= s.status() <= 2:
                        break
                elif RP2:  # 1 is STAT_CONNECTING. 2 reported by user (No IP?)
                    if not 1 <= s.status() <= 2:
                        break
            else:  # Timeout: still in connecting state
                s.disconnect()
                await asyncio.sleep(1)

        if not s.isconnected():  # Timed out
            raise OSError("Wi-Fi connect timed out")
        if not quick:  # Skip on first connection only if power saving
            # Ensure connection stays up for a few secs.
            self.dprint("Checking WiFi integrity.")
            for _ in range(5):
                if not s.isconnected():
                    raise OSError("Connection Unstable")  # in 1st 5 secs
                await asyncio.sleep(1)
            self.dprint("Got reliable connection")

    async def connect(self, *, quick=False):  # Quick initial connect option for battery apps
        if not self._has_connected:
            await self.wifi_connect(quick)  # On 1st call, caller handles error
            # Note this blocks if DNS lookup occurs. Do it once to prevent
            # blocking during later internet outage:
            self._addr = socket.getaddrinfo(self.server, self.port)[0][-1]
        self._in_connect = True  # Disable low level ._isconnected check
        try:
            is_clean = self._clean
            if not self._has_connected and self._clean_init and not self._clean:
                if self.mqttv5:
                    is_clean = True
                else:
                    # Power up. Clear previous session data but subsequently save it.
                    # Issue #40
                    await self._connect(True)  # Connect with clean session
                    try:
                        async with self.lock:
                            self._sock.write(b"\xe0\0")  # Force disconnect but keep socket open
                    except OSError:
                        pass
                    self.dprint("Waiting for disconnect")
                    await asyncio.sleep(2)  # Wait for broker to disconnect
                    self.dprint("About to reconnect with unclean session.")
            await self._connect(is_clean)
        except Exception:
            self._close()
            self._in_connect = False  # Caller may run .isconnected()
            raise
        self.rcv_pids.clear()
        # If we get here without error broker/LAN must be up.
        self._isconnected = True
        self._in_connect = False  # Low level code can now check connectivity.
        if not self._events:
            asyncio.create_task(self._wifi_handler(True))  # User handler.
        if not self._has_connected:
            self._has_connected = True  # Use normal clean flag on reconnect.
            asyncio.create_task(self._keep_connected())
            # Runs forever unless user issues .disconnect()

        asyncio.create_task(self._handle_msg())  # Task quits on connection fail.
        self._tasks.append(asyncio.create_task(self._keep_alive()))
        # if self.DEBUG:
        #     self._tasks.append(asyncio.create_task(self._memory()))
        if self._events:
            self.up.set()  # Connectivity is up
        else:
            asyncio.create_task(self._connect_handler(self))  # User handler.

    # Launched by .connect(). Runs until connectivity fails. Checks for and
    # handles incoming messages.
    async def _handle_msg(self):
        try:
            while self.isconnected():
                async with self.lock:
                    await self.wait_msg()  # Immediate return if no message
                # DZEM: 0 -> non-zero
                await asyncio.sleep_ms(ZERO_SLEEP_MS)  # Let other tasks get lock

        except OSError:
            pass
        self._reconnect()  # Broker or WiFi fail.

    # Keep broker alive MQTT spec 3.1.2.10 Keep Alive.
    # Runs until ping failure or no response in keepalive period.
    async def _keep_alive(self):
        while self.isconnected():
            pings_due = ticks_diff(ticks_ms(), self.last_rx) // self._ping_interval
            if pings_due >= 4:
                self.dprint("Reconnect: broker fail.")
                break
            await asyncio.sleep_ms(self._ping_interval)
            try:
                await self._ping()
            except OSError:
                break
        self._reconnect()  # Broker or WiFi fail.

    async def _kill_tasks(self, kill_skt):  # Cancel running tasks
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        await asyncio.sleep_ms(ZERO_SLEEP_MS)  # Ensure cancellation complete
        if kill_skt:  # Close socket
            self._close()

    # DEBUG: show RAM messages.
    async def _memory(self):
        while True:
            await asyncio.sleep(20)
            gc.collect()
            self.dprint("RAM free %d alloc %d", gc.mem_free(), gc.mem_alloc())

    def isconnected(self):
        if self._in_connect:  # Disable low-level check during .connect()
            return True

        if self._isconnected and not self._sta_if.isconnected():  # It's going down.
            self._reconnect()
        return self._isconnected

    def _reconnect(self):  # Schedule a reconnection if not underway.
        if self._isconnected:
            self._isconnected = False
            asyncio.create_task(self._kill_tasks(True))  # Shut down tasks and socket
            if self._events:  # Signal an outage
                self.down.set()
            else:
                asyncio.create_task(self._wifi_handler(False))  # User handler.

    # Await broker connection.
    async def _connection(self):
        while not self._isconnected:
            await asyncio.sleep(1)

    # Scheduled on 1st successful connection. Runs forever maintaining wifi and
    # broker connection. Must handle conditions at edge of WiFi range.
    async def _keep_connected(self):
        while self._has_connected:
            if self.isconnected():  # Pause for 1 second
                await asyncio.sleep(1)
                gc.collect()
            else:  # Link is down, socket is closed, tasks are killed
                try:
                    self._sta_if.disconnect()
                except OSError:
                    self.dprint("Wi-Fi not started, unable to disconnect interface")
                await asyncio.sleep(1)
                try:
                    await self.wifi_connect()
                except OSError:
                    continue
                if not self._has_connected:  # User has issued the terminal .disconnect()
                    self.dprint("Disconnected, exiting _keep_connected")
                    break
                try:
                    await self.connect()
                    # Now has set ._isconnected and scheduled _connect_handler().
                    self.dprint("Reconnect OK!")
                except OSError as e:
                    self.dprint("Error in reconnect. %s", e)
                    # Can get ECONNABORTED or -1. The latter signifies no or bad CONNACK received.
                    self._close()  # Disconnect and try again.
                    self._in_connect = False
                    self._isconnected = False
        self.dprint("Disconnected, exited _keep_connected")

    async def subscribe(self, topic, qos=0, properties=None):
        qos_check(qos)
        while 1:
            await self._connection()
            try:
                return await super().subscribe(topic, qos, properties)
            except OSError:
                pass
            self._reconnect()  # Broker or WiFi fail.

    async def unsubscribe(self, topic, properties=None):
        while 1:
            await self._connection()
            try:
                return await super().unsubscribe(topic, properties)
            except OSError:
                pass
            self._reconnect()  # Broker or WiFi fail.

    # DZEM: do not use this method, it is not reliable.
    # async def publish(self, topic, msg, retain=False, qos=0, properties=None):
    #     qos_check(qos)
    #     while 1:
    #         await self._connection()
    #         try:
    #             return await super().publish(topic, msg, retain, qos, properties)
    #         except OSError:
    #             pass
    #         self._reconnect()  # Broker or WiFi fail.
