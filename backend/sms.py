import datetime
from urllib import parse, request, error
from configuration import Configuration

import logging
logger = logging.getLogger(__name__)

class SMS:

    def __init__(self):
        conf = Configuration.get_sms_config()
        self.headers = {"Content-Type": "application/x-www-form-urlencoded",
                        "Authorization": "Bearer {}".format(conf["sms_token"])}
        self.url = "https://api2.smsplanet.pl/"
        self.sender = conf["sms_sender"]
        self.recipients = conf["sms_recipients"]

    def _smsplanet_post(self, method, data):
        try:
            req = request.Request(self.url + method, headers=self.headers, data=parse.urlencode(data).encode())
            resp = request.urlopen(req)
            return resp.read().decode(resp.headers.get_content_charset())

        except error.URLError as e:
            logger.fatal("Error sending SMS: " + str(e))

    def _smsplanet_get(self, method, data):
        try:
            logger.info("URL call: {}".format(self.url + method + "?" + parse.urlencode(data)))
            req = request.Request(self.url + method + "?" + parse.urlencode(data), headers=self.headers)
            resp = request.urlopen(req)
            return resp.read().decode()

        except error.URLError as e:
            logger.fatal("Error sending SMS: " + str(e))

    def laundry(self):
        logger.info("Sending laundry SMS...")
        msg = "Pranie trzeba ogarnąć. Godzina: {} ref: http://status.home/".format(datetime.datetime.now().strftime("%H:%M"))
        result = self._smsplanet_post("sms", {"from": self.sender, "to": self.recipients, "msg": msg})
        logger.info("Sending laundry SMS: {}".format(result))
        return result

    def balance(self):
        return self._smsplanet_post("getBalance", {"product": "SMS"})

    def parts_count(self, message):
        return self._smsplanet_get("sms/parts-count", {"content": message})
