from board.worker import MQTTWorker


class TestWorker(MQTTWorker):

    def __init__(self, debug=False):
        super().__init__("test", debug)

        worker_data = self.get_data()
        worker_data.loop_sleep = 1
        worker_data.data = {
            "process": None,
        }

    def start(self):
        self.begin()
        worker_data = self.get_data()
        i = 0

        while self.keep_working():
            try:
                publish = False

                # Save last process readable time
                worker_data.data["process"] = self.the_time_str()
                i += 1
                if i % 10 == 0:
                    publish = True
                    i = 0

                if publish:
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()

            except BaseException as e:
                self.handle_exception(e)

        self.end()
