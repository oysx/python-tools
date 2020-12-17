#!/bin/env python

import os
import subprocess
import json
import re
import getopt
import sys
import pprint
import tarfile
import errno
import shutil


class Docker(object):
    def __init__(self, name):
        self.name = name
        self.layers = []

    def command(self, cmd):
        out = subprocess.check_output(
            "docker {} {}".format(cmd, self.name),
            shell=True
        )
        return out

    def layer_list(self):
        info = self.command("inspect")
        info = json.loads(info)
        driver = info[0]["GraphDriver"]
        gd = getattr(self, 'layer_list_{}'.format(driver['Name']))
        out = gd(driver['Data'])
        return out

    def layer_list_overlay2(self, data):
        layers = data['LowerDir'].split(':')
        layers = [data['UpperDir']] + layers
        self.layers = layers
        return layers

    def layer_find(self, name):
        self.layer_list()
        name = name.strip('/')
        for layer in self.layers:
            print("-".center(20, "-"))
            path = os.path.join(layer, name)
            whiteout = name.strip('/').split('/')
            parent = os.path.join(*whiteout[:-1])
            if os.path.exists(path):
                print("*****{}".format(layer))
                if os.path.isdir(path):
                    print(os.listdir(path))
                else:
                    print(path)
            elif os.path.isdir(parent):
                entries = os.listdir(parent)
                out = [entry for entry in entries if re.search(r'\.wh\..*{}'.format(whiteout[-1]), entry)]
                if out:
                    print(out)

    def layer_strip(self, id):
        pass

class DockerTar(object):
    def __init__(self, directory):
        self.directory = directory

    def sync_cmd_with_layer(self):
        history = [(h["created_by"], index) for h, index in zip(self.history, range(len(self.history)))]
        self.cmds = filter(lambda entity: any([entity[0].startswith(cmd) for cmd in ["RUN", "COPY", "ADD", "/bin/sh -c #(nop) ADD"]]), history)

    def parse(self):
        with open(os.path.join(self.directory, "manifest.json")) as f:
            self.manifest = json.load(f)
            self.manifest = self.manifest[0]

        config_file = self.manifest['Config']
        self.layers = self.manifest["Layers"]
        with open(os.path.join(self.directory, config_file)) as f:
            self.config = json.load(f)
            self.history = self.config["history"]

        self.sync_cmd_with_layer()
        print("Total %d layers" % len(self.layers))
        pprint.pprint(list(enumerate(self.layers)))
        print("Total %d commands" % len(self.cmds))
        pprint.pprint(list(enumerate(self.cmds)))

    def is_last_layer(self, num):
        return num == len(self.layers) - 1

    def layer_get_json(self, layer):
        layer = os.path.join(self.directory, layer, "json")
        with open(layer) as f:
            layer = json.load(f)
        return layer

    def layer_set_json(self, layer, content):
        layer = os.path.join(self.directory, layer, "json")
        with open(layer, 'w') as f:
            json.dump(content, f)

    def change_last_layer(self):
        print("Change last layer")
        lastlayer = self.layer_get_json(self.layer(-1))
        parentlayer = self.layer_get_json(lastlayer["parent"])

        layerdiff = {k: lastlayer[k] for k in set(lastlayer) - set(parentlayer)}
        parentlayer.update(layerdiff)
        self.layer_set_json(lastlayer["parent"], parentlayer)

        self.config["created"] = parentlayer["created"]

    def layer(self, num):
        return os.path.dirname(self.manifest["Layers"][num])

    def change_layer(self, num):
        print("Change layer")
        curlayer = self.layer_get_json(self.layer(num))
        lowlayer = self.layer_get_json(self.layer(num+1)) if num+1 < len(self.layers) else None
        if lowlayer:
            lowlayer["parent"] = curlayer.get("parent", None)
            if not lowlayer["parent"]:
                del lowlayer["parent"]

            with open(os.path.join(self.directory, self.layer(num+1), "json"), 'w') as f:
                json.dump(lowlayer, f)

    def extract(self, num):
        if self.is_last_layer(num):
            self.change_last_layer()

        self.change_layer(num)

        rmdir = os.path.dirname(self.layers[num])
        shutil.rmtree(os.path.join(self.directory, rmdir))
        del self.layers[num]
        del self.config["rootfs"]["diff_ids"][num]
        del self.config["history"][self.cmds[num][1]]

        with open(os.path.join(self.directory, "manifest.json"), 'w') as f:
            json.dump([self.manifest], f)

        with open(os.path.join(self.directory, self.manifest["Config"]), 'w') as f:
            json.dump(self.config, f)

g_params = None
def docker_tar(docker):
    tmpdir = "/tmp/vidocker/"
    try:
        os.makedirs(tmpdir)
    except OSError as e:
        if errno.EEXIST != e.errno:
            raise

    tardir = os.path.join(tmpdir, docker.name)
    tarname = os.path.join(tardir + ".tar")

    if not os.path.exists(tarname):
        print("Starting to save docker image to %s" % tarname)
        output = subprocess.check_output("docker save -o {} {}".format(tarname, docker.name), shell=True)
        print(output)
        print("created tar file %s" % tarname)

    if not os.path.exists(tardir):
        print("Starting to extract tar file")
        with tarfile.open(tarname) as f:
            f.extractall(tardir)

    mytar = DockerTar(tardir)
    mytar.parse()
    return mytar

def docker_extract(docker):
    mytar = docker_tar(docker)
    mytar.extract(int(g_params))


def docker_list(docker):
    out = docker.layer_list()
    pprint.pprint(out)

def docker_search(docker):
    docker.layer_find(g_params)

def docker_walk(docker):
    global g_params
    out = docker.layer_list()
    for layer in out:
        print("-".center(20, "-"))
        try:
            cmd = g_params.format(layer)
            # print("command: {}".format(cmd))
            output = subprocess.check_output(cmd, shell=True)
            print(output)
        except:
            pass

def docker_diff(docker):
    global g_params
    base = docker.layer_list()
    base.reverse()
    docker_a = Docker(g_params)
    another = docker_a.layer_list()
    another.reverse()

    print("{}\t -- {}".format(docker.name, docker_a.name))
    common = [b for b, a in zip(base, another) if b == a]
    for c in common:
        print("***{}".format(c))

    b = base[len(common):]
    a = another[len(common):]
    for i in range(max(len(a), len(b))):
        try:
            show = b[i]
        except:
            show = "<null>"

        try:
            show += " -- " + a[i]
        except:
            show += " -- " + "<null>"

        print(show)

'''
Example:
# fo findout all "trusted.overlay.opaque" xattribute directories which is another whiteout mechanism for directories in overlay2 filesystem
./test.py -w 'getfattr --absolute-names -R -m "" -d {} 2>/dev/null | grep -B3 trusted.overlay.opaque 2>/dev/null' <containerID or imageID> 2>/dev/null
# to findout all character device with 0:0 deviceID which is the whiteout mechanism for overlay2 filesystem
./test.py -w 'find {} -type c'
'''
if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Usage: %s <dockerID>" % sys.argv[0])
        sys.exit()

    try:
        options, args = getopt.getopt(sys.argv[1:], "x:tw:ld:s:", ["extract", "tar", "walk", "list", "diff", "search"])
    except getopt.GetoptError:
        sys.exit()

    for k, v in options:
        if k in ("-l", "--list"):
            opcode = docker_list
        if k in ("-w", "--walk"):
            opcode = docker_walk
            g_params = v
        if k in ("-d", "--diff"):
            opcode = docker_diff
            g_params = v
        if k in ("-s", "--search"):
            opcode = docker_search
            g_params = v
        if k in ("-t", "--tar"):
            opcode = docker_tar
        if k in ("-x", "--extract"):
            opcode = docker_extract
            g_params = v


    docker = Docker(args[0])
    opcode(docker)
