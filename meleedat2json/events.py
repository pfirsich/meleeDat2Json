import struct
import bitstruct
from collections import OrderedDict as odict

class EventType(object):
    def __init__(self, length, name=None, fields=None):
        self.length = length
        self.name = name
        self.fields = fields

def postProcessHitboxEvent(fields):
    # size, x, y, z are fixed point floats
    fields["size"] /= 255
    fields["x"] /= 255
    fields["y"] /= 255
    fields["z"] /= 255

    elementMap = {
        0x00: "normal",
        0x01: "fire",
        0x02: "electric",
        0x03: "slash",
        0x04: "coin",
        0x05: "ice",
        0x06: "sleep_103f",
        0x07: "sleep_412f",
        0x08: "grab", # https://gist.github.com/pfirsich/c5b4c467405ba88332cf1e243f4a2e4b
        0x09: "grounded",
        0x0A: "cape",
        0x0B: "empty", # gray hitbox that doesn't hit
        0x0C: "disabled",
        0x0D: "darkness",
        0x0E: "screwAttack",
        0x0F: "poison/flower",
        0x10: "nothing", # no graphic on hit
    }
    fields["element"] = elementMap.get(fields["element"], fields["element"])

# mostly from here: https://github.com/Adjective-Object/melee_subaction_unpacker/blob/1489f016240440d76c2a0e6bf94dfc71ea816c5d/melee.langdef
# some info from here too: http://opensa.dantarion.com/wiki/Events_(Melee)
# and a lot from mer in the Melee Workshop Discord
# TODO: https://smashboards.com/threads/new-melee-syntax-school-you-can-write-character-commands-now.402587/
eventTypes = {
    0x00: EventType(0x04, "exit"),

    0x04: EventType(0x04, "waitFor", ("p2u24", ["frames"])),
    0x08: EventType(0x04, "waitUntil", ("p2u24", ["frame"])),
    0x0C: EventType(0x04, "setLoop", ("p2u24", ["loopCount"])),
    0x10: EventType(0x04, "executeLoop"),
    0x14: EventType(0x08, "goto", ("p26u32", ["location"])),
    0x18: EventType(0x04, "return"),
    0x1C: EventType(0x08, "subroutine", ("p26u32", ["location"])),
    0x20: EventType(0x04, "setTimerLoopingAnimation?"),

    0x28: EventType(0x14, "gfx", ("p26u16 p16s16s16s16 s16s16s16", [
        "id",
        "z", "y", "x",
        "zRange", "yRange", "xRange",
        ])),

    # https://smashboards.com/threads/melee-hacks-and-you-new-hackers-start-here-in-the-op.247119/page-48#post-10769744
    0x2C: EventType(0x14, "hitbox", ("u3p5u7p2u9 u16s16s16s16 u9u9u9p3u2u9 u5p1u7u8b1b1", [
        "id",
        # unknown (5 bits)
        "bone", # zero is character root position
        # unknown (2 bits)
        "damage",

        "size",
        "z", "y", "x",

        "angle",
        "kbGrowth",
        "weightDepKb",
        # unknown (3 bits)
        # https://smashboards.com/threads/official-ask-anyone-frame-things-thread.313889/page-16#post-17742200
        "hitboxInteraction",
        "baseKb",

        "element",
        # unknown (1 bit)
        "shieldDamage",
        "sfx",
        "hitGrounded",
        "hitAirborne",
        ], postProcessHitboxEvent)),

    0x30: EventType(0x04, "adjustHitboxDamage", ("u3u23", ["hitboxId", "damage"])),
    0x34: EventType(0x04, "adjustHitboxSize", ("u3u23", ["hitboxId", "size"])),
    0x38: EventType(0x04, "hitboxSetFlags", ("u24u2", ["hitboxId", "flags"])), # specifics unknown
    0x3C: EventType(0x04, "endOneCollision", ("u26", ["hitboxId"])),
    0x40: EventType(0x04, "endAllCollisions"),

    0x44: EventType(0x0C, "sfx"),
    0x48: EventType(0x04, "randomSmashSfx"),

    0x4C: EventType(0x04, "autocancel"), # melee_subaction_unpacker says length 0x0B

    0x50: EventType(0x04, "reverseDirection"), # used in throws?
    0x54: EventType(0x04, "setFlag_0x2210_10"),
    0x58: EventType(0x04, "setFlag_0x2210_20"),
    0x5C: EventType(0x04, "allowIasa"),

    0x60: EventType(0x04, "shootitem"),
    0x64: EventType(0x04, "related to ground/air state?"),
    0x68: EventType(0x04, "bodyCollisionState", ("p24u2", ["state"])), # 0 = normal, 1 = invulnerable, 2 = intangible
    0x6C: EventType(0x04, "bodyCollisionStatus"),

    0x70: EventType(0x04, "boneCollisionState", ("u8u18", ["bone", "state"])),
    0x74: EventType(0x04, "enableJabFollowup"),
    0x78: EventType(0x04, "toggleJabFollowup"),
    0x7C: EventType(0x04, "modelState", ("u6p12u8", ["structId", "tempObjectId"])),

    0x80: EventType(0x04, "revertModels"),
    0x84: EventType(0x04, "removeModels"),

    # https://smashboards.com/threads/melee-hacks-and-you-new-hackers-start-here-in-the-op.247119/page-49#post-10804377
    0x88: EventType(0x0C, "throw", ("u3p14 u9u9u9u7 p5u9u4 p3p4", [
        "throwType", # first throw command has a 0 here with all knockback data, second has a 1, which is needed for throw release
        "damage",
        "angle",
        "kbGrowth",
        "weightDepKb",
        "baseKb",
        "element",
    ])),

    0x8C: EventType(0x04, "heldItemInvisibility", ("p25b1", ["flag"])),

    0x90: EventType(0x04, "bodyArticleInvisibility", ("p25b1", ["flag"])),
    0x94: EventType(0x04, "characterInvisibility", ("p25b1", ["flag"])),
    0x98: EventType(0x1C, "pseudoRandomSfx"), # melee_subaction_unpacker says length 0x14
    0x9C: EventType(0x10),

    0xA0: EventType(0x04, "animateTexture"),
    0xA4: EventType(0x04, "animateModel"),
    0xA8: EventType(0x04, "parasol related?"), # melee_subaction_unpacker says 0x08 bytes
    0xAC: EventType(0x04, "rumble"),

    0xB0: EventType(0x04, "setFlag_0x221E_20", ("p25b1", ["flag"])),
    0xB4: EventType(0x04), # melee_subaction_unpacker says 0x0C bytes

    #https://smashboards.com/threads/changing-color-effects-in-melee.313177/page-2#post-14490878
    0xB8: EventType(0x04, "bodyaura", ("u8u18", ("auraId", "duration"))), # melee_subaction_unpacker says length 0x08
    0xBC: EventType(0x04, "removeColorOverlay"),

    0xC4: EventType(0x04, "swordTrail", ("b1p17u8", ["useBeamSwordTrail", "renderStatus"])),
    0xC8: EventType(0x04, "enableRagdollPhysics?", ("u26", ["bone"])),
    0xCC: EventType(0x04, "selfDamage", ("p10u16", ["damage"])),

    0xD0: EventType(0x04, "continuationControl?"), # "0 = earliest next, 1 = ?, 3 = open continuation window?"
    0xD8: EventType(0x0C, "footstepSfxAndGfx"),
    0xDC: EventType(0x0C, "landingSfxAndGfx"),

    # https://smashboards.com/threads/changing-color-effects-in-melee.313177/#post-13616960
    0xE0: EventType(0x08, "startSmashCharge", ("p2u8u16u8p24", ["chargeFrames", "chargeRate", "visualEffect"])),
    0xE8: EventType(0x10, "windEffect"),

    "default": EventType(0x04)
}

class Event(object):
    def __init__(self, eventStr, offset):
        self.commandId = eventStr[offset] & 0xFC
        eventType = eventTypes.get(self.commandId, eventTypes["default"])
        self.length = eventType.length
        self.name = eventType.name
        self.fields = odict()
        self.bytes = eventStr[offset:offset+self.length]

        if eventType.fields:
            if len(eventType.fields) > 2:
                fieldFormat, fieldNames, postProcess = eventType.fields
            else:
                fieldFormat, fieldNames = eventType.fields
                postProcess = None
            # p6 to skip command id
            values = bitstruct.unpack("p6" + fieldFormat.replace(" ", ""), self.bytes)
            assert len(values) == len(fieldNames), "format: {}, fields: {}, values: {}".format("p6" + fieldFormat, fieldNames, values)
            for i in range(len(fieldNames)):
                self.fields[fieldNames[i]] = values[i]

            if postProcess:
                postProcess(self.fields)

    def toJsonDict(self):
        event_json = odict()
        event_json["commandId"] = hex(self.commandId)
        if self.name:
            event_json["name"] = self.name
        event_json["length"] = self.length
        event_json["bytes"] = " ".join("{:02x}".format(byte) for byte in self.bytes)
        if len(self.fields) > 0:
            event_json["fields"] = self.fields
        return event_json

def parseEvents(eventStr, offset):
    events = []
    while offset < len(eventStr):
        event = Event(eventStr, offset)
        events.append(event)
        offset += event.length
        if event.commandId == 0:
            break
    return events
