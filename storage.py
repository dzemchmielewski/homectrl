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
            return cls.select().where(cls.name == name.upper()).order_by(cls.create_at.desc()).limit(1).get_or_none()

    @classmethod
    def get_lasts(cls, name: str, from_date:datetime = None, to_date: datetime = datetime.now()):
        return (cls.select()
                .where((cls.name == name.upper()) & (cls.create_at >= from_date) & (cls.create_at <= to_date))
                .order_by(cls.create_at.asc()))


class HomeCtrlValueBaseModel(HomeCtrlBaseModel):

    @classmethod
    def save_new_value(cls, name, create_at, value):
        previous = cls.get_last(name)
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


COLLECTIONS = [Temperature, Humidity, Daylight, Lights, Entry, Movement, Error]


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

    Temperature.save_new_value(b.name, b.create_at, b.value)
    Lights.save_new_value("test", datetime.now(), 1)
    print("OK")
