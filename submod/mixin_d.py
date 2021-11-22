from mixin_test import Base
from logging import error

error("Importing %s" % __name__)


class MixinD(Base):
    def methodB(self):
        error("MixinD: methodB")


