import argparse
from collections import OrderedDict as odict
import json
import os
import re
import sys
import struct
import time

# Sources:
# https://smashboards.com/threads/melee-dat-format.292603/
# http://opensa.dantarion.com/wiki/Moveset_File_Format_(Melee)
# https://github.com/Adjective-Object/melee_subaction_unpacker

from .events import parseEvents
from .attributes import attributesList

class FileHeader(object):
    def __init__(self, header):
        values = struct.unpack('>8I', header[:0x20])
        self.fileSize = values[0]
        self.dataBlockSize = values[1]
        self.relocationTableCount = values[2]
        self.rootCount = values[3]
        self.rootCount2 = values[4]
        self.unknown1 = values[5]
        self.unknown2 = values[6]
        self.unknown3 = values[7]

class FtDataHeader(object):
    def __init__(self, data):
        values = struct.unpack(">6I", data[:24])
        self.attributesOffset = values[0]
        self.attributesEnd = values[1]
        self.unknown1 = values[2]
        self.subactionsOffset = values[3]
        self.unknown2 = values[4]
        self.subactionsEnd = values[5]

def figatreeShortname(name):
    m = re.match(b".*ACTION_(.*?)_figatree", name)
    if m:
        return m.group(1)
    else:
        return name

class FtDataSubaction(object):
    def __init__(self, data, datFile):
        values = struct.unpack(">4IHHI", data)
        self.nameOffset = values[0]
        self.animationOffset = values[1] # Offset to the animation .dat in PlxxAJ
        self.animationSize = values[2] # Length of that animation .dat
        self.eventsOffset = values[3]
        self.posFlags = values[4] # related to changing position
        self.characterId = values[5]
        # last 4 bytes are always 00000000; game inserts pointer here to animation in ARAM

        self.name = datFile.getDataString(self.nameOffset)
        self.shortName = figatreeShortname(self.name)

        self.events = parseEvents(datFile.data, self.eventsOffset)

        if datFile.animFileData and self.animationSize > 0:
            self.animation = DatFile(datFile.animFileData[self.animationOffset:self.animationOffset+self.animationSize])
        else:
            self.animation = None

class FtData(object):
    def __init__(self, data, datFile):
        self.header = FtDataHeader(data)

        # load attributes
        self.attributeData = datFile.data[self.header.attributesOffset:self.header.attributesEnd]
        fmt = ">"
        for attr in attributesList:
            fmt += attr[0]
        values = struct.unpack(fmt, self.attributeData)

        self.attributes = odict()
        for i, attr in enumerate(attributesList):
            name = attr[1]
            if name != "?":
                self.attributes[name] = values[i]

        # load subactions
        subactionDataSize = self.header.subactionsEnd - self.header.subactionsOffset
        subactionCount = subactionDataSize // 24
        assert subactionCount * 24 == subactionDataSize
        self.subactions = []
        self.subroutines = {}
        for i in range(subactionCount):
            start = self.header.subactionsOffset + i * 24
            subactionHeaderData = datFile.dataSlice(start, 24)
            subaction = FtDataSubaction(subactionHeaderData, datFile)
            self.subactions.append(subaction)

            # we might end up parsing some evnets multiple times here, be we don't care
            for event in subaction.events:
                if event.name == "subroutine" or event.name == "goto":
                    offset = int(event.fields["location"])
                    self.subroutines[offset] = parseEvents(datFile.data, offset)

class FigaTreeHeader(object):
    def __init__(self, data):
        values = struct.unpack(">2If2I", data)
        assert values[0] == 1
        assert values[1] == 0
        self.numFrames = values[2]
        self.boneTableOffset = values[3]
        self.animDataOffset = values[4]

# https://smashboards.com/threads/melee-dat-format.292603/page-6#post-20386112
# https://smashboards.com/threads/melee-animation-model-workshop.433432/
class FigaTree(object):
    def __init__(self, data, datFile):
        self.header = FigaTreeHeader(data)

class RootNode(object):
    def __init__(self, data, datFile):
        values = struct.unpack(">2I", data[:0x08])
        self.rootOffset = values[0]
        self.stringTableOffset = values[1]
        self.name = datFile.getString(self.stringTableOffset)
        self.data = None

        if self.name.startswith(b"ftData"):
            # character data
            self.data = FtData(datFile.dataSlice(self.rootOffset, 0x60), datFile)
        elif self.name.endswith(b"_figatree"):
            # animation file
            self.data = FigaTree(datFile.dataSlice(self.rootOffset, 0x14), datFile)
            self.shortName = figatreeShortname(self.name)
        else:
            print("Warning! Unkown/Unimplemented node type:", self.name)

class DatFile(object):
    def __init__(self, fileData, animFileData=None):
        self.header = FileHeader(fileData[:0x20])
        self.dataBlockOffset = 0x20
        self.relocationTableOffset = self.dataBlockOffset + self.header.dataBlockSize
        self.relocationTableSize = self.header.relocationTableCount * 4 # each entry is a uint32
        self.rootNodesOffset = self.relocationTableOffset + self.relocationTableSize
        self.rootNodesSize = (self.header.rootCount + self.header.rootCount2) * 8 # each entry is 2*uint32
        self.stringTableOffset = self.rootNodesOffset + self.rootNodesSize

        self.fileData = fileData
        self.data = fileData[self.dataBlockOffset:self.dataBlockOffset + self.header.dataBlockSize]
        self.animFileData = animFileData

        # load relocation table
        self.relocationTableData = fileData[self.relocationTableOffset:self.relocationTableOffset + self.relocationTableSize]
        self.relocationTable = list(struct.unpack(">{}I".format(self.header.relocationTableCount), self.relocationTableData))

        # load root nodes
        self.rootNodesData = fileData[self.rootNodesOffset:self.rootNodesOffset + self.rootNodesSize]

        self.rootNodes = []
        for i in range(self.header.rootCount + self.header.rootCount2):
            start = 0x08 * i
            node = RootNode(self.rootNodesData[start:start+0x08], self)
            self.rootNodes.append(node)

    def getString(self, offset):
        return self.fileData[self.stringTableOffset + offset:].split(b'\0', 1)[0]

    def getDataString(self, offset):
        return self.data[offset:].split(b'\0', 1)[0]

    def dataSlice(self, offset, length=None):
        if length == None:
            return self.data[offset:]
        else:
            return self.data[offset:offset+length]

    def toJsonDict(self):
        file_json = odict()
        file_json["nodes"] = []
        for node in self.rootNodes:
            node_json = odict([
                ("name", node.name.decode("utf-8")),
                ("rootOffset", node.rootOffset)
            ])
            if isinstance(node.data, FtData):
                subactions_json = []
                for i, subaction in enumerate(node.data.subactions):
                    subaction_json = odict([
                        ("shortName", subaction.shortName.decode("utf-8")),
                        ("name", subaction.name.decode("utf-8")),
                        ("animOffset", subaction.animationOffset),
                        ("animSize", subaction.animationSize),
                    ])

                    if subaction.animation:
                        if not "animationFiles" in file_json:
                            file_json["animationFiles"] = []
                        subaction_json["animationFile"] = len(file_json["animationFiles"])
                        file_json["animationFiles"].append(subaction.animation.toJsonDict())

                    subaction_json["eventsOffset"] = subaction.eventsOffset
                    subaction_json["events"] = []
                    for event in subaction.events:
                        subaction_json["events"].append(event.toJsonDict())

                    subactions_json.append(subaction_json)

                subroutines_json = odict()
                for offset, subroutine in node.data.subroutines.items():
                    subroutines_json[offset] = []
                    for event in subroutine:
                        subroutines_json[offset].append(event.toJsonDict())

                node_json["data"] = odict([
                    ("attributes", node.data.attributes),
                    ("subactions", subactions_json),
                    ("subroutines", subroutines_json),
                ])
            elif isinstance(node.data, FigaTree):
                node_json["shortName"] = node.shortName.decode("utf-8")
                node_json.move_to_end("shortName", last=False)
                node_json["data"] = odict([
                    ("numFrames", node.data.header.numFrames),
                    ("boneTableOffset", node.data.header.boneTableOffset),
                    ("animDataOffset", node.data.header.animDataOffset),
                ])

            file_json["nodes"].append(node_json)
        return file_json

def main():
    parser = argparse.ArgumentParser(description='Dump Melee .dat files to JSON')
    parser.add_argument('datfile', help='The .dat file')
    parser.add_argument("-a", "--animfile", default=None, help="Path to the corresponding animation file. If nothing is given an Pl**AJ.dat file will be looked for next to the PJ**.dat (the input)")
    parser.add_argument("--dumpanims", default=False, action="store_true", help="Dumps animation files from the Pl**AJ.dat to separate files (per subaction)")
    parser.add_argument("--animpath", default="animationFiles", help="Directory to where the animations from Pl**AJ.dat should be dumped to.")
    parser.add_argument("--out", default=None, help="Path to output JSON file.")
    parser.add_argument("--time", default=False, action="store_true", help="Times how long the dumping took. Mainly for optimization.")
    args = parser.parse_args()

    startTime = time.time()

    with open(args.datfile, "rb") as f:
        fileData = f.read()

    if args.animfile:
        ajFilePath = args.animfile
    else:
        ajFilePath = os.path.splitext(args.datfile)[0] + "AJ.dat"

    if os.path.isfile(ajFilePath):
        with open(ajFilePath, "rb") as f:
            animFileData = f.read()
    else:
        print("Pl**AJ.dat file not found in '{}'".format(ajFilePath))
        print("You can pass --animfile to pass the path to the AJ file directly")
        animFileData = None

    file = DatFile(fileData, animFileData)

    # Dump Anims
    if args.dumpanims:
        assert animFileData
        assert file.rootNodes[0].name.startswith(b"ftData")
        os.makedirs(args.animpath, exist_ok=True)
        for i, subact in enumerate(file.rootNodes[0].data.subactions):
            name = str(i)
            if len(subact.name) > 0:
                name += " - " + subact.shortName.decode("utf-8")
            with open(os.path.join(args.animpath, "{}.dat".format(name)), "wb") as f:
                f.write(animFileData[subact.animationOffset:subact.animationOffset+subact.animationSize])

    # Save to JSON
    if args.out:
        outPath = args.out
    else:
        outPath = os.path.splitext(args.datfile)[0] + ".json"
    print("Saving to {}..".format(outPath))

    with open(outPath, "w") as f:
        json.dump(file.toJsonDict(), f, indent=4)

    print("Duration: {}s".format(time.time() - startTime))

if __name__ == "__main__":
    main()
