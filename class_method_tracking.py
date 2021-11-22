from six import add_metaclass
from functools import partial


class MethodTracking(object):
    def __init__(self, cls_name, func):
        self.cls_name = cls_name
        self.func = func
        self.name = func.__name__ if hasattr(func, '__name__') else func.__func__.__name__

    def __call__(self, *args, **kwargs):
        print("Starting {}.{}".format(self.cls_name, self.name))
        result = self.inner(*args, **kwargs)
        print("Ending {}.{}".format(self.cls_name, self.name))
        return result

    def __get__(self, instance, owner):
        if isinstance(self.func, classmethod):
            self.inner = self.func.__get__(instance, owner)
            param = None    # the returned object is already instancemethod
        elif isinstance(self.func, staticmethod):
            self.inner = self.func.__get__(instance, owner)
            param = None
        else:   # instancemethod
            self.inner = self.func
            param = instance
        return self.__call__ if param is None else partial(self.__call__, param)


class MetaClass(type):
    def __init__(cls, *args, **kwargs):
        print(cls, args, kwargs)
        super(MetaClass, cls).__init__(*args, **kwargs)

    def __new__(mcs, *args, **kwargs):
        print(mcs, args, kwargs)
        properties = args[2] if len(args) >= 3 else {}
        for k, v in properties.items():
            if True:#if k != "__new__" and k != "__init__":
                if isinstance(v, type(lambda: None)) or isinstance(v, staticmethod) or isinstance(v, classmethod):
                    properties[k] = MethodTracking(args[0], v)

        return super(MetaClass, mcs).__new__(mcs, *args, **kwargs)

    def metaclass_method(cls):
        print("method in metaclass", cls)


@add_metaclass(MetaClass)
class SuperClass(object):
    def __init__(self, *args, **kwargs):
        super(SuperClass, self).__init__(*args, **kwargs)

    def __new__(cls, *args, **kwargs):
        print(cls, args, kwargs)
        return super(SuperClass, cls).__new__(cls, *args, **kwargs)

    def superclass_method(self):
        print("method in superclass", self)


class MainClass(SuperClass):
    def __init__(self, *args, **kwargs):
        self.param = None
        super(MainClass, self).__init__(*args, **kwargs)

    def method(self):
        print("method: ", self.param)

    @classmethod
    def class_method(cls):
        print("class_method")

    @staticmethod
    def static_method():
        print("static_method")


obj = MainClass()
obj.method()
obj.superclass_method()
obj.static_method()
MainClass.static_method()
obj.class_method()
MainClass.class_method()




