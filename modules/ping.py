import io
import os
import subprocess
import time
from common.common import Common


class Ping(Common):

    def __init__(self, name, ip, debug=False):
        super().__init__(name if name is not None else "PING{}".format(ip), debug=debug)
        self.ip = ip
        self.last_result = -1

    def is_up(self):
        result = self._ping()
        if self.last_result != result:
            if self.last_result == 1:
                # Confirm the ON -> OFF change
                # sleep, and try again:
                time.sleep(1)
                result = self._ping()
            self.last_result = result
        return self.last_result

    def _ping(self):
        with io.open(os.devnull, 'wb') as devnull:
            try:
                subprocess.check_call(
                    ['ping', '-c1', self.ip],
                    stdout=devnull, stderr=devnull)
            except subprocess.CalledProcessError:
                return 0
            else:
                return 1
