import types
import sys


class ByteCode(object):
    def __init__(self, filename):
        self.filename = filename
        with open(filename, "r") as f:
            self.text = f.read()
        self.code = None

    def parse(self):
        self.code = compile(self.text, self.filename, 'exec')

        """Iterate over all the code objects in `code`."""
        stack = [self.code]
        while stack:
            # We're going to return the code object on the stack, but first
            # push its children for later returning.
            code = stack.pop()
            for c in code.co_consts:
                if isinstance(c, types.CodeType):
                    stack.append(c)
            yield code


if __name__ == "__main__":
    bytecode = ByteCode(sys.argv[1])
    for code in bytecode.parse():
        # print out each callable definition including <module>, class, function
        print(code)

