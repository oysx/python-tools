# class A:
#     mm = 10
#
# a = A()
# print(a.mm==A.mm)
# b = A()
# print(b.mm==A.mm)
# a.mm = 20
# print(a.mm==A.mm)
# print(b.mm==A.mm)
#
# print(type(10))
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
        return super(MetaClass, cls).__init__(*args, **kwargs)

    def __call__(cls, *args, **kwargs):
        print("-".center(len(inspect.stack()), "-")+"In MetaClass.call", cls, args, kwargs)
        return super(MetaClass, cls).__call__(*args, **kwargs)


class TestClass:
    __metaclass__ = MetaClass

    def __new__(cls, *args, **kwargs):
        print("-".center(len(inspect.stack()), "-")+"In Test.new", cls, args, kwargs)
        return super(TestClass, cls).__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        print("-".center(len(inspect.stack()), "-")+"In Test.init", self, args, kwargs)
        return super(TestClass, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        print("-".center(len(inspect.stack()), "-")+"In Test.call", self, args, kwargs)


print("*******")
test = TestClass()
print("*******")
test()

# The result is:
'''
('--In MetaClass.new', <class '__main__.MetaClass'>, ('TestClass', (), {'__call__': <function __call__ at 0x0000000003B499E8>, '__module__': '__main__', '__metaclass__': <class '__main__.MetaClass'>, '__new__': <function __new__ at 0x0000000003B49908>, '__init__': <function __init__ at 0x0000000003B49978>}), {})
('--In MetaClass.init', <class '__main__.TestClass'>, ('TestClass', (), {'__call__': <function __call__ at 0x0000000003B499E8>, '__module__': '__main__', '__metaclass__': <class '__main__.MetaClass'>, '__new__': <function __new__ at 0x0000000003B49908>, '__init__': <function __init__ at 0x0000000003B49978>}), {})
('--In MetaClass.call', <class '__main__.TestClass'>, (), {})
('---In Test.new', <class '__main__.TestClass'>, (), {})
('---In Test.init', <__main__.TestClass object at 0x0000000003CFCC48>, (), {})
*******
('--In Test.call', <__main__.TestClass object at 0x0000000003CFCC48>, (), {})
'''