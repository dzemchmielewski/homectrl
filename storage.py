from datetime import datetime

import peewee
from peewee import Model, CharField, DateTimeField, DecimalField, BooleanField, IntegerField, TextField, ForeignKeyField

from configuration import Configuration

db = Configuration.get_database_config()
database = peewee.PostgresqlDatabase(db["db"], user=db["username"], password=db["password"], host=db["host"], port=db["port"], autorollback=True)


def entities():
    return subclasses(BaseModel)


def on_start():
    with database:
        database.create_tables(entities())
        for name in [["kitchen", "Kitchen"], ["radio", "Radio"], ["pantry", "Pantry"], ["wardrobe", "Wardrobe"]]:
            try:
                Name.create(value=name[0], description=name[1])
            except:
                pass


class StorageError(BaseException):
    def __init__(self, value):
        self.value = value


class BaseModel(Model):
    class Meta:
        database = database


class Name(BaseModel):
    value = CharField(max_length=25, primary_key=True)
    description = TextField(null=True)

    @classmethod
    def get_last(cls, name=None):
        return None


class HomeCtrlBaseModel(BaseModel):
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

    @classmethod
    def get_currents(cls):
        with database:
            subq = (cls.select(peewee.fn.row_number().over(partition_by=cls.name_id, order_by=[cls.create_at.desc()]).alias("row_num"), cls))
            query = (peewee.Select(columns=[subq.c.id, subq.c.create_at, subq.c.name_id, subq.c.value])
                     .from_(subq)
                     .where(subq.c.row_num == 1)
                     .bind(database))
            return list(map(lambda r: cls(**r), query))


class Temperature(HomeCtrlValueBaseModel):
    name = ForeignKeyField(Name)
    value = DecimalField(decimal_places=2)


class Humidity(HomeCtrlValueBaseModel):
    name = ForeignKeyField(Name)
    value = DecimalField(decimal_places=2)


class Darkness(HomeCtrlValueBaseModel):
    name = ForeignKeyField(Name, on_update='CASCADE')
    value = BooleanField()


class Light(HomeCtrlValueBaseModel):
    name = ForeignKeyField(Name)
    value = BooleanField()


class Presence(HomeCtrlValueBaseModel):
    name = ForeignKeyField(Name)
    value = BooleanField()


class Pressure(HomeCtrlValueBaseModel):
    name = ForeignKeyField(Name)
    value = DecimalField(decimal_places=2)


class Live(HomeCtrlValueBaseModel):
    name = ForeignKeyField(Name)
    value = BooleanField()

    @classmethod
    def get_currentsAAAA(cls):
        with database:
            subq = (Live.select(peewee.fn.row_number().over(partition_by=Live.name_id, order_by=[Live.create_at.desc()]).alias("row_num"), Live))
            query = (peewee.Select(columns=[subq.c.id, subq.c.create_at, subq.c.name_id, subq.c.value])
                     .from_(subq)
                     .where(subq.c.row_num == 1)
                     .bind(database))
            return list(map(lambda r: Live(**r), query))


class Radio(HomeCtrlBaseModel):
    name = ForeignKeyField(Name)
    station_name = TextField()
    station_code = TextField()
    volume = IntegerField(null=True)
    muted = BooleanField(null=True)
    playinfo = TextField()


class Radar(HomeCtrlBaseModel):
    name = ForeignKeyField(Name)
    presence = BooleanField()
    target_state = IntegerField()
    # move_distance = IntegerField()
    # move_energy = IntegerField()
    # static_distance = IntegerField()
    # static_energy = IntegerField()
    distance = IntegerField()

    def save_new_value(self):
        previous = self.__class__.get_last(self.name)
        if previous is None or previous.presence != self.presence or previous.target_state != self.target_state or previous.distance != self.distance:
            return self.save()
        return None


def save(data: dict):
    try:
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
            elif key == "presence":
                Presence.save_new_value(name=name, create_at=timestamp, value=value)
            elif key == "pressure":
                Pressure.save_new_value(name=name, create_at=timestamp, value=value)
            elif key == "radar":
                Radar(name=name, create_at=timestamp,
                      presence=value["presence"], target_state=value["target_state"],
                      # move_distance=value["move"]["distance"], move_energy=value["move"]["energy"],
                      # static_distance=value["static"]["distance"], static_energy=value["static"]["energy"],
                      distance=value["distance"]).save_new_value()
            elif key == "radio":
                Radio(name=name, create_at=timestamp,
                      station_name=value["station"]["name"], station_code=value["station"]["code"],
                      volume=value["volume"]["volume"], muted=value["volume"]["is_muted"], playinfo=value["playinfo"]).save()
    except BaseException as error:
        raise StorageError(f"Following error:\"{error}\" occurred while saving data: {data}")


def subclasses(cls):
    result = []
    for subclass in cls.__subclasses__():
        if "BaseModel" not in subclass.__name__:
            result.append(subclass)
        result = result + subclasses(subclass)
    return result


on_start()

if __name__ == "__main__":

    import logging
    logger = logging.getLogger('peewee')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)

    #Name.create(value="test", description="TEST")
    #Light(name="test", create_at=datetime.now(), value=True).save()

    # Darkness.create(name='kitchen', create_at=datetime.now(), value=True)
    # Darkness.create(name='kitchen', create_at=datetime.now(), value=False)

    # Temperature(name="TEST", create_at=datetime.now(), value=121).save()
    # Temperature(name="TEST", create_at=datetime.now(), value=122).save()
    # print("Temperature saved")
    # q = Temperature.select().order_by(Temperature.create_at.desc()).limit(1).get()


    print("OK")
