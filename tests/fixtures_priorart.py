"""Synthetic fixtures for the prior-art (Source ``.smd`` / ``.ascii``) parsers.

Mirrors the layouts observed in the Bloodborne Vergil package (E-014) without
shipping any third-party asset.
"""


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
