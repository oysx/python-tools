from threading import Thread
import os
import sys
import time

class Test1(Thread):
    def run(self) -> None:
        print("Test1 Starting")
        time.sleep(10)
        print("Test1 Ending")

class Test2(Thread):
    def run(self) -> None:
        print("Test2 Starting")
        time.sleep(10)
        print("Test2 Ending")

import signal

def sigint(num, frame):
    print("Signal: {}, {}".format(num, frame))


signal.signal(signal.SIGINT, sigint)
signal.signal(signal.SIGTERM, signal.SIG_IGN)

t1 = Test1()
t2 = Test2()

t1.start()
t2.start()

print("main starting")
time.sleep(1)
print("kill to thread")
signal.pthread_kill(t1.ident, signal.SIGTERM)
print("main to sleep")
time.sleep(10)

print("main ending")
