"""Synthetic fixtures for the prior-art (Source ``.smd`` / ``.ascii``) parsers
and the FLVER header reader.

Mirrors the layouts observed in the Bloodborne Vergil package (E-014) without
shipping any third-party asset.
"""

import struct


def flver_header() -> bytes:
    """The 128-byte FLVER header of ``BD_M_10100.flver`` from the prior-art
    package (E-039).

    Every field is a verbatim observation of the real file at offset 0x00; no
    field meaning is assumed. Bytes 0x5C..0x7F are zero.
    """
    blob = bytearray(0x80)
    blob[0x00:0x06] = b"FLVER\x00"
    struct.pack_into("<H", blob, 0x06, 0x004C)   # u16 76
    struct.pack_into("<H", blob, 0x08, 0x0014)   # u16 20
    struct.pack_into("<H", blob, 0x0A, 0x0002)   # u16 2
    struct.pack_into("<I", blob, 0x0C, 0x0000F030)  # u32 61488
    struct.pack_into("<I", blob, 0x10, 0x00063010)  # u32 405520
    struct.pack_into("<I", blob, 0x14, 0)
    struct.pack_into("<I", blob, 0x18, 6)
    struct.pack_into("<I", blob, 0x1C, 0x0000014E)  # u32 334
    struct.pack_into("<I", blob, 0x20, 6)
    struct.pack_into("<I", blob, 0x24, 0x0000000C)  # u32 12
    struct.pack_into("<f", blob, 0x28, -0.7157)     # f32 (bbox)
    struct.pack_into("<f", blob, 0x2C, 0.0)
    struct.pack_into("<f", blob, 0x30, -0.1980)
    struct.pack_into("<f", blob, 0x34, 0.7180)
    struct.pack_into("<f", blob, 0x38, 1.7909)
    struct.pack_into("<f", blob, 0x3C, 0.2405)
    struct.pack_into("<I", blob, 0x40, 0x00006D9E)  # u32 28062
    struct.pack_into("<I", blob, 0x44, 0x00006D9E)
    struct.pack_into("<I", blob, 0x48, 0x00000100)  # u32 256
    struct.pack_into("<I", blob, 0x4C, 0)
    struct.pack_into("<I", blob, 0x50, 0x00000024)  # u32 36
    struct.pack_into("<I", blob, 0x54, 0x0000000A)  # u32 10
    struct.pack_into("<I", blob, 0x58, 0x0000002A)  # u32 42
    return bytes(blob)


def flver_sections() -> bytes:
    """FLVER header plus section table mirroring real observations.

    Builds the 128-byte header of ``BD_M_10100.flver`` followed by the six
    32-byte section entries observed at file offset 0x80 (E-039/E-040). Every
    value is a verbatim observation of the real file; no field meaning is
    assumed. The layout is what the parser under test consumes.
    """
    blob = bytearray(flver_header())
    blob.extend(b"\x00" * (6 * 0x20))  # room for the six section entries
    # u32_18 == 6 => six section entries; each entry is two 16-byte records.
    sections = [
        (49600, 49616, 7, 0, 366, 48160, 0, 0),
        (49966, 49976, 7, 7, 360, 48400, 1, 0),
        (50326, 50338, 7, 14, 362, 48640, 2, 0),
        (50688, 50700, 7, 21, 370, 48880, 3, 0),
        (51058, 51082, 7, 28, 374, 49120, 4, 0),
        (51432, 51442, 7, 35, 334, 49360, 5, 0),
    ]
    for index, fields in enumerate(sections):
        off = 0x80 + index * 0x20
        struct.pack_into("<8I", blob, off, *fields)
    return bytes(blob)


def smd_text(materials=None) -> str:
    """A small but structurally faithful ``version 1`` SMD.

    ``materials`` maps a material name to a list of ``(bone, weight)`` links
    used for every vertex in that group; one triangle is emitted per group.
    """
    if materials is None:
        materials = {"m0_Test": [(1, 1.0)]}
    nodes = [
        (0, "Root", -1),
        (1, "Joint_A", 0),
        (2, "Joint_B", 0),
    ]
    bones = [
        (0, (0.0, 0.0, 0.0)),
        (1, (0.0, -1.0, 0.0)),
        (2, (0.0, -2.0, 0.0)),
    ]
    lines = ["version 1", "nodes"]
    for index, name, parent in nodes:
        lines.append(f'{index} "{name}" {parent}')
    lines.append("end")
    lines.append("skeleton")
    lines.append("time 0")
    for index, pos in bones:
        lines.append(f"{index} {pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f} 0.000000 0.000000 0.000000")
    lines.append("end")
    lines.append("triangles")
    for material, links in materials.items():
        lines.append(material)
        corners = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        for cx, cy, cz in corners:
            link_text = " ".join(f"{bone} {weight:.6f}" for bone, weight in links)
            lines.append(
                f"0  {cx:.6f} {cy:.6f} {cz:.6f}  0.000000 0.000000 1.000000  "
                f"{cx:.6f} {cy:.6f} {len(links)} {link_text}"
            )
    lines.append("end")
    return "\n".join(lines) + "\n"


def ascii_text(vertex_count: int = 3, face_count: int = 1) -> str:
    """A small but structurally faithful Source reference ``.ascii`` mesh."""
    lines = ["2"]  # bones
    lines += ["Root", "-1", "0 0 0 0 0 0 1"]
    lines += ["Blade_00", "0", "0 -0.5 0 0 0 0.05 0.999"]

    lines.append("1")  # meshes
    lines.append("m0_Test")
    lines.append("2")  # unknown
    lines.append("2")  # textures
    lines += ["N:\\data\\tex\\Test_a.tif", "0"]
    lines += ["N:\\data\\tex\\Test_n.tif", "0"]

    lines.append(str(vertex_count))
    for index in range(vertex_count):
        lines.append(f"{index}.0 0.0 0.0")          # position
        lines.append("0.0 0.0 1.0")                  # normal
        lines.append("255 255 255 255")              # color
        lines.append(f"{index}.0 0.0")               # uv
        lines.append(f"{index}.0 0.0")               # uv2
        lines.append("1 0 0 0")                      # bone indices
        lines.append("1.0 0.0 0.0 0.0")              # bone weights

    lines.append(str(face_count))
    for index in range(face_count):
        base = index % max(1, vertex_count - 2)
        lines.append(f"{base} {base + 1} {base + 2}")

    return "\n".join(lines) + "\n"
