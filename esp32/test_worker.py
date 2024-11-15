from board.worker import MQTTWorker


class TestWorker(MQTTWorker):

    def __init__(self, debug=False):
        super().__init__("test", debug)

        worker_data = self.get_data()
        worker_data.data = {
            "process": None,
        }

    def start(self):
        self.begin()
        worker_data = self.get_data()

        while self.keep_working():
            try:
                publish = False

                # Save last process readable time
                worker_data.data["process"] = self.the_time_str()

                if publish:
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()

            except BaseException as e:
                self.handle_exception(e)

        self.end()
