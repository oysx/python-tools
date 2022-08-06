#!/usr/bin/env python
# ulimit -n 1000000
# shell script to workaround for issue "perf record -p <pid>" not work:
# perf record -g -t $(ls /proc/$(pgrep -n java)/task/|xargs|tr ' ' ',') -- sleep 30

from subprocess import Popen, PIPE
import re
import sys


def run(cmd):
    print("CMD:", cmd)
    pipe = Popen(cmd, shell=False, stdout=PIPE, stderr=PIPE)
    stdout, stderr = pipe.communicate()
    if pipe.returncode:
        raise ValueError(stderr)
    return stdout


def run_pipe(cmds):
    pipe = None
    for cmd in cmds:
        print("CMD:", cmd)
        pipe = Popen(cmd, shell=False, stdin=pipe.stdout if pipe else None, stdout=PIPE)

    stdout, stderr = pipe.communicate()
    if pipe.returncode:
        raise ValueError(stderr)
    return stdout


def show(pid):
    tids = []
    output = run(["jstack", "-l", pid])
    result = re.findall(r'Handling (.*)RequestHandlerThread.* nid=0x(\w+) ', output)
    if result:
        output = [(r[0], int(r[1], 16)) for r in result]
        tids = [int(r[1], 16) for r in result]
        print(output)
    return tids


def perf(tids):
    run(["perf", "record", "-g", "-t", ",".join([str(t) for t in tids]), "--", "sleep", "10"])


def symbol(pid):
    run(["./perf-map-agent/bin/create-java-perf-map.sh", pid])


def flamegraph(output):
    out = run_pipe([["perf", "script"], ["./FlameGraph/stackcollapse-perf.pl"], ["./FlameGraph/flamegraph.pl", "--color=java", "--hash"]])
    with open(output, "wb") as f:
        f.write(out)


if __name__ == "__main__":
    pid = sys.argv[1]
    tids = show(pid)
    if tids:
        perf(tids)
        symbol(pid)
        flamegraph("flame.svg")
