import struct
import bitstruct
from collections import OrderedDict as odict

class EventType(object):
    def __init__(self, length, name=None, fields=None):
        self.length = length
        self.name = name
        self.fields = fields

# mostly from here: https://github.com/Adjective-Object/melee_subaction_unpacker/blob/1489f016240440d76c2a0e6bf94dfc71ea816c5d/melee.langdef
# some info from here too: http://opensa.dantarion.com/wiki/Events_(Melee)
# and a lot from mer in the Melee Workshop Discord
eventTypes = {
    0x00: EventType(0x04, "exit"),

    0x04: EventType(0x04, "wait_until", ("p2u24", ["frames"])),
    0x08: EventType(0x04, "wait_for", ("p2u24", ["frames"])),

    0x0C: EventType(0x04, "set_loop", ("p2u24", ["loop_count"])),
    0x10: EventType(0x04, "execute_loop"),

    0x14: EventType(0x08, "goto", ("p26u32", ["location"])),
    0x18: EventType(0x04, "return"),
    0x1C: EventType(0x08, "subroutine", ("p26u32", ["location"])),

    0x4C: EventType(0x04, "autocancel"),
    0x5C: EventType(0x04, "allow_iasa"),
    0xE0: EventType(0x08, "start_smash_charge"),

    # 0 = normal, 1 = invulnerable, 2 = intangible
    0x68: EventType(0x04, "body_collision_state", ("p24u2", ["state"])),
    0x70: EventType(0x04, "bone_collision_state", ("u8u18", ["bone", "state"])),
    0x74: EventType(0x04, "enable_jab_followup"),
    0x78: EventType(0x04, "toggle_jab_followup"),
    0x7C: EventType(0x04, "model_state", ("u6p12u8", ["struct_id", "temp_object_id"])),
    0x80: EventType(0x04, "revert_models"),
    0x84: EventType(0x04, "remove_models"),
    0x88: EventType(0x10, "throw"),

    0x50: EventType(0x04, "reverse_direction"),
    0x4C: EventType(0x0B, "airstop?"),

    0xAC: EventType(0x04, "gen_article/rumble?"),
    0xCC: EventType(0x04, "self_damage", ("p10u16", ["damage"])),

    0x20: EventType(0x04, "set_timer_looping_animation?"),

    0x2C: EventType(0x14, "hitbox", ("u3p5u7p2u9u16s16s16s16u9u9u9p3u2u9u5p1u7u8u2", [
        "id",
        "bone",
        "damage",
        "size",
        "z", "y", "x",
        "angle",
        "kb_growth",
        "weight_dep_kb",
        "hitbox_interaction",
        "base_kb",
        "element",
        "shield_damage",
        "sfx",
        "hurtbox_interaction",
        ])),

    0x28: EventType(0x14, "graphic_common", ("p26u16p16s16s16s16s16s16s16", [
        "id",
        "z", "y", "x",
        "z_range", "y_range", "x_range",
        ])),

    0x30: EventType(0x04, "adjust_hitbox_damage", ("u3u23", ["hitbox_id", "damage"])),
    0x34: EventType(0x04, "adjust_hitbox_size", ("u3u23", ["hitbox_id", "size"])),
    0x38: EventType(0x04, "hitbox_set_flags", ("u24u2", ["hitbox_id", "flags"])), # specifics unknown

    0x3C: EventType(0x04, "end_one_collision", ("u26", ["hitbox_id"])),
    0x40: EventType(0x04, "end_all_collisions"),

    # "looks like the first bit is some boolean flag that selects bodyaura group 1 vs 2"
    0xB8: EventType(0x08, "bodyaura"),

    0x44: EventType(0x0C, "sfx"),
    0x48: EventType(0x04, "random_smash_sfx"),

    0x60: EventType(0x04, "shootitem1/projectile flag?"),

    0xA0: EventType(0x04, "animate_texture"),

    # Unsure/Unknown
    0xD0: EventType(0x04, "continuation_control?"), # "0 = earliest next, 1 = ?, 3 = open continuation window?"

    0xD8: EventType(0x0C),
    0xDC: EventType(0x0C),
    0xB4: EventType(0x0C),
    0xA8: EventType(0x08), # alternative von mer
    0x38: EventType(0x04, "roll?"),
    0xE8: EventType(0x10),
    0x98: EventType(0x14), # alternative von mer
    0x9C: EventType(0x10),

    "default": EventType(0x04)
}

class Event(object):
    def __init__(self, eventStr):
        self.commandId = eventStr[0] & 0xFC
        eventType = eventTypes.get(self.commandId, eventTypes["default"])
        self.length = eventType.length
        self.name = eventType.name
        self.fields = odict()
        self.bytes = eventStr[:self.length]

        if eventType.fields:
            fieldFormat, fieldNames = eventType.fields
            # p6 to skip command id
            values = bitstruct.unpack("p6" + fieldFormat, eventStr)
            assert len(values) == len(fieldNames), "format: {}, fields: {}, values: {}".format("p6" + fieldFormat, fieldNames, values)
            for i in range(len(fieldNames)):
                self.fields[fieldNames[i]] = values[i]

    def __str__(self):
        if self.name:
            return "Event<name: {}, fields: {}>".format(self.name, self.fields)
        else:
            return "Event<id: {}, length: {}, name: {}, bytes: {}>".format(
                self.commandId, self.length, self.name, self.bytes.hex().upper())

def parseEvents(eventStr):
    i = 0
    events = []
    while i < len(eventStr):
        event = Event(eventStr[i:])
        events.append(event)
        i += event.length
        if event.commandId == 0:
            break
    return events
