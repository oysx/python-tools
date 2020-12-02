import inspect


class MetaClass(type):
    def __new__(mcs, *args, **kwargs):
        # mcs means metaclass
        # args: (class_name, (base_classes_tuple), {namespace_dict})
        print("-".center(len(inspect.stack()), "-")+"In MetaClass.new", mcs, args, kwargs)
        return super(MetaClass, mcs).__new__(mcs, *args, **kwargs)

    def __init__(cls, *args, **kwargs):
        # args: (class_name, (base_classes_tuple), {namespace_dict})
        print("-".center(len(inspect.stack()), "-")+"In MetaClass.init", cls, args, kwargs)

        # Copy parent class'es variable "_params" onto child class
        base_class = cls.__base__
        copied_params = [cls.__name__]
        if hasattr(base_class, "_params"):
            copied_params.extend(base_class._params)
        setattr(cls, "_params", copied_params)

        return super(MetaClass, cls).__init__(*args, **kwargs)

    def __call__(cls, *args, **kwargs):
        print("-".center(len(inspect.stack()), "-")+"In MetaClass.call", cls, args, kwargs)
        return super(MetaClass, cls).__call__(*args, **kwargs)


class TestClass:
    __metaclass__ = MetaClass

    _params = ["TestClass"]

    def __new__(cls, *args, **kwargs):
        print("-".center(len(inspect.stack()), "-")+"In Test.new", cls, args, kwargs)
        return super(TestClass, cls).__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        print("-".center(len(inspect.stack()), "-")+"In Test.init", self, args, kwargs)
        return super(TestClass, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        print("-".center(len(inspect.stack()), "-")+"In Test.call", self, args, kwargs)

    @classmethod
    def add_params(cls, name):
        cls._params.append(name)

    @classmethod
    def show_params(cls):
        print(id(cls._params), cls._params)


class ChildClass(TestClass):
    def doit(self):
        print(id(self._params), self._params)


class GrandChildClass(ChildClass):
    pass


print("*******Start")
test = TestClass()
print("*******TestClass")
test()
print("*******ChildClass")
ChildClass.add_params("ChildClassVar")
test = ChildClass()
print("*******")
TestClass.show_params()
ChildClass.show_params()
test.doit()
GrandChildClass.show_params()

# The result is:
'''
('--In MetaClass.new', <class '__main__.MetaClass'>, ('TestClass', (), {'__module__': '__main__', '__metaclass__': <class '__main__.MetaClass'>, '__new__': <function __new__ at 0x00000000031A45F8>, 'add_params': <classmethod object at 0x00000000030A1978>, '_params': ['TestClass'], '__call__': <function __call__ at 0x00000000031A46D8>, 'show_params': <classmethod object at 0x00000000030A1A98>, '__init__': <function __init__ at 0x00000000031A4668>}), {})
('--In MetaClass.init', <class '__main__.TestClass'>, ('TestClass', (), {'__module__': '__main__', '__metaclass__': <class '__main__.MetaClass'>, '__new__': <function __new__ at 0x00000000031A45F8>, 'add_params': <classmethod object at 0x00000000030A1978>, '_params': ['TestClass'], '__call__': <function __call__ at 0x00000000031A46D8>, 'show_params': <classmethod object at 0x00000000030A1A98>, '__init__': <function __init__ at 0x00000000031A4668>}), {})
('--In MetaClass.new', <class '__main__.MetaClass'>, ('ChildClass', (<class '__main__.TestClass'>,), {'doit': <function doit at 0x00000000031A4C18>, '__module__': '__main__'}), {})
('--In MetaClass.init', <class '__main__.ChildClass'>, ('ChildClass', (<class '__main__.TestClass'>,), {'doit': <function doit at 0x00000000031A4C18>, '__module__': '__main__'}), {})
('--In MetaClass.new', <class '__main__.MetaClass'>, ('GrandChildClass', (<class '__main__.ChildClass'>,), {'__module__': '__main__'}), {})
('--In MetaClass.init', <class '__main__.GrandChildClass'>, ('GrandChildClass', (<class '__main__.ChildClass'>,), {'__module__': '__main__'}), {})
*******Start
('--In MetaClass.call', <class '__main__.TestClass'>, (), {})
('---In Test.new', <class '__main__.TestClass'>, (), {})
('---In Test.init', <__main__.TestClass object at 0x00000000031A5788>, (), {})
*******TestClass
('--In Test.call', <__main__.TestClass object at 0x00000000031A5788>, (), {})
*******ChildClass
('--In MetaClass.call', <class '__main__.ChildClass'>, (), {})
('---In Test.new', <class '__main__.ChildClass'>, (), {})
('---In Test.init', <__main__.ChildClass object at 0x00000000031A5B08>, (), {})
*******
(51644424L, ['TestClass'])
(51629512L, ['ChildClass', 'TestClass', 'ChildClassVar'])
(51629512L, ['ChildClass', 'TestClass', 'ChildClassVar'])
(51627272L, ['GrandChildClass', 'ChildClass', 'TestClass'])
'''