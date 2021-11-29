def fake_function_one(name):
    print("fake_function_one with %s" % name)

import os


def fake_decorator_one(func):
    def _wrapper(*args, **kwargs):
        print("Before %s" % str(func))
        result = func(*args, **kwargs)
        print("After %s" % str(func))
        return result
    return _wrapper


def fake_decorator_two(func):
    def _wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return _wrapper


class FakeClassOne(object):
    def __init__(self):
        self._property_two = 2
        print("FakeClassOne __init__")

    def doit(self, name):
        print("%s: doit with %s" % (self.__class__.__name__, name))

    @staticmethod
    def static_method_one(name):
        print("%s: static_method_one with %s" % (FakeClassOne.__name__, name))

    @classmethod
    def class_method_one(cls, name):
        print("%s: class_method_one with %s" % (cls.__name__, name))

    @property
    def property_one(self):
        print("%s: property_one" % self.__class__.__name__)
        return 1

    @property
    def property_two(self):
        print("%s: property_two's get" % self.__class__.__name__)
        return self._property_two

    @property_two.setter
    def property_two(self, value):
        print("%s: property_two's set with %s" % (self.__class__.__name__, value))
        self._property_two = value

    @fake_decorator_two
    @fake_decorator_one
    def custom_wrapped_function(self, name):
        print("%s: custom_wrapped_function with %s" % (self.__class__.__name__, name))
        return name


def fake_function_two():
    print("fake_function_two")
