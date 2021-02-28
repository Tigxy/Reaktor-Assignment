from enum import Enum


class Availability(Enum):
    UNKNOWN = 0
    OUT_OF_STOCK = 1
    LESS_THAN_10 = 2
    IN_STOCK = 3


def pretty_availability(available):
    return " ".join([word.capitalize() for word in available.name.split('_')])


class UpdateResult(Enum):
    FAILURE = 0
    CHANGED = 1
    ADDED_REMOVED = 2


