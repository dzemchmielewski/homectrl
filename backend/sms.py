from urllib import parse, request, error

from common.common import Common
from configuration import Configuration
import datetime


class SMS(Common):

    def __init__(self):
        super().__init__("SMS")
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
            self.log("Error sending SMS: " + str(e))

    def _smsplanet_get(self, method, data):
        try:
            self.log("URL call: {}".format(self.url + method + "?" + parse.urlencode(data)))
            req = request.Request(self.url + method + "?" + parse.urlencode(data), headers=self.headers)
            resp = request.urlopen(req)
            return resp.read().decode()

        except error.URLError as e:
            print("Error sending SMS: " + str(e))

    def laundry(self):
        self.log("Sending laundry SMS...")
        msg = "Pranie trzeba ogarnąć! Godzina: {} ref: http://status.home/".format(datetime.datetime.now().strftime("%H:%M"))
        result = self._smsplanet_post("sms", {"from": self.sender, "to": self.recipients, "msg": msg})
        self.log("Sending laundry SMS: {}".format(result))
        return result

    def balance(self):
        return self._smsplanet_post("getBalance", {"product": "SMS"})

    def parts_count(self, message):
        return self._smsplanet_get("sms/parts-count", {"content": message})
