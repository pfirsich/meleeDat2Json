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
        0x04: "fire",
        0x08: "electric",
        0x0C: "slash",
        0x10: "coin",
        0x14: "ice",
        0x18: "sleep",
        0x1C: "sleep",
        0x20: "grounded",
        0x24: "grounded",
        0x28: "cape",
        0x2C: "empty", # gray hitbox that doesn't hit
        0x30: "disabled",
        0x34: "darkness",
        0x38: "screw_attack",
        0x3C: "poison/flower",
        0x40: "nothing", # no graphic on hit
    }
    fields["element"] = elementMap.get(fields["element"], fields["element"])

# mostly from here: https://github.com/Adjective-Object/melee_subaction_unpacker/blob/1489f016240440d76c2a0e6bf94dfc71ea816c5d/melee.langdef
# some info from here too: http://opensa.dantarion.com/wiki/Events_(Melee)
# and a lot from mer in the Melee Workshop Discord
# TODO: https://smashboards.com/threads/new-melee-syntax-school-you-can-write-character-commands-now.402587/
eventTypes = {
    0x00: EventType(0x04, "exit"),

    0x04: EventType(0x04, "wait_for", ("p2u24", ["frames"])),
    0x08: EventType(0x04, "wait_until", ("p2u24", ["frame"])),
    0x0C: EventType(0x04, "set_loop", ("p2u24", ["loop_count"])),
    0x10: EventType(0x04, "execute_loop"),
    0x14: EventType(0x08, "goto", ("p26u32", ["location"])),
    0x18: EventType(0x04, "return"),
    0x1C: EventType(0x08, "subroutine", ("p26u32", ["location"])),
    0x20: EventType(0x04, "set_timer_looping_animation?"),

    0x28: EventType(0x14, "graphic_common", ("p26u16 p16s16s16s16 s16s16s16", [
        "id",
        "z", "y", "x",
        "z_range", "y_range", "x_range",
        ])),

    # https://smashboards.com/threads/melee-hacks-and-you-new-hackers-start-here-in-the-op.247119/page-48#post-10769744
    0x2C: EventType(0x14, "hitbox", ("u3p5u7p2u9 u16s16s16s16 u9u9u9p3u2u9 u5p1u7u8b1b1", [
        "id",
        "bone", # zero is character root position
        "damage",

        "size",
        "z", "y", "x",

        "angle",
        "kb_growth",
        "weight_dep_kb",
        # https://smashboards.com/threads/official-ask-anyone-frame-things-thread.313889/page-16#post-17742200
        "hitbox_interaction",
        "base_kb",

        "element",
        "shield_damage",
        "sfx",
        "hit_grounded",
        "hit_airborne",
        ], postProcessHitboxEvent)),

    0x30: EventType(0x04, "adjust_hitbox_damage", ("u3u23", ["hitbox_id", "damage"])),
    0x34: EventType(0x04, "adjust_hitbox_size", ("u3u23", ["hitbox_id", "size"])),
    0x38: EventType(0x04, "hitbox_set_flags", ("u24u2", ["hitbox_id", "flags"])), # specifics unknown
    0x3C: EventType(0x04, "end_one_collision", ("u26", ["hitbox_id"])),
    0x40: EventType(0x04, "end_all_collisions"),

    0x44: EventType(0x0C, "sfx"),
    0x48: EventType(0x04, "random_smash_sfx"),

    0x4C: EventType(0x04, "autocancel"), # melee_subaction_unpacker says length 0x0B

    0x50: EventType(0x04, "reverse_direction"), # used in throws?
    0x54: EventType(0x04, "set_flag_0x2210_10"),
    0x58: EventType(0x04, "set_flag_0x2210_20"),
    0x5C: EventType(0x04, "allow_iasa"),

    0x60: EventType(0x04, "shootitem1/projectile flag?"),
    0x64: EventType(0x04, "related to ground/air state?"),
    0x68: EventType(0x04, "body_collision_state", ("p24u2", ["state"])), # 0 = normal, 1 = invulnerable, 2 = intangible
    0x6C: EventType(0x04, "body_collision_status"),

    0x70: EventType(0x04, "bone_collision_state", ("u8u18", ["bone", "state"])),
    0x74: EventType(0x04, "enable_jab_followup"),
    0x78: EventType(0x04, "toggle_jab_followup"),
    0x7C: EventType(0x04, "model_state", ("u6p12u8", ["struct_id", "temp_object_id"])),

    0x80: EventType(0x04, "revert_models"),
    0x84: EventType(0x04, "remove_models"),

    # https://smashboards.com/threads/melee-hacks-and-you-new-hackers-start-here-in-the-op.247119/page-49#post-10804377
    0x88: EventType(0x0C, "throw", ("u3p14 u9u9u9u7 p5u9u4 p3p4", [
        "throw_type", # first throw command has a 0 here with all knockback data, second has a 1, which is needed for throw release
        "damage",
        "angle",
        "kb_growth",
        "weight_dep_kb",
        "base_kb",
        "element",
    ])),

    0x8C: EventType(0x04, "held_item_invisibility", ("p25b1", ["flag"])),

    0x90: EventType(0x04, "body_article_invisibility", ("p25b1", ["flag"])),
    0x94: EventType(0x04, "character_invisibility", ("p25b1", ["flag"])),
    0x98: EventType(0x1C, "pseudo_random_sfx"), # melee_subaction_unpacker says length 0x14
    0x9C: EventType(0x10),

    0xA0: EventType(0x04, "animate_texture"),
    0xA4: EventType(0x04, "animate_model"),
    0xA8: EventType(0x04, "parasol related?"), # melee_subaction_unpacker says 0x08 bytes
    0xAC: EventType(0x04, "rumble"),

    0xB0: EventType(0x04, "set_flag_0x221E_20", ("p25b1", ["flag"])),
    0xB4: EventType(0x04), # melee_subaction_unpacker says 0x0C bytes

    #https://smashboards.com/threads/changing-color-effects-in-melee.313177/page-2#post-14490878
    0xB8: EventType(0x04, "bodyaura", ("u8u18", ("aura_id", "duration"))), # melee_subaction_unpacker says length 0x08
    0xBC: EventType(0x04, "remove_color_overlay"),

    0xC4: EventType(0x04, "sword_trail", ("b1p17u8", ["use_beam_sword_trail", "render_status"])),
    0xC8: EventType(0x04, "enable_ragdoll_physics?", ("u26", ["bone"])),
    0xCC: EventType(0x04, "self_damage", ("p10u16", ["damage"])),

    0xD0: EventType(0x04, "continuation_control?"), # "0 = earliest next, 1 = ?, 3 = open continuation window?"
    0xD8: EventType(0x0C, "footstep_sfx_and_gfx"),
    0xDC: EventType(0x0C, "landing_sfx_and_gfx"),

    # https://smashboards.com/threads/changing-color-effects-in-melee.313177/#post-13616960
    0xE0: EventType(0x08, "start_smash_charge", ("p2u8u16u8p24", ["charge_frames", "charge_rate", "visual_effect"])),
    0xE8: EventType(0x10, "wind_effect"),

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
            if len(eventType.fields) > 2:
                fieldFormat, fieldNames, postProcess = eventType.fields
            else:
                fieldFormat, fieldNames = eventType.fields
                postProcess = None
            # p6 to skip command id
            values = bitstruct.unpack("p6" + fieldFormat.replace(" ", ""), eventStr)
            assert len(values) == len(fieldNames), "format: {}, fields: {}, values: {}".format("p6" + fieldFormat, fieldNames, values)
            for i in range(len(fieldNames)):
                self.fields[fieldNames[i]] = values[i]

            if postProcess:
                postProcess(self.fields)

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
