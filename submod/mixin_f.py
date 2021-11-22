from mixin_test import Base
from logging import error

error("Importing %s" % __name__)


class MixinF(Base):
    def methodB(self):
        error("MixinF: methodB")

    def methodA(self):
        error("MinxF: methodA")

