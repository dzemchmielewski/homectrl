import os
from datetime import datetime
from peewee import SqliteDatabase, Model, CharField, DateTimeField, DecimalField, BooleanField, IntegerField, TextField


DATABASE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "homectrl.db")
database = SqliteDatabase(DATABASE)

class BaseModel(Model):
    class Meta:
        database = database


class HomeCtrlBaseModel(BaseModel):
    name = CharField()
    create_at = DateTimeField()

    @classmethod
    def get_last(cls):
        return cls.select().order_by(cls.create_at.desc()).limit(1).get_or_none()


class HomeCtrlValueBaseModel(HomeCtrlBaseModel):

    @classmethod
    def save_new_value(cls, name, create_at, value):
        previous = cls.get_last()
        if previous is None or previous.value != value:
            return cls.create(name=name, create_at=create_at, value=value)
        return None


class Error(HomeCtrlBaseModel):
    value = TextField()


class Temperature(HomeCtrlValueBaseModel):
    value = DecimalField(decimal_places=2)


class Humidity(HomeCtrlValueBaseModel):
    value = DecimalField(decimal_places=2)


class Daylight(HomeCtrlValueBaseModel):
    value = BooleanField()


class Lights(HomeCtrlValueBaseModel):
    value = BooleanField()


class Entry(HomeCtrlValueBaseModel):
    value = BooleanField()


class Movement(HomeCtrlValueBaseModel):
    value = BooleanField()
    type = IntegerField()
    energy = DecimalField(decimal_places=2)
    distance = DecimalField(decimal_places=2)
    # TODO: override 'save_new_value' method


def error(name: str, error: str, timestamp: datetime = datetime.now()):
    Error.create(name=name, timestamp=timestamp, value=error)


def save(data: dict):
    name = data.get("name")
    if (timestamp := data.get("timestamp")) is None:
        timestamp = datetime.now()

    for key, value in data.items():
        if key == "temperature":
            Temperature.save_new_value(name=name, create_at=timestamp, value=value)
        elif key == "humidity":
            Humidity.save_new_value(name=name, create_at=timestamp, value=value)
        elif key == "lights":
            Lights.save_new_value(name=name, create_at=timestamp, value=value)
        elif key == "entry":
            Entry.save_new_value(name=name, create_at=timestamp, value=value)
        elif key == "movement":
            if isinstance(value, dict):
                Movement.create(name=name, create_at=timestamp,
                                value=value.get("value"), type=value.get("type"),
                                energy=value.get("energy"), distance=value.get("distance"))
                pass
            else:
                Movement.create(name=name, create_at=timestamp, value=value)


def create_tables():
    with database:
        database.create_tables([Temperature, Humidity, Daylight, Lights, Entry, Movement, Error])


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

    Temperature.save_new_value(b.name, b.create_at, b.value)
    Lights.save_new_value("test", datetime.now(), 1)
    print("OK")