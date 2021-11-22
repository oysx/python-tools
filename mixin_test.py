from logging import error as debug
import sys
import util
from submod.mod_j import ModJ

class Base(object):
    def __init__(self):
        debug("Base:__init__")

    def methodA(self):
        debug("Base:methodA")

    def methodB(self):
        debug("Base:methodB")

class ChildX(Base):
    def methodA(self):
        debug("ChildX: methodA")

class ChildY(ChildX):
    def methodB(self):
        debug("ChildY: methodB")

class MixinZ(Base):
    # def methodA(self):
    #     debug("MixinZ: methodA")

    def methodB(self):
        debug("MixinZ: methodB")

class MetaAll(type):
    __classes = {}  # hold all classes created by this meta class

    @staticmethod
    def create(name, bases, mixin, dictionary):
        return MetaAll(name, (mixin,) + bases, dictionary)

    def __new__(mcs, name, bases=(), dct={}):
        if mcs.__classes.get(name, None):
            # Singleton
            return mcs.__classes[name]

        # Use Skeleton as base class
        result = super(MetaAll, mcs).__new__(mcs, name, bases, dct)
        mcs.__classes[name] = result
        return result


def show(base, lvl):
    debug('-'.join(['' for i in range(lvl)])+base.__name__)
    for c in base.__subclasses__():
        show(c, lvl+2)


def main():
    show(Base, 1)
    cls = MetaAll.create("ChildZ", (ChildY,), MixinZ, {})
    debug("OK")
    instance = cls()
    instance.methodA()
    instance.methodB()
    show(Base, 1)
    find()

def find_class(name):
    def _recursive(cls):
        if cls.__name__ == name:
            return cls
        for sub in cls.__subclasses__():
            ret = _recursive(sub)
            if ret:
                return ret

        return None

    return _recursive(Base)

import importlib
def find():

    all = [{'mixin_d': ()}, 'mixin_e', {'mixin_f': ({'ChildY': 'methodA'})}]
    pre = ChildY
    for entity in all:
        name = entity if isinstance(entity, str) else entity.keys()[0]
        try:
            cls_name = "Child"+ name.split('_')[1].upper()
            mix_name = name.split('_')[0][0].upper() + name.split('_')[0][1:] + name.split('_')[1].upper()
            mod = importlib.import_module("submod."+name)
            mixin = getattr(mod, mix_name)

        except Exception as e:
            debug("Ignore "+name)
            continue

        dct = {}
        if isinstance(entity, dict) and entity.values()[0]:
            en = entity.values()[0]
            _cls = find_class(en.keys()[0])
            _med = getattr(_cls, en.values()[0])
            dct = {en.values()[0] : _med}

        cls = MetaAll.create(cls_name, (pre,), mixin, dct)
        ins = cls()
        ins.methodB()
        ins.methodA()

        pre = cls

def tt():
    def aa():
        print("AA")

    return aa

from abc import ABCMeta
from six import add_metaclass

import abc

@add_metaclass(ABCMeta)
class MethodTestClass(object):
    def normal_method(self):
        print(__name__)

    @staticmethod
    def static_method():
        print(__name__)

    # @abc.abstractmethod
    # def abs_method(self):
    #     pass

    def __get__(self, instance, owner):
        print(instance, owner)
        return super(MethodTestClass, self).__get__(instance, owner)


def decorator(*args, **kwargs):
    print("decorator")


def test1():
    bb = MethodTestClass()
    MethodTestClass.static_method()
    save = getattr(MethodTestClass, "static_method")
    static_save = staticmethod(getattr(MethodTestClass, "static_method"))
    get_save = MethodTestClass.static_method
    attr_save = MethodTestClass.__getattribute__(MethodTestClass, "static_method")
    dict_save = MethodTestClass.__dict__["static_method"]
    normal_save = MethodTestClass.normal_method
    cc = decorator
    setattr(MethodTestClass, "static_method", decorator)
    MethodTestClass.static_method()

import time
def test2():
    try:
        time.sleep(10)
    except (KeyboardInterrupt, SystemExit):
        print("Cancel")
        raise

def test3():
    try:
        test2()
    except Exception as e:
        print(e)

class MyType(type):
    pass

@add_metaclass(MyType)
class MyClass:
    def test(self):
        pass

class NormalClass:
    pass

class ObjectClass(object):
    pass

from multiprocessing.process import Process
class BaseCls(object):
    Process = Process

    def test(self):
        print(BaseCls.Process)

class SubCls(BaseCls):
    from submod.mod_j import Process

    def test(self):
        print(super(SubCls, self).Process)
        print(SubCls.Process)
        print(self.Process)

if __name__ == '__main__':
    # main()
    # c=tt()
    # d=tt()
    # print(c==d)
    # test3()


    # print(isinstance(MyType, type))
    # print(isinstance(MethodTestClass, type))
    # print(isinstance(object, type))
    # print(isinstance(MyClass, type))
    # print(isinstance(decorator, type))
    #
    # my_class = MyClass()
    #
    # util.hierarchy(my_class)
    # util.hierarchy(MethodTestClass)
    # util.hierarchy(NormalClass)
    # util.hierarchy(ObjectClass)
    # util.hierarchy(object)
    #
    # MethodTestClass()

    base = BaseCls()
    sub = SubCls()
    base.test()
    sub.test()