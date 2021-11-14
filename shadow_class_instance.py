import sys
import inspect
import six

class meta(type):
    def __instancecheck__(self, instance):
        if instance.__class__ is self:
            return True
        elif instance.__class__ is snapshot:
            # pretend to be a instance of "module"
            return True
        return False


@six.add_metaclass(metaclass=meta)
class base(object):
    @property
    def val(self):
        return base.__name__

class module(base):
    def __init__(self):
        self.__dict__["name"] = "vv"
        self.i = 1

    def checkpoint(self):
        return snapshot(self)

    def get(self):
        return self.i+1

    @property
    def name(self):
        self.__dict__["name"] = "vv"
        return self.__class__.__name__



class snapshot(object):
    def __init__(self, proxy):
        # self.__dict__["name"] = 1
        # proxy the input object
        self.proxy = proxy

        # lookup all "property" decorated attributes and create corresponding attributes in this object
        # for k in dir(self.proxy):
        #     if isinstance(getattr(self.proxy.__class__, k, None), property):
        #         print("Proxy: {}".format(k))
        #         setattr(self, k, None)  # add placeholder

    def __enter__(self):
        # iterate all local variables in the caller frame and find out whose value is the original module object
        # and then save found objects and their variable names
        # and replace these found local variables value to self
        frame = inspect.stack()[1]
        variables = frame[0].f_locals
        for k, v in variables.items():
            if v is self.proxy:
                print("Found: {}:{}".format(k, v))
                self.saved = {k: v}
                variables[k] = self

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # restore all local variables in the caller frame
        variables = inspect.stack()[1][0].f_locals
        for k, v in self.saved.items():
            variables[k] = v

    def __getattr__(self, item):
        # any not found attributes and methods will be routed to original object
        return getattr(self.proxy, item)

    def __repr__(self):
        return self.proxy.__repr__()

    def refresh(self):
        # update cache property decorated values in this object
        pass

b =c= module()
a=b
print(b.name)
print(b.name)
print(b.name)

# object "b" is instance of "module"
with b.checkpoint():
    # object "b" is changed to instance of "snapshot"
    print("***IN***")
    print(isinstance(b, module))
    print(b)
    print(b.i)  # access "snapshot" attribute "i" will goto "__getattr__"
    print(b.get())  # access "snapshot" method "get" will goto "__getattr__"
    print(b.name)   # access "snapshot" attribute "name" will retrieve from itself's attribute "name"

# object "b" is restored as instance of "module"
print("***OUT***")
print(isinstance(b, module))
print(b)
print(b.i)
print(b.get())
print(b.name)
