import __builtin__
import sys
from pprint import pformat
import imp
import types

globals().update({"vivi_ident": ""})


def show_ident(func):
    def _wrapper(self, *args, **kwargs):
        g = globals()['vivi_ident']
        globals().update({"vivi_ident": g+"  "})
        result = func(self, *args, **kwargs)
        globals().update({"vivi_ident": g})
        return result
    return _wrapper


class ViMetaPathFinder(object):
    def __init__(self):
        # add meta path finder
        print("meta_path_finders: ", sys.meta_path[:])
        sys.meta_path.append(self)
        # sys.meta_path.insert(0, self)

    @show_ident
    def find_module(self, fullname, path):
        print("%s%s find_module: " % (vivi_ident, self.__class__.__name__), fullname, path)
        return None


class ViPathEntryFinder(object):
    def __init__(self):
        # add path entry finder
        print("%spath_entry_finders: " % vivi_ident, sys.path_hooks)
        print("path_entry_finders_cache: %s" % pformat(sys.path_importer_cache))
        sys.path_hooks.append(self)
        # sys.path_hooks.insert(0, self)

    @show_ident
    def find_module(self, *args, **kwargs):
        fullname = args[0]
        print("%s%s find_module: " % (vivi_ident, self.__class__.__name__), fullname)
        path = []
        for p in fullname.split("."):
            n = ".".join(path)
            if not n:
                n = None
            else:
                n = sys.modules[n].__path__
            path.append(p)
            result = imp.find_module(p, n)
        self.result = result
        return self

    @show_ident
    def load_module(self, fullname):
        print("%s%s load_module" % (vivi_ident, self.__class__.__name__), fullname)
        result = imp.load_module(fullname, *self.result)
        self.hijack_functions(result)
        return result

    def decorator_function(self, func):
        def _wrapper(*args, **kwargs):
            print("=====Entering %s" % func)
            result = func(*args, **kwargs)
            print("#####Exiting %s" % func)
            return result
        return _wrapper

    def hijack_functions(self, obj):
        class Fake(object): pass

        for k, v in vars(obj).items():
            if type(v) == types.FunctionType:
                print("^^^WRAP: %s.%s" % (obj, k))
                setattr(obj, k, self.decorator_function(v))
            elif type(v) == type(Fake):
                self.hijack_functions(v)

    @show_ident
    def __call__(self, *args, **kwargs):
        print("%s%s" % (vivi_ident, self.__class__.__name__), args, kwargs)
        # raise ImportError
        return self


class ViImport(object):
    def __init__(self):
        self.importer = __builtin__.__import__
        # wrap the default builtin __import__ function
        __builtin__.__import__ = self.myImport

        self.meta_path_finder = ViMetaPathFinder()
        self.path_entry_finder = ViPathEntryFinder()

    @show_ident
    def myImport(self, *args, **kwargs):
        name = args[0]
        params = ["name", "globals", "locals", "fromlist", "level"]
        for i, v in enumerate(args):
            params[i] = v
        if len(args) >=5 and args[4] >= 1:
            # handle relative import: args[4] is level, args[1] is globals
            pkg = args[1].get("__package__")
            pkg = pkg.split(".")[:-args[4]+1]
            name = ".".join(pkg+[name])
        print("%sbefore __import__" % vivi_ident, args[0], params[3:], name in sys.modules)
        show = False
        if name not in sys.modules:
            show = True
        result = self.importer(*args, **kwargs)
        if show:
            print("%smyImport(%s):" % (vivi_ident, args[0]), map(lambda x: (x[0], type(x[1])), result.__dict__.items()))
        return result


vi_importer = ViImport()
from fake_module.fake_mod import fake_decorator_one, fake_function_one, FakeClassOne
import six
import ast
import base64
from fake_module.fake_submodule import fake_submod

if __name__ == "__main__":
    print("test import mechanism")
    print("meta path: ", sys.meta_path[:])
    print("path entry: ", sys.path_hooks)
    print("path_entry_finders_cache: %s" % pformat(sys.path_importer_cache))
    fake_function_one("hello")
    cls_one = FakeClassOne()
    cls_one.doit("HELLO")
    cls_one.class_method_one("CLASS")
