from datetime import datetime
from peewee import SqliteDatabase, Model, CharField, DateTimeField, DecimalField, BooleanField, IntegerField, TextField
from homectrl import Configuration

database = SqliteDatabase(Configuration.DATABASE)


class BaseModel(Model):
    class Meta:
        database = database


class HomeCtrlBaseModel(BaseModel):
    name = CharField()
    create_at = DateTimeField()

    @classmethod
    def get_last(cls, name=None):
        if not name:
            return cls.select().order_by(cls.create_at.desc()).limit(1).get_or_none()
        else:
            return cls.select().where(cls.name == name).order_by(cls.create_at.desc()).limit(1).get_or_none()

    @classmethod
    def get_lasts(cls, name: str, from_date:datetime = None, to_date: datetime = datetime.now()):
        return (cls.select()
                .where((cls.name == name) & (cls.create_at >= from_date) & (cls.create_at <= to_date))
                .order_by(cls.create_at.asc()))


class HomeCtrlValueBaseModel(HomeCtrlBaseModel):

    @classmethod
    def save_new_value(cls, name, create_at, value):
        previous = cls.get_last(name)
        if previous is None or previous.value != value:
            return cls.create(name=name, create_at=create_at, value=value)
        return None


class Temperature(HomeCtrlValueBaseModel):
    value = DecimalField(decimal_places=2)


class Humidity(HomeCtrlValueBaseModel):
    value = DecimalField(decimal_places=2)


class Darkness(HomeCtrlValueBaseModel):
    value = BooleanField()


class Light(HomeCtrlValueBaseModel):
    value = BooleanField()


class Presence(HomeCtrlValueBaseModel):
    value = BooleanField()


class Live(HomeCtrlValueBaseModel):
    value = BooleanField()


# Not used yet:
class Error(HomeCtrlBaseModel):
    value = TextField()


class Entry(HomeCtrlValueBaseModel):
    value = BooleanField()


class Radio(HomeCtrlBaseModel):
    station_name = TextField()
    station_code = TextField()
    volume = IntegerField()
    muted = BooleanField()
    playinfo = TextField()


class Radar(HomeCtrlBaseModel):
    presence = BooleanField()
    target_state = IntegerField()
    move_distance = IntegerField()
    move_energy = IntegerField()
    static_distance = IntegerField()
    static_energy = IntegerField()
    distance = IntegerField()


COLLECTIONS = [Temperature, Humidity, Darkness, Light, Live, Entry, Radar, Error, Presence, Radio]


def error(name: str, error: str, timestamp: datetime = datetime.now()):
    Error.create(name=name, timestamp=timestamp, value=error)


def save(data: dict):
    name = data.get("name")

    if (timestamp := data.get("timestamp")) is None:
        timestamp = datetime.now()

    Live.save_new_value(name=name, create_at=timestamp, value=data.get("live") is None or data.get("live"))

    for key, value in data.items():
        if key == "temperature":
            Temperature.save_new_value(name=name, create_at=timestamp, value=value)
        elif key == "humidity":
            Humidity.save_new_value(name=name, create_at=timestamp, value=value)
        elif key == "darkness":
            Darkness.save_new_value(name=name, create_at=timestamp, value=value)
        elif key == "light":
            Light.save_new_value(name=name, create_at=timestamp, value=value)
        elif key == "entry":
            Entry.save_new_value(name=name, create_at=timestamp, value=value)
        elif key == "presence":
            Presence.save_new_value(name=name, create_at=timestamp, value=value)
        elif key == "radar":
            Radar(name=name, create_at=timestamp,
                  presence=value["presence"], target_state=value["target_state"],
                  move_distance=value["move"]["distance"], move_energy=value["move"]["energy"],
                  static_distance=value["static"]["distance"], static_energy=value["static"]["energy"],
                  distance=value["distance"]).save()
        elif key == "radio":
            Radio(name=name, create_at=timestamp,
                  station_name=value["station"]["name"], station_code=value["station"]["code"],
                  volume=value["volume"]["volume"], muted=value["volume"]["is_muted"], playinfo=value["playinfo"]).save()

def create_tables():
    with database:
        database.create_tables(COLLECTIONS)


if __name__ == "__main__":

    import logging
    logger = logging.getLogger('peewee')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)

    create_tables()
    print("Database created")

    # Temperature(name="TEST", create_at=datetime.now(), value=121).save()
    # Temperature(name="TEST", create_at=datetime.now(), value=122).save()
    # print("Temperature saved")

    q = Temperature.select().order_by(Temperature.create_at.desc()).limit(1).get()

    print(q)
    print(type(q))
    print(q.value)

    b = Temperature.get_last()
    print("AAAAAAAAAA: {}".format(b))

    print("OK")
