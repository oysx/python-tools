from pprint import pprint


class Descriptor(object):
    def __init__(self):
        print(self.__class__.__name__, "init")

    def __set__(self, instance, value):
        print(self, "__set__", instance, value)

    def __get__(self, instance, owner):
        print(self, "__get__", instance, owner)

    def __delete__(self, instance):
        print(self, "__delete__", instance)


class Tester(object):
    descriptor = Descriptor()

    def __getattribute__(self, item):
        print(self, "__getattribute__", item)
        if item == "__class__":
            result = super(Tester, self).__getattribute__(item)
            print("get __class__:", result)
            return result

        if item != '__dict__':
            result = self.__dict__.get(item, "VVVII")
            return result if result != "VVVII" else getattr(type(self), item)
        return super(Tester, self).__getattribute__(item)


    def __setattr__(self, key, value):
        print(self, "__setattr__", key, value)
        self.__dict__[key] = value
        return
        return super(Tester, self).__setattr__(key, value)

    def real_func(self, *args, **kwargs):
        print(self, args, kwargs)


tester = Tester()
print(tester.__dict__)

tester.descriptor
tester.descriptor = 1
print(tester.__dict__)

tester.x = 1
print(tester.__dict__)

print("method:", tester.real_func)
print("method descriptor:", tester.__class__.real_func)
print("method descriptor class:", tester.__class__.real_func.__class__)
pprint(dict(tester.__class__.real_func.__dict__))
pprint(dict(tester.__class__.real_func.__class__.__dict__))


def func():
    pass

print(type(func))
print(type(type(tester).real_func))
print(type(tester).__dict__["real_func"])
print(type(type(tester).__dict__))
# new_instance = Tester()
# print("old:", tester)
# print("new:", new_instance)
tester.real_func(Tester(), 3)
aa=type(tester).real_func
print(aa)