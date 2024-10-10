import datetime
from enum import Enum
from typing import Any, Type, Self

from io import BytesIO

import peewee
from peewee import Model, CharField, DateTimeField, DecimalField, BooleanField, IntegerField, TextField, ForeignKeyField, BlobField
from playhouse.shortcuts import model_to_dict

from configuration import Configuration

db = Configuration.get_database_config()
database = peewee.PostgresqlDatabase(db["db"], user=db["username"], password=db["password"], host=db["host"], port=db["port"],
                                     autorollback=True)


def on_start():
    with database:
        database.create_tables(entities())
    with database:
        for name in [["kitchen", "Kitchen"], ["radio", "Radio"], ["pantry", "Pantry"], ["wardrobe", "Wardrobe"], ["dev", "Dev"], ["bathroom", "Bathroom"]]:
            try:
                Name.get_or_create(value=name[0], description=name[1])
            except BaseException as e:
                print("Exc: {}".format(e))
                pass


class EnumField(CharField):

    def __init__(self, enum: type[Enum], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not issubclass(enum, Enum):
            raise TypeError("enum must be a subclass of Enum")
        self.enum = enum

    def db_value(self, member: Enum) -> Any:
        if member is None:
            return None
        if not isinstance(member, self.enum):
            raise TypeError(f"Expected a member of {self.enum.__name__}, got {type(member).__name__}")
        return super().db_value(member.value)

    def python_value(self, value: Any) -> Any:
        if value is None and self.null:
            return None
        try:
            return self.enum(value)
        except KeyError as err:
            raise peewee.IntegrityError(
                f"Value '{value}' is not a valid member name of '{self.enum.__name__}'"
            ) from err


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


class Laundry(BaseModel):
    start_at = DateTimeField()
    end_at = DateTimeField(null=True)
    start_energy = IntegerField()
    end_energy = IntegerField(null=True)

    @classmethod
    def get_last(cls) -> Self:
        return cls.select().order_by(cls.start_at.desc()).limit(1).get_or_none()

    def is_active(self):
        return self.start_energy is not None and self.end_at is None


class HomeCtrlBaseModel(BaseModel):
    name = ForeignKeyField(Name, on_update='CASCADE')
    create_at = DateTimeField()

    def save_new_value(self) -> Self:
        previous = self.get_last(self.name.value)
        if not self.equals(previous):
            return self.save(force_insert=True)
        return None

    @classmethod
    def get_last(cls, name=None):
        if not name:
            return cls.select().order_by(cls.create_at.desc()).limit(1).get_or_none()
        else:
            return cls.select().where(cls.name == name).order_by(cls.create_at.desc()).limit(1).get_or_none()

    @classmethod
    def get_lasts(cls, name: str, from_date: datetime.datetime = None, to_date: datetime.datetime = None):
        return (cls.select()
                .where(cls.name == name, from_date is None or cls.create_at >= from_date, to_date is None or cls.create_at <= to_date)
                .order_by(cls.create_at.asc()))


class HomeCtrlValueBaseModel(HomeCtrlBaseModel):

    @classmethod
    def get_currents(cls):
        with database:
            subq = (
                cls.select(peewee.fn.row_number().over(partition_by=cls.name_id, order_by=[cls.create_at.desc()]).alias("row_num"), cls))
            query = (peewee.Select(columns=[subq.c.id, subq.c.create_at, subq.c.name_id, subq.c.value])
                     .from_(subq)
                     .where(subq.c.row_num == 1)
                     .bind(database))
            return list(map(lambda r: cls(**r), query))

    def equals(self, other: Self) -> bool:
        return other and type(other) is type(self) and self.value == other.value


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


class Pressure(HomeCtrlValueBaseModel):
    value = DecimalField(decimal_places=2)


class Voltage(HomeCtrlValueBaseModel):
    value = DecimalField(decimal_places=2)

class Live(HomeCtrlValueBaseModel):
    value = BooleanField()

    @classmethod
    def get_currentsAAAA(cls):
        with database:
            subq = (Live.select(peewee.fn.row_number().over(partition_by=Live.name_id, order_by=[Live.create_at.desc()]).alias("row_num"),
                                Live))
            query = (peewee.Select(columns=[subq.c.id, subq.c.create_at, subq.c.name_id, subq.c.value])
                     .from_(subq)
                     .where(subq.c.row_num == 1)
                     .bind(database))
            return list(map(lambda r: Live(**r), query))


class Radio(HomeCtrlBaseModel):
    station_name = TextField()
    station_code = TextField()
    volume = IntegerField(null=True)
    muted = BooleanField(null=True)
    playinfo = TextField(null=True)

    def equals(self, other: Self) -> bool:
        return (other and type(other) is type(self)
                and other.station_name == self.station_name and other.station_code == self.station_code
                and other.volume == self.volume and other.muted == self.muted
                and other.playinfo == self.playinfo)

    @classmethod
    def get_currents(cls):
        with database:
            subq = (
                cls.select(peewee.fn.row_number().over(partition_by=cls.name_id, order_by=[cls.create_at.desc()]).alias("row_num"), cls))
            query = (peewee.Select(columns=[subq.c.id, subq.c.create_at, subq.c.name_id,
                                            subq.c.station_name, subq.c.station_code, subq.c.volume,
                                            subq.c.muted, subq.c.playinfo])
                     .from_(subq)
                     .where(subq.c.row_num == 1)
                     .bind(database))
            return list(map(lambda r: cls(**r), query))


class Radar(HomeCtrlBaseModel):
    presence = BooleanField()
    target_state = IntegerField()
    # move_distance = IntegerField()
    # move_energy = IntegerField()
    # static_distance = IntegerField()
    # static_energy = IntegerField()
    distance = IntegerField()

    def equals(self, other: Self) -> bool:
        return (other and type(other) is type(self)
                and other.presence == self.presence and other.target_state == self.target_state and other.distance == self.distance)

    @classmethod
    def get_currents(cls):
        with database:
            subq = (
                cls.select(peewee.fn.row_number().over(partition_by=cls.name_id, order_by=[cls.create_at.desc()]).alias("row_num"), cls))
            query = (peewee.Select(columns=[subq.c.id, subq.c.create_at, subq.c.name_id,
                                            subq.c.presence, subq.c.target_state, subq.c.distance])
                     .from_(subq)
                     .where(subq.c.row_num == 1)
                     .bind(database))
            return list(map(lambda r: cls(**r), query))


class Electricity(HomeCtrlBaseModel):
    voltage = DecimalField(decimal_places=2)
    current = DecimalField(decimal_places=3)
    active_power = DecimalField(decimal_places=2)
    active_energy = IntegerField()
    power_factor = DecimalField(decimal_places=3)

    def equals(self, other: Self) -> bool:
        return (other and type(other) is type(self)
                and other.voltage == self.voltage and other.current == self.current and other.active_power == self.active_power
                and other.active_energy == self.active_energy and other.power_factor == self.power_factor)

    @classmethod
    def get_currents(cls):
        with database:
            subq = (
                cls.select(peewee.fn.row_number().over(partition_by=cls.name_id, order_by=[cls.create_at.desc()]).alias("row_num"), cls))
            query = (peewee.Select(columns=[subq.c.id, subq.c.create_at, subq.c.name_id,
                                            subq.c.voltage, subq.c.current, subq.c.active_power,
                                            subq.c.active_energy, subq.c.power_factor])
                     .from_(subq)
                     .where(subq.c.row_num == 1)
                     .bind(database))
            return list(map(lambda r: cls(**r), query))


class ChartPeriod(Enum):
    hours24 = "24 hours"
    days7 = "7 days"
    month1 = "1 month"

    @classmethod
    def from_str(cls, name: str):
        return cls.__getitem__(name)


class FigureCache(BaseModel):
    name = ForeignKeyField(Name, on_update='CASCADE')
    model = TextField()
    period = EnumField(ChartPeriod, max_length=8)
    data = BlobField()
    create_at = DateTimeField()

    @classmethod
    def get_last(cls, model: Any, period: ChartPeriod, name: str):
        if not isinstance(model, str):
            model = model.__name__
        return (FigureCache
                .select()
                .where(FigureCache.model == model, FigureCache.period == period, FigureCache.name == name)
                .get_or_none())

    def getvalue(self):
        result = BytesIO()
        result.write(self.data)
        return result.getvalue()


# def save(data: dict):
#     try:
#         name = data.get("name")
#
#         if (timestamp := data.get("timestamp")) is None:
#             timestamp = datetime.datetime.now()
#
#         Live.save_new_value(name=name, create_at=timestamp, value=data.get("live") is None or data.get("live"))
#
#         for key, value in data.items():
#             if key == "temperature":
#                 Temperature.save_new_value(name=name, create_at=timestamp, value=value)
#             elif key == "humidity":
#                 Humidity.save_new_value(name=name, create_at=timestamp, value=value)
#             elif key == "darkness":
#                 Darkness.save_new_value(name=name, create_at=timestamp, value=value)
#             elif key == "light":
#                 Light.save_new_value(name=name, create_at=timestamp, value=value)
#             elif key == "presence":
#                 Presence.save_new_value(name=name, create_at=timestamp, value=value)
#             elif key == "pressure":
#                 Pressure.save_new_value(name=name, create_at=timestamp, value=value)
#             elif key == "voltage":
#                 Voltage.save_new_value(name=name, create_at=timestamp, value=value)
#             elif key == "radar":
#                 Radar(name=name, create_at=timestamp,
#                       presence=value["presence"], target_state=value["target_state"],
#                       # move_distance=value["move"]["distance"], move_energy=value["move"]["energy"],
#                       # static_distance=value["static"]["distance"], static_energy=value["static"]["energy"],
#                       distance=value["distance"]).save_new_value()
#             elif key == "radio":
#                 Radio(name=name, create_at=timestamp,
#                       station_name=value["station"]["name"], station_code=value["station"]["code"],
#                       volume=value["volume"]["volume"], muted=value["volume"]["is_muted"], playinfo=value["playinfo"]).save()
#     except BaseException as error:
#         raise StorageError(f"Following error:\"{error}\" occurred while saving data: {data}")


def subclasses(cls):
    result = []
    for subclass in cls.__subclasses__():
        if "BaseModel" not in subclass.__name__:
            result.append(subclass)
        result = result + subclasses(subclass)
    return result


def device_entities() -> [Type[HomeCtrlBaseModel]]:
    return subclasses(HomeCtrlBaseModel)


def entities():
    return subclasses(BaseModel)



on_start()

if __name__ == "__main__":
    import logging

    logger = logging.getLogger('peewee')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)

    #Name.create(value="test", description="TEST")
    #Light(name="test", create_at=datetime.datetime.now(), value=True).save()

    # Darkness.create(name='kitchen', create_at=datetime.now(), value=True)
    # Darkness.create(name='kitchen', create_at=datetime.now(), value=False)

    # Temperature(name="TEST", create_at=datetime.now(), value=121).save()
    # Temperature(name="TEST", create_at=datetime.now(), value=122).save()
    # print("Temperature saved")
    # q = Temperature.select().order_by(Temperature.create_at.desc()).limit(1).get()

#    last_24h = datetime.datetime.now() - datetime.timedelta(hours=12)
#    query = Darkness.select(Presence.create_at, Presence.value).where(Presence.name == "kitchen" and Presence.create_at > last_24h)

    # query = Darkness.get_lasts("kitchen", datetime.datetime.now() - datetime.timedelta(hours=24), datetime.datetime.now())
    # query = Presence.get_lasts("kitchen", datetime.datetime.now() - datetime.timedelta(days=1))


    #print(list(query))
    # for p in query:
    #     print(p.create_at.isoformat(), 1 if p.value else 0)


#    print("OK")
