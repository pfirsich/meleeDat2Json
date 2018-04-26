import sys
import struct
import json
from collections import OrderedDict as odict

# Sources:
# https://smashboards.com/threads/melee-dat-format.292603/
# http://opensa.dantarion.com/wiki/Moveset_File_Format_(Melee)
# https://github.com/Adjective-Object/melee_subaction_unpacker

from .events import parseEvents

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

    def __str__(self):
        return "FileHeader<fileSize: {}, dataBlockSize: {}, relocationTableCount: {}, rootCount: {}, rootCount2: {}, unknown1: {}, unknown2: {}, unknown3: {}>".format(
            self.fileSize, self.dataBlockSize, self.relocationTableCount, self.rootCount, self.rootCount2, self.unknown1, self.unknown2, self.unknown3)

class FtDataHeader(object):
    def __init__(self, data):
        values = struct.unpack(">6I", data[:24])
        self.attributesOffset = values[0]
        self.attributesEnd = values[1]
        self.unknown1 = values[2]
        self.subactionsOffset = values[3]
        self.unknown2 = values[4]
        self.subactionsEnd = values[5]

    def __str__(self):
        return "FtDataHeader<attributesOffset: {}, attributesEnd: {}, subactionsOffset: {}, subactionsEnd: {}, unknown1: {}, unknown2: {}>".format(
            self.attributesOffset, self.attributesEnd, self.subactionsOffset, self.subactionsEnd, self.unknown1, self.unknown2)

class FtDataAttributes(object):
    def __init__(self, data):
        pass
        # TODO: put this into variables later:
        # https://github.com/Adjective-Object/melee_subaction_unpacker/blob/master/src/dolfs/ftdata.hpp#L55
        # http://opensa.dantarion.com/wiki/Attributes_(Melee)
        # maybe look up if by now more is known about the unknown values

    def __str__(self):
        return "FtDataAttributes<>"

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
        self.eventsData = datFile.dataSlice(self.eventsOffset)

        self.events = parseEvents(self.eventsData)

    def __str__(self):
        return "Subaction<nameOffset: {}, eventsOffset: {}, name: {}>".format(
            self.nameOffset, self.eventsOffset, self.name)

class FtData(object):
    def __init__(self, data, datFile):
        self.header = FtDataHeader(data)
        self.attributeData = datFile.data[self.header.attributesOffset:self.header.attributesEnd]
        self.attributes = FtDataAttributes(self.attributeData)
        self.subactionData = datFile.data[self.header.subactionsOffset:self.header.subactionsEnd]

        subactionCount = len(self.subactionData) // 24
        assert subactionCount * 24 == len(self.subactionData)
        self.subactions = []
        for i in range(subactionCount):
            start = i * 24
            subactionHeaderData = self.subactionData[start:start+24]
            subaction = FtDataSubaction(subactionHeaderData, datFile)
            self.subactions.append(subaction)

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
        else:
            print("Warning! Unkown/Unimplemented node type:", self.name)

    def __str__(self):
        return "RootNode<rootOffset: {}, stringTableOffset: {}, name: {}>".format(self.rootOffset, self.stringTableOffset, self.name)

class DatFile(object):
    def __init__(self, fileData):
        self.header = FileHeader(fileData[:0x20])
        self.dataBlockOffset = 0x20
        self.relocationTableOffset = self.dataBlockOffset + self.header.dataBlockSize
        self.relocationTableSize = self.header.relocationTableCount * 4 # each entry is a uint32
        self.rootNodesOffset = self.relocationTableOffset + self.relocationTableSize
        self.rootNodesSize = (self.header.rootCount + self.header.rootCount2) * 8 # each entry is 2*uint32
        self.stringTableOffset = self.rootNodesOffset + self.rootNodesSize
        self.stringTableData = fileData[self.stringTableOffset:]

        self.data = fileData[self.dataBlockOffset:self.dataBlockOffset + self.header.dataBlockSize]

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
        return self.stringTableData[offset:].split(b'\0', 1)[0]

    def getDataString(self, offset):
        return self.data[offset:].split(b'\0', 1)[0]

    def dataSlice(self, offset, length=None):
        if length == None:
            return self.data[offset:]
        else:
            return self.data[offset:offset+length]

def main():
    with open(sys.argv[1], "rb") as f:
        fileData = f.read()

    file = DatFile(fileData)

    # Save to JSON
    file_json = {"nodes": []}
    for node in file.rootNodes:
        node_json = {
            "rootOffset": node.rootOffset,
            "name": node.name.decode("utf-8")
        }
        if isinstance(node.data, FtData):
            # TODO: save attributes
            attributes_json = []

            subactions_json = []
            for i, subaction in enumerate(node.data.subactions):
                print(i, subaction.name)
                subaction_json = {
                    "name": subaction.name.decode("utf-8"),
                    "animOffset": subaction.animationOffset,
                    "animSize": subaction.animationSize,
                    "events": []
                }

                for event in subaction.events:
                    event_json = odict()
                    event_json["commandId"] = hex(event.commandId)
                    if event.name:
                        event_json["name"] = event.name
                    event_json["length"] = event.length
                    event_json["bytes"] = " ".join("{:02x}".format(byte) for byte in event.bytes)
                    if len(event.fields) > 0:
                        event_json["fields"] = event.fields

                    subaction_json["events"].append(event_json)

                subactions_json.append(subaction_json)
            node_json["data"] = {
                "attributes": attributes_json,
                "subactions": subactions_json
            }
        elif isinstance(node.data, FigaTree):
            node_json["data"] = {
                "numFrames": node.data.header.numFrames,
                "boneTableOffset": node.data.header.boneTableOffset,
                "animDataOffset": node.data.header.animDataOffset,
            }

        file_json["nodes"].append(node_json)

    with open(sys.argv[2], "w") as f:
        json.dump(file_json, f, indent=4)

if __name__ == "__main__":
    main()
