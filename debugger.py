#!/usr/bin/env python
import sys
import os
import linecache


class Debugger(object):
    GAP = 2

    def __init__(self, prefix=''):
        self.prefix = prefix
        self.space = 0

    def trace_line(self, frame, event, arg):
        if event == 'line':
            self.on_line(frame, event, arg)
            return self.trace_line
        elif event != 'return':
            return self.trace_line

        self.on_call(frame, event, arg)
        self.space -= self.GAP

    def trace_dispatch(self, frame, event, arg):
        if not self.is_concerned(frame):
            # Don't trace in this scope
            return None

        if event == 'call':
            self.space += self.GAP

        self.on_call(frame, event, arg)
        if event == 'return':
            self.space -= self.GAP
        return self.trace_line

    def is_concerned(self, frame):
        if not self.prefix:
            return True
        name = frame.f_globals.get('__name__')
        return name and name.startswith(self.prefix)

    def on_line(self, frame, event, arg):
        if self.scope_module(frame):
            return self.on_line_module(frame, event, arg)
        elif self.scope_class(frame):
            return self.on_line_class(frame, event, arg)

    def on_line_module(self, frame, event, arg):
        pass

    def on_line_class(self, frame, event, arg):
        pass

    def on_call(self, frame, event, arg):
        if self.scope_module(frame):
            return self.on_call_module(frame, event, arg)
        elif self.scope_class(frame):
            return self.on_call_class(frame, event, arg)
        else:
            return self.on_call_function(frame, event, arg)

    def on_call_module(self, frame, event, arg):
        pass

    def on_call_class(self, frame, event, arg):
        pass

    def on_call_function(self, frame, event, arg):
        pass

    def show_common(self, frame, event, arg, extra=''):
        name = frame.f_globals.get('__name__')
        func = frame.f_code.co_name
        line = frame.f_lineno
        print("%s%s: %s in %s:%d, val=%s %s" % (' ' * self.space, event, func, name, line, arg, extra))

    def show_content(self, frame, event, arg):
        fn = frame.f_code.co_filename
        line = frame.f_lineno
        content = linecache.getline(fn, line) if linecache else ''
        self.show_common(frame, event, arg, "\"%s\"" % content)

    @staticmethod
    def scope_module(frame):
        return frame.f_code.co_name == "<module>"

    @staticmethod
    def scope_class(frame):
        # return "__name__" in frame.f_code.co_names
        return "__module__" in frame.f_code.co_names


class DebugClass(Debugger):
    def on_line_class(self, frame, event, arg):
        self.show_content(frame, event, arg)

    def on_call_class(self, frame, event, arg):
        self.show_content(frame, event, arg)
        # print(frame.f_code.co_names)

        if event == 'return':
            self.hijack(arg)

    def hijack(self, arg):
        func = arg.get("doit") if arg else None
        if not func:
            return None

        def _wrapper(*args, **kwargs):
            print("***hijack class successful")
            return func(*args, **kwargs)
        arg['doit'] = _wrapper


class DebugModule(Debugger):
    def __init__(self, *args, **kwargs):
        super(DebugModule, self).__init__(*args, **kwargs)
        self.modules = {}

    def on_line_module(self, frame, event, arg):
        self.show_content(frame, event, arg)

    def on_call_module(self, frame, event, arg):
        self.show_common(frame, event, arg)
        name = frame.f_globals.get('__name__')
        if event == 'call':
            self.modules[name] = dir(sys.modules.get(name))
        if event == 'return':
            modules = dir(sys.modules.get(name))
            print(set(modules) - set(self.modules))

            self.hijack(sys.modules.get(name))

    def hijack(self, module):
        name = 'fake_function_one'
        func = getattr(module, name, None)
        if not func:
            return

        def _wrapper(*args, **kwargs):
            print("###hijack module successful")
            return func(*args, **kwargs)

        setattr(module, name, _wrapper)


class DebugFunction(Debugger):
    def on_call_function(self, frame, event, arg):
        self.show_common(frame, event, arg)


class DebugEverythink(Debugger):
    def trace_line(self, frame, event, arg):
        self.show_common(frame, event, arg)
        if event == 'return':
            self.space -= self.GAP
        return self.trace_line

    def trace_dispatch(self, frame, event, arg):
        if event == 'call':
            self.space += self.GAP
            print(frame.f_code.co_names)
        self.show_common(frame, event, arg)
        if event == 'return':
            self.space -= self.GAP
        return self.trace_line


def main():
    if not sys.argv[1:] or sys.argv[1] in ("--help", "-h"):
        print "usage: debugger.py scriptfile [arg] ..."
        sys.exit(2)

    mainpyfile = sys.argv[1]
    if not os.path.exists(mainpyfile):
        print 'Error:', mainpyfile, 'does not exist'
        sys.exit(1)

    del sys.argv[0]
    sys.path[0] = os.path.dirname(mainpyfile)

    debugger = DebugFunction()

    import __main__
    __main__.__dict__.clear()
    __main__.__dict__.update({"__name__": "__main__",
                              "__file__": mainpyfile,
                              "__builtins__": __builtins__,
                              })

    statement = 'execfile(%r)' % mainpyfile
    # sys.settrace(debugger.trace_dispatch)
    sys.setprofile(debugger.trace_dispatch)

    globals = __main__.__dict__
    locals = __main__.__dict__
    exec statement in globals, locals


if __name__ == '__main__':
    import debugger
    debugger.main()
