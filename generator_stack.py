class GeneratorStack(object):
    def __init__(self, generators):
        self.generators = [g() for g in generators]
        self.stack = []

    def __enter__(self):
        try:
            for gen in self.generators:
                next(gen)
                self.stack.insert(0, gen)
        except Exception as e:
            print("ENTER-----------: {}".format(e))
            exc = sys.exc_info() if not isinstance(e, StopIteration) else (None, None, None)
            ret = self.__exit__(*exc)
            if isinstance(e, StopIteration):
                # Stop iteration when there are exception occur in the __enter__ stage.
                raise e
            elif not ret:
                raise

        return self

    def __exit__(self, *exc):
        original_exc = exc
        for gen in self.stack:
            try:
                if not exc[0]:
                    # exit without exception
                    print("NEXT")
                    next(gen)
                else:
                    print("THROW", exc)
                    gen.throw(*exc)
            except StopIteration as e:
                print("stop_iteration---------------")
                # When one of the context manager cancel the exception in its __exit__(), it will raise this one on next() call
                exc = None, None, None
            except Exception as e:
                print("+++++++++", e)
                exc = sys.exc_info()
                print(exc)
            else:
                exc = None, None, None

        self.stack = []

        if not exc[1]:
            # If there is no exception finally (for example, some context manager cancel throwing exception)
            return True
        elif exc[1] and original_exc[1] is not exc[1]:
            # on the teardown stage, there is a new exception occur
            raise exc[0](exc[1]).with_traceback(exc[2])

####### The following is used to test the above class functionality.
# uncomment those 'raise ValueError' lines and replace the line '# with Ignorer()' to test for different scenario.

import sys

class Counter(object):
    count = 0

    def __enter__(self):
        Counter.count += 1
        print('C: enter', self.count, self)
        return self

    def __exit__(self, *exc):
        print('C: exit', self.count, self, exc)
        Counter.count -= 1
        return False

class Derivated(Counter):
    pass

class ErrorThrower(object):
    def __enter__(self):
        print("E:enter")
        # raise ValueError("E: enter")
        return self

    def __exit__(self, *exc):
        print("E:exit", exc)
        # raise ValueError("E: exit")

class Ignorer(Counter):
    def __exit__(self, *exc):
        print("I:exit", exc)
        return True

def gen_x():
    with Counter():
        with Counter():
            print("x.IN", Counter.count)
            yield
            print("x.OUT", Counter.count)

def gen_y():
    with Counter():
        with Counter():  # with Ignorer():
            with ErrorThrower():
                with Derivated():
                    print("y.IN", Derivated.count)
                    # raise ValueError()
                    yield
                    print("y.OUT", Derivated.count)

def test():
    g = GeneratorStack([gen_x, gen_y])
    with g:
        print("IN----------test")
        # raise ValueError('x,y')
        print("AFTER----------test")

try:
    test()
except:
    print(sys.exc_info())
    raise

print("main exit")
