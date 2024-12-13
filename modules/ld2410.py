# This code bases on very good work of Sean Yong:
# https://github.com/vjsyong/LD2410
# Thanks Sean!
import time

from common.common import Common, CommonSerial
from modules.ld2410_consts import *
from collections import deque
import struct


class Queue:
    def __init__(self, max_size):
        self.queue = deque((), max_size)

    def add(self, element):
        self.queue.append(element)

    def byte_str(self):
        return b"".join(list(self.queue))


class LD2410(Common):
    def __init__(self, name, serial: CommonSerial, debug=False) -> None:
        super().__init__(name, debug)
        self.eng_mode = False
        self.read_fail_count = 0
        self.ser = serial

    # Validate that the input is within a valid range
    @staticmethod
    def validate_range(input, lower, upper):
        if input in range(lower, upper):
            return True
        else:
            input_name = f'{input=}'.split('=')[0]
            raise Exception(f"{input_name} {input} is not a valid setting, please pick a value between {lower} and {upper}")

    # Helper functions
    @staticmethod
    def frame_wrapper(command):
        return bytes.fromhex(CMD_HEADER + command + CMD_MFR)

    # Convert a decimal integer to a 4 byte little endian string
    @staticmethod
    def int_to_4b(num):
        hex_string = bytearray.fromhex(struct.pack('>I', num).hex())

        # bytearray.reverse is not available in micropython
        # hex_string.reverse()
        # so, here workaround:
        rev = bytearray()
        for byte in reversed(hex_string):
            rev.append(byte)
        hex_string = rev

        return bytes(hex_string).hex()

    # Base functions

    def read_until(self, str, return_reads = False):
        result = bytearray()
        buffer = Queue(max_size=4)
        # Keep cycling the buffer until frame starts
        while buffer.byte_str() != bytes.fromhex(str):
            success_read = True
            try:
                b = self.ser.read(1)
                if b is None:
                    success_read = False
            except:
                success_read = False

            if not success_read:
                self.read_fail_count += 1
                self.debug("Serial failed to read data. Trying again")
                self.read_fail_count += 1
                if self.read_fail_count > 320:
                    self.read_fail_count = 0
                    self.log(
                        "Serial failed to read data many times in a row. Please check if the baud rate is correct. Hint: Check the firmware version, if it looks weird, it's probably wrong")
                    # raise OSError("Serial failed to read data many times in a row.")

                b = b""

            buffer.add(b)
            if return_reads:
                result.append(int.from_bytes(b, 'big'))
        return result

    # Sends a dataframe encoded as bytes enclosed within a format specific header
    # Returns the acknowledged data received from the radar
    def send_frame(self, command):
        while True:
            try:
                # Wrap up the command 
                command_bytes = self.frame_wrapper(command)

                self.ser.write(command_bytes)
                ret_bytes = self.ser.read(MAX_BUFFER_SIZE)

                self.debug(f"Sending data:  {command_bytes.hex(' ')}")
                self.debug(f"Received data: {ret_bytes.hex(' ')}")

                return ret_bytes  # Returns the response given by the radar module

            except Exception as e:
                self.debug(e)
                raise e

    # Sends a dataframe encoded as bytes enclosed within a format specific header
    # Returns the acknowledged data received from the radar
    def send_frame2(self, command, ack_command):
        while True:
            try:
                # Wrap up the command
                command_bytes = self.frame_wrapper(command)
                self.debug(f"Sending data:  {command_bytes.hex(' ')}")
                self.ser.write(command_bytes)

                self.read_until(CMD_HEADER)
                head = bytes.fromhex(CMD_HEADER)
                ack_word = None
                while ack_word != bytes.fromhex(ack_command):
                    answer = head + self.read_until(CMD_MFR, True)
                    ack_word = answer[6:8]

                self.debug(f"Received data: {answer.hex(' ')}")

                return answer  # Returns the response given by the radar module

            except Exception as e:
                self.debug(e)
                raise e

    def send_command(self, command):
        # Enable config mode
        self.send_frame(CMD_CONFIG_ENABLE)
        # Send command
        ret_bytes = self.send_frame(command)
        # Disable config mode
        self.send_frame(CMD_CONFIG_DISABLE)

        return ret_bytes

    def send_command2(self, command, ack_command):
        # Enable config mode
        self.send_frame2(CMD_CONFIG_ENABLE, CMD_CONFIG_ENABLE_ACK)
        # Send command
        ret_bytes = self.send_frame2(command, ack_command)
        # Disable config mode
        self.send_frame2(CMD_CONFIG_DISABLE, CMD_CONFIG_DISABLE_ACK)

        return ret_bytes

    # Configure Detection Gates and Detect Duration
    def edit_detection_params(self, moving_max_gate, static_max_gate, timeout):
        self.log("Editing detection parameters")
        self.validate_range(moving_max_gate, GATE_MIN, GATE_MAX + 1)
        self.validate_range(static_max_gate, GATE_MIN, GATE_MAX + 1)
        self.validate_range(timeout, TIMEOUT_MIN, TIMEOUT_MAX + 1)

        command = CMD_PARAM_EDIT + PARAM_MAX_MOVING_GATE + self.int_to_4b(moving_max_gate) \
                  + PARAM_MAX_STATIC_GATE + self.int_to_4b(static_max_gate) \
                  + PARAM_EMPTY_DURATION + self.int_to_4b(timeout)

        self.send_command(command)

    # Read the currently configured parameters 
    #
    # Returns 3 arrays, 
    # 
    # first array: [moving gate threshold, static gate threshold, empty timeout]
    # second array: [moving gate sens 0.... moving gate sens 8]
    # third array: [static gate sens 0.... static gate sens 8]

    def read_detection_params(self):
        # Send command to retrieve parameters
        self.log("Reading detection parameters")
        ret = self.send_command2(CMD_PARAM_READ, CMD_PARAM_READ_ACK)

        # Process response
        # Threshold Params
        thresholds = [ret[REF_MAX_MOVING_GATE], ret[REF_MAX_STATIC_GATE], ret[REF_EMPTY_TIMEOUT]]

        # Movement Gate Sensitivities
        move_sens = [int(byte) for byte in ret[REF_MOVING_GATE_SENS_0:REF_MOVING_GATE_SENS_8]]
        # Static Gate Sensitivities
        static_sens = [int(byte) for byte in ret[REF_STATIC_GATE_SENS_0:REF_STATIC_GATE_SENS_8]]

        self.debug(f"Thresholds:{thresholds}, Movement Sens:{move_sens}, Static Sens:{static_sens}")
        return thresholds, move_sens, static_sens

    # Enable Engineering Mode
    # Adds energy level of each gate to the radar output
    def enable_engineering_mode(self):
        self.log("Enabling engineering mode")
        self.eng_mode = True
        self.send_command(CMD_ENG_MODE_ENABLE)

    # Disable Engineering Mode
    def disable_engineering_mode(self):
        self.log("Disabling engineering mode")
        self.eng_mode = False
        self.send_command(CMD_ENG_MODE_DISABLE)

    # Configure Gate Movement and Static Sensitivities
    def edit_gate_sensitivity(self, gate, moving_sens, static_sens):
        self.log("Editing gate sensitivity")
        self.validate_range(gate, GATE_MIN, GATE_MAX + 1)
        self.validate_range(moving_sens, SENS_MIN, SENS_MAX + 1)

        # if gate == 0 or gate == 1:
        if gate == 20:
            self.log("You cannot set gate 0 or 1 static sensitivity to anything other than 0")
            self.validate_range(static_sens, 0, 1)
        else:
            self.validate_range(static_sens, SENS_MIN, SENS_MAX + 1)

        command = CMD_GATE_SENS_EDIT + PARAM_GATE_SELECT + self.int_to_4b(gate) \
                  + PARAM_MOVING_GATE_WORD + self.int_to_4b(moving_sens) \
                  + PARAM_STATIC_GATE_WORD + self.int_to_4b(static_sens)

        self.send_command(command)

    # Read Firmware Version
    def read_firmware_version(self):
        self.log("Reading firmware version")
        ret = self.send_command2(CMD_FIRMWARE_READ, CMD_FIRMWARE_READ_ACK)

        # Need to flip from little endian to big endian
        fw_major = bytes(reversed(ret[REF_FW_MAJOR_HEAD:REF_FW_MAJOR_TAIL]))
        fw_minor = bytes(reversed(ret[REF_FW_MINOR_HEAD:REF_FW_MINOR_TAIL]))

        fw_version = f"V{fw_major[0]}.{fw_major[1]:02}.{fw_minor.hex()}"

        return fw_version

    # Used to set the baud rate of the module. 
    # Setting "reconnect=True" will allow the driver to 
    # restart and reset the module and adapt the host to the new baud rate

    # Check consts.py to find the right settings
    def set_baud_rate(self, baud_rate, reconnect=True):
        self.log(f"Setting baud rate to {BAUD_LOOKUP[baud_rate]}")
        if baud_rate not in PARAM_ACCEPTABLE_BAUDS:
            raise Exception(f"{baud_rate} is not a valid setting. Consult consts.py to find an appropriate setting.")

        self.send_command(CMD_BAUD_RATE_SET + baud_rate)

        if reconnect:
            self.log("Baud rate set command issued. Calling restart.")
            # Restart the driver with the new baudrate
            self.restart_module(baud_rate)

    def factory_reset(self, reconnect=True):
        self.log("Module will now be factory reset")
        self.send_command(CMD_FACTORY_RESET)
        if reconnect:
            self.restart_module()

    def restart_module(self):
        self.log("Restarting module")
        self.send_command(CMD_RESTART)

        self.ser.close()
        self.ser = self.ser.reinit()
        self.eng_mode = False
        time.sleep(1)

    # Enable Bluetooth
    def bt_enable(self):
        self.log("Enabling Bluetooth")
        self.send_command(CMD_BT_ENABLE)

    # Disable Bluetooth
    def bt_disable(self):
        self.log("Disabling Bluetooth")
        self.send_command(CMD_BT_DISABLE)

    # Get Bluetooth MAC Address
    # Returns a string in the format of xx:xx:xx:xx:xx:xx
    def bt_query_mac(self):
        self.log("Getting Bluetooth Address")
        ret = self.send_command(CMD_BT_MAC_QUERY)
        mac = ret[REF_BT_ADDR_HEAD:REF_BT_ADDR_TAIL].hex(":")
        self.log(f"Bluetooth address is {mac}")
        return mac

    # Get Radar Frame
    def get_data_frame(self):
        self.debug("Getting raw dataframe")

        # Keep cycling the buffer until frame starts
        self.read_until(REF_READ_HEADER,False)

        # Different packet lengths depending on whether engineering mode is on
        if self.eng_mode:
            read_len = REF_ENG_MODE_PACKET_LEN
        else:
            read_len = REF_NORMAL_PACKET_LEN

        try:
            ret_candidate = self.ser.read(read_len)
        except:
            self.debug("Serial failed to read data. Skipping this read")
            return None

        self.debug(f"get_data_frame() returning {ret_candidate.hex(' ')}")

        # Catch engineering mode not set error
        if ret_candidate[REF_ENG_CHECK_IDX] == REF_ENG_CHECK and self.eng_mode == False:  # Engineering mode is on, but not set in driver
            self.log(
                "Data seems to be in engineering mode format. However, driver isn't set to use parse engineering mode. Setting it now")
            self.eng_mode = True
        elif ret_candidate[REF_PACKET_CRC_IDX:] != bytes.fromhex(REF_PACKET_CRC):
            self.log(f'Ignoring packet. Checksum not correct received this packet {ret_candidate.hex(" ")}')
            # raise Exception("Checksum of received data is wrong. Data may be corrupted")

            # dzem: Let's return None, instead of potentially corrupted data.
            # None will force the get_radar_data to read once again.
            return None

        # dzem: testing shows that it may happen return bytes are shorter then required;
        if len(ret_candidate) < read_len:
            self.log(f'Ignoring packet. Packet size is too short: {len(ret_candidate)}')
            return None

        if ret_candidate:
            self.read_fail_count = 0

        return ret_candidate

    # Sets 3 lists (standard, move_energies, static_energies). If engineering mode is disabled, second and third list is empty
    def get_radar_data(self):
        self.debug("Getting raw dataframe")

        # Read the serial port until the end of the buffer -
        # - it is usually something between 340 -360 bytes
        # This way we are making sure the radar data will
        # be most up to date
        self.ser.read(1_000)

        ret = self.get_data_frame()
        while not ret:
            ret = self.get_data_frame()

        move_energies = None
        static_energies = None

        target_type = ret[REF_TARGET_TYPE]  # 0 No Target, 1 Moving, 2 Static, 3 Static + Moving

        moving_target_dist = int(bytes(reversed(ret[REF_TARGET_MOVE_DIST_HEAD:REF_TARGET_MOVE_DIST_TAIL + 1])).hex(), 16)
        moving_target_energy = ret[REF_TARGET_MOVE_ENERGY]

        static_target_dist = int(bytes(reversed(ret[REF_TARGET_STATIC_DIST_HEAD:REF_TARGET_STATIC_DIST_TAIL + 1])).hex(), 16)
        static_target_energy = ret[REF_TARGET_STATIC_ENERGY]

        detection_dist = ret[REF_DETECT_DIST]

        standard_frame = [target_type, moving_target_dist, moving_target_energy, static_target_dist, static_target_energy, detection_dist]

        self.debug(f"Returning dataframes {standard_frame}, {move_energies}, {static_energies}")

        if self.eng_mode:
            # Movement Gate Sensitivities
            move_energies = [int(byte) for byte in ret[REF_MOVING_GATE_ENERGY_0:REF_MOVING_GATE_ENERGY_8 + 1]]
            # Static Gate Sensitivities
            static_energies = [int(byte) for byte in ret[REF_STATIC_GATE_ENERGY_0:REF_STATIC_GATE_ENERGY_8 + 1]]

        return standard_frame, move_energies, static_energies
