"""Stylized low-poly 3D scenes rendered with Blender (Cycles, CPU).

Usage: python3 scenes3d.py <scene> <out_dir> <seconds> [fps] [samples]
Writes PNG frames (no text); the overlay is added later by engine.py.
"""
import math
import random
import sys

import bpy
from mathutils import Vector

RES = (432, 768)


# ------------------------------------------------------------------ basics
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.use_denoising = True
    s.cycles.max_bounces = 4
    s.cycles.diffuse_bounces = 2
    s.cycles.glossy_bounces = 1
    s.cycles.transparent_max_bounces = 4
    s.render.resolution_x, s.render.resolution_y = RES
    s.render.image_settings.file_format = "PNG"
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = "AgX - Punchy"
    return s


def world(color, strength=1.0, top=None):
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    if top is None:
        bg.inputs[0].default_value = (*color, 1)
    else:  # vertical gradient sky
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        neg = nt.nodes.new("ShaderNodeMath")
        neg.operation = "MULTIPLY"
        neg.inputs[1].default_value = -1.0
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        nt.links.new(geo.outputs["Incoming"], sep.inputs[0])
        nt.links.new(sep.outputs[2], neg.inputs[0])
        nt.links.new(neg.outputs[0], ramp.inputs[0])
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = (*color, 1)
        ramp.color_ramp.elements[1].position = 0.5
        ramp.color_ramp.elements[1].color = (*top, 1)
        nt.links.new(ramp.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = strength


_mats = {}


def mat(name, color, rough=0.6, emit=None, strength=0.0, metal=0.0):
    key = (name, color, emit, strength)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    _mats[key] = m
    return m


def window_mat(name, wall, lit, density=0.55, strength=4.0, scale=(1.4, 1.8)):
    """Building facade: brick texture = window grid with random lit/unlit cells."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    br = nt.nodes.new("ShaderNodeTexBrick")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs[0], add.inputs[0])
    nt.links.new(sep.outputs[1], add.inputs[1])
    nt.links.new(add.outputs[0], comb.inputs[0])
    nt.links.new(sep.outputs[2], comb.inputs[1])
    nt.links.new(comb.outputs[0], br.inputs["Vector"])
    br.offset = 0.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = scale[0]
    br.inputs["Row Height"].default_value = scale[1]
    br.inputs["Mortar Size"].default_value = 0.35
    br.inputs["Bias"].default_value = density * 2 - 1
    br.inputs["Color1"].default_value = (*lit, 1)
    br.inputs["Color2"].default_value = (0.0, 0.0, 0.0, 1)
    br.inputs["Mortar"].default_value = (0, 0, 0, 1)
    nt.links.new(br.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Base Color"].default_value = (*wall, 1)
    b.inputs["Roughness"].default_value = 0.8
    b.inputs["Emission Strength"].default_value = strength
    return m


_meshes = {}


def box_mesh(w, d, h):
    key = ("box", round(w, 2), round(d, 2), round(h, 2))
    if key in _meshes:
        return _meshes[key]
    x, y = w / 2, d / 2
    v = [(-x, -y, 0), (x, -y, 0), (x, y, 0), (-x, y, 0), (-x, -y, h), (x, -y, h), (x, y, h), (-x, y, h)]
    f = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    me = bpy.data.meshes.new("box")
    me.from_pydata(v, [], f)
    _meshes[key] = me
    return me


def prim_mesh(kind, **kw):
    key = (kind, tuple(sorted(kw.items())))
    if key in _meshes:
        return _meshes[key]
    getattr(bpy.ops.mesh, f"primitive_{kind}_add")(**kw)
    o = bpy.context.object
    me = o.data
    bpy.data.objects.remove(o)
    for p in me.polygons:
        p.use_smooth = True
    _meshes[key] = me
    return me


def obj(me, loc, material=None, rot=(0, 0, 0), scale=(1, 1, 1), name="o"):
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.location, o.rotation_euler, o.scale = loc, rot, scale
    if material:
        if not o.data.materials:
            o.data.materials.append(material)
        o.material_slots[0].link = "OBJECT"
        o.material_slots[0].material = material
    return o


def box(loc, w, d, h, material, rot=(0, 0, 0)):
    return obj(box_mesh(w, d, h), loc, material, rot)


def light(kind, loc, energy, color=(1, 1, 1), size=1.0, rot=(0, 0, 0)):
    ld = bpy.data.lights.new("L", kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.size = size
    elif kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = size
    elif kind == "SUN":
        ld.angle = size
    o = bpy.data.objects.new("L", ld)
    bpy.context.scene.collection.objects.link(o)
    o.location, o.rotation_euler = loc, rot
    return o


def flicker(o, base, amount, fps, frames, speed=1.0):
    for f in range(0, frames + 1, 1):
        o.data.energy = base * (1 + amount * (math.sin(f * 1.7 * speed) * 0.6 + math.sin(f * 3.1 * speed + 1) * 0.4))
        o.data.keyframe_insert("energy", frame=f + 1)


def camera(path, fov=50, frames=40):
    """path: list of (frame_fraction, location, look_at)."""
    cd = bpy.data.cameras.new("C")
    cd.lens_unit = "FOV"
    cd.angle = math.radians(fov)
    c = bpy.data.objects.new("C", cd)
    bpy.context.scene.collection.objects.link(c)
    bpy.context.scene.camera = c
    for frac, loc, target in path:
        c.location = loc
        dvec = Vector(target) - Vector(loc)
        c.rotation_euler = dvec.to_track_quat("-Z", "Y").to_euler()
        f = 1 + int(frac * (frames - 1))
        c.keyframe_insert("location", frame=f)
        c.keyframe_insert("rotation_euler", frame=f)
    if c.animation_data and c.animation_data.action:
        for fc in getattr(c.animation_data.action, "fcurves", []):
            for k in fc.keyframe_points:
                k.interpolation = "SINE"
    return c


def hide_at(o, frame):
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=max(1, frame - 1))
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=frame)


SKIN = [(0.85, 0.62, 0.48), (0.62, 0.42, 0.3), (0.4, 0.26, 0.18), (0.95, 0.75, 0.6)]
CLOTH = [(0.6, 0.08, 0.08), (0.08, 0.15, 0.45), (0.85, 0.65, 0.1), (0.1, 0.1, 0.12), (0.15, 0.4, 0.2),
         (0.5, 0.5, 0.55), (0.9, 0.9, 0.88), (0.45, 0.2, 0.5), (0.85, 0.35, 0.1)]


def person(loc, rng, s=1.0, cloth=None, skin=None, face=0.0):
    """Stylized character: capsule body, round head, simple hair cap."""
    cloth = cloth or rng.choice(CLOTH)
    skin = skin or rng.choice(SKIN)
    body = obj(prim_mesh("uv_sphere", segments=12, ring_count=8, radius=1), (loc[0], loc[1], loc[2] + 0.75 * s),
               mat("cloth", cloth), rot=(0, 0, face), scale=(0.28 * s, 0.2 * s, 0.6 * s))
    head = obj(prim_mesh("uv_sphere", segments=12, ring_count=8, radius=1), (loc[0], loc[1], loc[2] + 1.55 * s),
               mat("skin", skin, 0.5), scale=(0.17 * s, 0.17 * s, 0.19 * s))
    hair = obj(prim_mesh("uv_sphere", segments=12, ring_count=8, radius=1), (loc[0], loc[1] + 0.02 * s, loc[2] + 1.62 * s),
               mat("hair", rng.choice([(0.05, 0.03, 0.02), (0.25, 0.12, 0.05), (0.6, 0.45, 0.2)]), 0.7),
               scale=(0.18 * s, 0.18 * s, 0.14 * s))
    return [body, head, hair]


def ground(color, size=400, rough=0.5, z=0.0):
    return box((0, 0, z - 0.1), size, size, 0.1, mat("ground", color, rough))


# ------------------------------------------------------------------ scenes
def city_canyon(rng, F, crowd=900, vanish=0.0, lights_off=0.0, confetti=False, cam="high"):
    world((0.02, 0.01, 0.05), 0.6, top=(0.08, 0.03, 0.15))
    ground((0.05, 0.04, 0.06), rough=0.25)
    pal = [(1.0, 0.7, 0.35), (0.9, 0.85, 1.0), (1.0, 0.55, 0.3)]
    bmats = []
    for i in range(4):
        m = window_mat(f"win{i}", (0.04, 0.04, 0.06), pal[i % 3], density=0.55 + 0.1 * (i % 2), strength=3.0)
        bmats.append(m)
    neon = [(1, 0.1, 0.4), (0.1, 0.6, 1), (1, 0.75, 0.1), (0.6, 0.2, 1)]
    for side in (-1, 1):
        y = -10
        while y < 160:
            w = rng.uniform(10, 18)
            h = rng.uniform(40, 120)
            x = side * (14 + w / 2 + rng.uniform(0, 3))
            m = rng.choice(bmats)
            box((x, y + w / 2, 0), w, w, h, m)
            if rng.random() < 0.7:  # glowing billboard
                c = rng.choice(neon)
                bh = rng.uniform(5, 12)
                box((side * (14 + 0.3), y + w / 2, rng.uniform(6, 25)), 0.4, w * 0.8, bh,
                    mat(f"neon{c}", (0, 0, 0), emit=c, strength=6))
            y += w + rng.uniform(0.5, 3)
    # warm street glow + bounce from billboards
    for y in range(0, 120, 25):
        light("POINT", (0, y, 8), 4000, (1, 0.6, 0.35), 3)
    light("AREA", (0, 40, 60), 30000, (0.6, 0.4, 1.0), 40, rot=(0, 0, 0))
    people = []
    for i in range(crowd):
        x = rng.uniform(-12, 12)
        y = rng.uniform(-6, 70) ** 1.0
        people.append(person((x, y, 0), rng, s=rng.uniform(0.9, 1.1), face=rng.uniform(-0.5, 0.5)))
    if vanish:
        for p in people:
            if rng.random() < vanish:
                f = int(F * rng.uniform(0.25, 0.45))
                for part in p:
                    hide_at(part, f)
    if confetti:
        cm = [mat(f"conf{i}", c, emit=c, strength=2) for i, c in enumerate(neon)]
        me = box_mesh(0.25, 0.02, 0.15)
        for i in range(500):
            o = obj(me, (rng.uniform(-12, 12), rng.uniform(-5, 60), rng.uniform(3, 35)), rng.choice(cm),
                    rot=(rng.random() * 6, rng.random() * 6, rng.random() * 6))
            o.keyframe_insert("location", frame=1)
            o.location.z -= rng.uniform(3, 6)
            o.rotation_euler.x += 6
            o.keyframe_insert("location", frame=F)
            o.keyframe_insert("rotation_euler", frame=F)
    if lights_off:
        for i, m in enumerate(bmats):
            b = m.node_tree.nodes["Principled BSDF"]
            f0 = int(F * (0.15 + 0.15 * i))
            b.inputs["Emission Strength"].keyframe_insert("default_value", frame=f0)
            b.inputs["Emission Strength"].default_value = 3.0 * (1 - lights_off)
            b.inputs["Emission Strength"].keyframe_insert("default_value", frame=f0 + 3)
    if cam == "high":
        camera([(0, (0, -22, 30), (0, 40, 0)), (1, (0, -14, 24), (0, 42, 2))], 55, F)
    else:
        camera([(0, (2, -10, 6), (0, 60, 18)), (1, (-1, 0, 7), (0, 70, 22))], 60, F)


def sky_plane(rng, F):
    world((0.9, 0.55, 0.35), 1.2, top=(0.15, 0.25, 0.55))
    light("SUN", (0, 0, 10), 3.0, (1, 0.8, 0.6), 0.1, rot=(1.2, 0, 0.6))
    cm = mat("cloud", (1, 1, 1), 1.0)
    for i in range(50):
        cx, cy, cz = rng.uniform(-80, 80), rng.uniform(20, 200), rng.uniform(-30, 10)
        for k in range(5):
            r = rng.uniform(3, 8)
            obj(prim_mesh("uv_sphere", segments=16, ring_count=10, radius=1),
                (cx + rng.uniform(-8, 8), cy + rng.uniform(-3, 3), cz + rng.uniform(-1, 2)), cm, scale=(r, r * 0.8, r * 0.5))
    pm = mat("plane", (0.55, 0.57, 0.62), 0.3, metal=0.3)
    tm = mat("tail", (0.7, 0.1, 0.1), 0.4)
    root = bpy.data.objects.new("plane", None)
    bpy.context.scene.collection.objects.link(root)
    parts = [obj(prim_mesh("uv_sphere", segments=16, ring_count=10, radius=1), (0, 0, 0), pm, scale=(0.9, 6, 0.9)),
             box((0, 0.5, -0.2), 12, 1.6, 0.25, pm), box((0, -5, 0), 4, 1, 0.2, pm), box((0, -5.2, 0), 0.25, 1.2, 2.5, tm)]
    for p in parts:
        p.parent = root
    smoke = mat("smoke", (0.18, 0.17, 0.17), 1.0)
    fire = mat("fire", (1, 0.4, 0.1), emit=(1, 0.35, 0.05), strength=30)
    eng = obj(prim_mesh("uv_sphere", segments=12, ring_count=8, radius=1), (3.5, 0.5, -0.4), fire, scale=(0.8, 0.8, 0.8))
    eng.parent = root
    fl = light("POINT", (3.5, 0.5, 0), 3000, (1, 0.4, 0.1), 1)
    fl.parent = root
    for f in range(1, F + 1):
        u = (f - 1) / (F - 1)
        root.location = (-8 + 14 * u, 34 - 6 * u, 12 - 16 * u ** 1.6)
        root.rotation_euler = (-0.25 - 0.6 * u, 0.5 + 1.2 * u, -0.6)
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
        if f % 2 == 0:
            r = 0.4 + 0.5 * rng.random()
            obj(prim_mesh("uv_sphere", segments=10, ring_count=6, radius=1), Vector(root.location) + Vector((3.5, 0, 0)),
                smoke, scale=(r, r, r))
    camera([(0, (0, 0, 2), (-2, 34, 8)), (1, (0, 3, 1.5), (2, 30, 0))], 55, F)


def street_cars(rng, F, fire=True, night=True, debris=True):
    world((0.01, 0.01, 0.03) if night else (0.5, 0.45, 0.4), 0.5 if night else 0.8,
          top=(0.03, 0.03, 0.08) if night else (0.5, 0.6, 0.8))
    ground((0.06, 0.06, 0.07), rough=0.3)
    side = mat("walk", (0.25, 0.22, 0.22), 0.8)
    for s in (-1, 1):
        box((s * 9, 50, 0), 4, 200, 0.2, side)
        y = -5
        while y < 150:
            w = rng.uniform(8, 14)
            m = window_mat(f"sw{y}", (0.15, 0.08, 0.07), (1, 0.6, 0.3), density=0.35 if night else 0.0, strength=2.5)
            box((s * (11 + 5), y + w / 2, 0), 10, w, rng.uniform(15, 35), m)
            y += w
    lamp = mat("lamp", (1, 0.8, 0.5), emit=(1, 0.7, 0.4), strength=20)
    for y in range(0, 120, 18):
        for s in (-1, 1):
            box((s * 7.8, y, 0), 0.2, 0.2, 6, mat("pole", (0.1, 0.1, 0.1)))
            obj(prim_mesh("uv_sphere", segments=10, ring_count=6, radius=0.35), (s * 7.8, y, 6.2), lamp)
            if night:
                light("POINT", (s * 7.6, y, 6), 600, (1, 0.65, 0.35), 0.5)
    cars = [(0.6, 0.05, 0.05), (0.85, 0.85, 0.85), (0.05, 0.1, 0.3), (0.1, 0.1, 0.1), (0.8, 0.6, 0.1)]
    wheel = mat("wheel", (0.02, 0.02, 0.02))
    glass = mat("glass", (0.05, 0.07, 0.1), 0.05)
    tail = mat("tail", (0.3, 0, 0), emit=(1, 0.05, 0.05), strength=8)
    for i in range(16):
        x, y = rng.uniform(-5, 5), rng.uniform(5, 110)
        rz = rng.uniform(-0.7, 0.7)
        cm = mat(f"car{i % 5}", rng.choice(cars), 0.25, metal=0.4)
        b = box((x, y, 0.4), 2, 4.2, 0.9, cm, rot=(0, 0, rz))
        t = box((x, y, 1.3), 1.7, 2.2, 0.6, glass, rot=(0, 0, rz))
        for dx, dy in ((-1, -1.3), (1, -1.3), (-1, 1.3), (1, 1.3)):
            off = Vector((dx, dy, 0))
            off.rotate(b.rotation_euler)
            obj(prim_mesh("cylinder", vertices=12, radius=0.4, depth=0.3), (x + off.x, y + off.y, 0.4), wheel, rot=(0, math.pi / 2, rz))
        off = Vector((0, -2.1, 0.7))
        off.rotate(b.rotation_euler)
        box((x + off.x, y + off.y, 0.7), 1.6, 0.05, 0.2, tail, rot=(0, 0, rz))
    if fire:
        fm = mat("flame", (1, 0.3, 0.05), emit=(1, 0.28, 0.03), strength=6)
        for (x, y) in ((-3, 25), (4, 55)):
            for k in range(6):
                r = rng.uniform(0.3, 0.8)
                obj(prim_mesh("ico_sphere", subdivisions=1, radius=1), (x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), 1 + rng.uniform(0, 1.5)),
                    fm, scale=(r, r, r * 1.8))
            fl = light("POINT", (x, y, 3), 8000, (1, 0.45, 0.15), 2)
            flicker(fl, 8000, 0.3, 8, F, 1.3)
    if debris:
        pm = mat("paper", (0.8, 0.8, 0.75))
        for i in range(60):
            box((rng.uniform(-8, 8), rng.uniform(0, 80), 0.01), rng.uniform(0.3, 0.6), rng.uniform(0.3, 0.6), 0.01, pm, rot=(0, 0, rng.random() * 3))
    if not night:
        light("SUN", (0, 0, 10), 2.5, (1, 0.75, 0.55), 0.05, rot=(1.3, 0, 2.6))
    camera([(0, (1.5, -8, 2.2), (0, 60, 3)), (1, (0.5, 4, 2.0), (0, 70, 3))], 55, F)


def vigil(rng, F, candles=700, people=60, tower=True):
    world((0.01, 0.01, 0.03), 0.6, top=(0.06, 0.05, 0.15))
    ground((0.12, 0.1, 0.1), rough=0.35)
    wax = mat("wax", (0.9, 0.88, 0.8), 0.5)
    flame = mat("flame", (1, 0.6, 0.2), emit=(1, 0.55, 0.15), strength=60)
    for i in range(candles):
        r = 30 * math.sqrt(rng.random())
        a = rng.random() * 6.28
        x, y = r * math.cos(a), 30 + r * math.sin(a) * 1.4
        obj(prim_mesh("cylinder", vertices=8, radius=0.07, depth=0.2), (x, y, 0.1), wax)
        obj(prim_mesh("uv_sphere", segments=8, ring_count=6, radius=0.05), (x, y, 0.25), flame, scale=(1, 1, 1.8))
        if i % 25 == 0:
            fl = light("POINT", (x, y, 0.6), 60, (1, 0.55, 0.2), 0.3)
            flicker(fl, 60, 0.15, 8, F, 2 + rng.random())
    for i in range(people):
        r = rng.uniform(5, 34)
        a = rng.random() * 6.28
        person((r * math.cos(a), 30 + r * math.sin(a) * 1.4, 0), rng, s=1.0,
               cloth=rng.choice([(0.05, 0.05, 0.06), (0.12, 0.1, 0.12), (0.2, 0.08, 0.1)]), face=rng.uniform(-3, 3))
    if tower:  # distant lit monument
        tm = mat("tower", (0.3, 0.25, 0.2), emit=(1, 0.7, 0.4), strength=0.9)
        for k in range(14):
            w = 6 - k * 0.4
            box((0, 110, k * 5), w, w, 5, tm)
        light("AREA", (0, 100, 30), 6000, (1, 0.7, 0.4), 15)
    for s in (-1, 1):
        for y in range(40, 140, 14):
            m = window_mat(f"vw{y}{s}", (0.08, 0.07, 0.1), (1, 0.7, 0.4), 0.3, 2)
            box((s * 45, y, 0), 14, 12, rng.uniform(15, 25), m)
    camera([(0, (0, -12, 7), (0, 40, 0)), (1, (0, -4, 5), (0, 45, 1))], 55, F)


def corridor(rng, F, tint=(0.8, 0.85, 0.9), bars=True, alarm=False):
    world((0, 0, 0), 0)
    wall = mat("wall", tint, 0.6)
    floor = mat("floor", (0.35, 0.36, 0.38), 0.15)
    L = 80
    box((0, L / 2, -0.1), 8, L, 0.1, floor)
    box((0, L / 2, 4), 8, L, 0.1, mat("ceil", (0.5, 0.5, 0.5)))
    for s in (-1, 1):
        box((s * 4, L / 2, 0), 0.1, L, 4, wall)
    box((0, L, 0), 8, 0.1, 4, wall)
    panel = mat("panel", (1, 1, 1), emit=(1, 0.98, 0.92), strength=12)
    stripe = mat("stripe", (0.05, 0.15, 0.5), 0.4)
    for s in (-1, 1):
        box((s * 2.2, L / 2, 0.001), 0.15, L, 0.002, stripe)
    for y in range(4, L, 7):
        box((0, y, 3.9), 2.2, 0.8, 0.05, panel)
    bar = mat("bar", (0.3, 0.32, 0.35), 0.3, metal=0.9)
    for y in range(6, L - 4, 8):
        for s in (-1, 1):
            if bars:
                for k in range(8):
                    box((s * 3.9, y + k * 0.45, 0), 0.08, 0.08, 4, bar)
            else:
                box((s * 3.92, y + 1.5, 0), 0.05, 1.8, 3, mat("door", (0.3, 0.35, 0.4)))
    light("AREA", (0, L / 2, 3.8), 3000, (1, 0.97, 0.9), 6, rot=(0, 0, 0))
    if alarm:
        for y in range(10, L, 15):
            al = light("POINT", (3.5, y, 3.2), 300, (1, 0.05, 0.05), 0.2)
            for f in range(1, F + 1):
                al.data.energy = 600 * max(0, math.sin(f * 0.8))
                al.data.keyframe_insert("energy", frame=f)
    pm = mat("paper", (0.9, 0.9, 0.88))
    for i in range(25):
        box((rng.uniform(-3, 3), rng.uniform(0, L), 0.01), 0.3, 0.4, 0.01, pm, rot=(0, 0, rng.random() * 3))
    camera([(0, (0, -1, 1.7), (0, 40, 1.5)), (1, (0, 6, 1.7), (0, 45, 1.5))], 60, F)


def construction(rng, F):
    world((0.9, 0.5, 0.3), 1.0, top=(0.2, 0.25, 0.5))
    ground((0.35, 0.28, 0.2), rough=0.9)
    light("SUN", (0, 0, 10), 3.0, (1, 0.6, 0.35), 0.05, rot=(1.35, 0, 2.3))
    steel = mat("steel", (0.6, 0.3, 0.1), 0.5, metal=0.6)
    conc = mat("conc", (0.55, 0.53, 0.5), 0.9)
    for bx, by, floors in ((-12, 40, 8), (10, 60, 12), (-5, 85, 5)):
        for fl in range(floors):
            box((bx, by, fl * 3.5), 14, 14, 0.4, conc)
            for cx in (-6.5, 6.5):
                for cy in (-6.5, 6.5):
                    box((bx + cx, by + cy, fl * 3.5), 0.4, 0.4, 3.5, steel)
    yellow = mat("crane", (0.95, 0.7, 0.05), 0.5)
    for k in range(20):
        box((18, 40, k * 3), 1.2, 1.2, 3, yellow)
    box((10, 40, 60), 40, 1.2, 1.2, yellow)
    hook = box((-2, 40, 40), 0.1, 0.1, 20, mat("cable", (0.1, 0.1, 0.1)))
    for i in range(10):
        box((rng.uniform(-20, 20), rng.uniform(10, 30), 0), 3, 0.5, 0.5, steel, rot=(0, 0, rng.random() * 3))
    camera([(0, (-6, -10, 3), (0, 50, 15)), (1, (-2, -4, 4), (2, 55, 18))], 55, F)


def lab(rng, F, close=False, scientist=True):
    world((0, 0.01, 0.012), 0.5)
    ground((0.03, 0.06, 0.07), rough=0.15)
    glow = mat("tube", (0.1, 0.9, 0.75), 0.05, emit=(0.1, 1, 0.8), strength=6)
    cap = mat("cap", (0.3, 0.33, 0.35), 0.3, metal=0.8)
    for y in range(4, 70, 7):
        for s in (-1, 1):
            x = s * 5
            obj(prim_mesh("cylinder", vertices=24, radius=1.0, depth=4), (x, y, 2.4), glow)
            obj(prim_mesh("cylinder", vertices=24, radius=1.15, depth=0.4), (x, y, 0.2), cap)
            obj(prim_mesh("cylinder", vertices=24, radius=1.15, depth=0.4), (x, y, 4.6), cap)
            if y % 14 == 4:
                light("POINT", (s * 3.5, y, 2.5), 400, (0.2, 1, 0.85), 0.5)
    strip = mat("strip", (1, 1, 1), emit=(0.7, 1, 0.95), strength=10)
    for y in range(0, 70, 6):
        box((0, y, 7), 0.4, 4, 0.1, strip)
    box((0, 35, 7.2), 30, 80, 0.1, mat("ceil", (0.05, 0.08, 0.09)))
    screen = mat("screen", (0, 0, 0), emit=(0.3, 1, 0.85), strength=3)
    box((2.2, 12, 2.5), 0.05, 2, 1.2, screen)
    if scientist:
        person((1.2, 10, 0), rng, s=1.0, cloth=(0.92, 0.94, 0.95), face=1.2)
        person((-2, 20, 0), rng, s=1.0, cloth=(0.92, 0.94, 0.95), face=-1.0)
    if close:
        camera([(0, (-1.5, 3, 2.3), (3, 11, 1.8)), (1, (-1.0, 5, 2.1), (3, 11, 1.8))], 50, F)
    else:
        camera([(0, (0, -6, 2.5), (0, 40, 2)), (1, (0, 2, 2.4), (0, 45, 2))], 60, F)


def park_day(rng, F, people=12):
    world((0.95, 0.8, 0.6), 1.0, top=(0.2, 0.4, 0.85))
    ground((0.2, 0.45, 0.15), rough=0.9)
    light("SUN", (0, 0, 10), 4.0, (1, 0.9, 0.75), 0.05, rot=(0.9, 0, 2.6))
    trunk = mat("trunk", (0.25, 0.15, 0.08))
    leaves = [mat(f"leaf{i}", c, 0.8) for i, c in enumerate([(0.15, 0.45, 0.1), (0.3, 0.55, 0.1), (0.1, 0.35, 0.12)])]
    for i in range(40):
        x, y = rng.uniform(-40, 40), rng.uniform(10, 120)
        if abs(x) < 6:
            continue
        box((x, y, 0), 0.5, 0.5, 3, trunk)
        r = rng.uniform(1.8, 3)
        obj(prim_mesh("ico_sphere", subdivisions=2, radius=1), (x, y, 3 + r * 0.8), rng.choice(leaves), scale=(r, r, r))
    path = mat("path", (0.5, 0.42, 0.32), 0.9)
    box((0, 60, 0.001), 5, 140, 0.01, path)
    fl = [mat(f"fl{i}", c, emit=c, strength=0.3) for i, c in enumerate([(1, 0.3, 0.4), (1, 0.85, 0.2), (0.95, 0.95, 1), (0.6, 0.3, 1)])]
    for i in range(600):
        x, y = rng.uniform(-30, 30), rng.uniform(0, 80)
        if abs(x) < 3:
            continue
        obj(prim_mesh("uv_sphere", segments=6, ring_count=4, radius=0.12), (x, y, 0.15), rng.choice(fl))
    for i in range(people):
        p = person((rng.uniform(-2, 2), rng.uniform(8, 60), 0), rng, s=rng.choice([1.0, 1.0, 0.7]), face=rng.uniform(-0.3, 0.3))
    camera([(0, (0, -6, 2.0), (0, 40, 2)), (1, (0, 2, 2.0), (0, 45, 2))], 55, F)


def campfire(rng, F, people=7):
    world((0.005, 0.005, 0.015), 0.4, top=(0.02, 0.02, 0.06))
    ground((0.1, 0.08, 0.06), rough=0.9)
    fm = mat("flame", (1, 0.3, 0.05), emit=(1, 0.3, 0.04), strength=5)
    logm = mat("log", (0.15, 0.08, 0.04))
    for k in range(5):
        box((0, 0, 0.1), 1.6, 0.25, 0.25, logm, rot=(0, 0, k * 0.6))
    for k in range(7):
        r = rng.uniform(0.25, 0.5)
        obj(prim_mesh("ico_sphere", subdivisions=1, radius=1), (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0.4 + rng.uniform(0, 0.6)), fm, scale=(r, r, r * 1.8))
    fl = light("POINT", (0, 0, 1.2), 2500, (1, 0.45, 0.15), 0.6)
    flicker(fl, 2500, 0.25, 8, F, 1.5)
    for i in range(people):
        a = math.pi * (0.2 + 1.6 * i / people) + math.pi * 0.5
        person((3.2 * math.cos(a), 3.2 * math.sin(a), 0), rng, s=1.0,
               cloth=rng.choice([(0.25, 0.1, 0.08), (0.1, 0.12, 0.2), (0.3, 0.25, 0.2)]), face=a + math.pi / 2)
    tm = mat("tree", (0.03, 0.03, 0.03))
    for i in range(30):
        a = rng.random() * 6.28
        r = rng.uniform(10, 25)
        box((r * math.cos(a), r * math.sin(a), 0), 0.3, 0.3, rng.uniform(5, 10), tm, rot=(rng.uniform(-0.1, 0.1), 0, 0))
    sp = mat("spark", (1, 0.7, 0.3), emit=(1, 0.6, 0.2), strength=50)
    for i in range(40):
        o = obj(prim_mesh("uv_sphere", segments=6, ring_count=4, radius=0.03), (rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), 0.8), sp)
        o.keyframe_insert("location", frame=1 + int(rng.random() * F / 2))
        o.location.z += rng.uniform(3, 6)
        o.location.x += rng.uniform(-1, 1)
        o.keyframe_insert("location", frame=F)
    camera([(0, (0, -9, 2.6), (0, 0, 0.9)), (1, (0, -7, 2.2), (0, 0, 1.0))], 50, F)


def snow_girl(rng, F):
    world((0.01, 0.015, 0.04), 0.5, top=(0.03, 0.04, 0.1))
    ground((0.7, 0.75, 0.85), rough=0.8)
    light("SUN", (0, 0, 10), 0.15, (0.6, 0.7, 1.0), 0.1, rot=(1.1, 0, 0.5))
    person((0, 0, 0), rng, s=0.75, cloth=(0.15, 0.35, 0.55), skin=(0.85, 0.62, 0.48), face=0.3)
    lm = mat("lantern", (1, 0.6, 0.3), emit=(1, 0.5, 0.2), strength=6)
    obj(prim_mesh("uv_sphere", segments=10, ring_count=8, radius=0.12), (0.45, -0.3, 0.12), lm)
    l = light("POINT", (0.45, -0.3, 0.3), 120, (1, 0.6, 0.3), 0.1)
    flicker(l, 120, 0.1, 8, F, 2)
    sm = mat("snow", (1, 1, 1), emit=(0.8, 0.85, 1), strength=0.5)
    for i in range(300):
        o = obj(prim_mesh("uv_sphere", segments=6, ring_count=4, radius=0.03), (rng.uniform(-6, 6), rng.uniform(-4, 10), rng.uniform(1, 8)), sm)
        o.keyframe_insert("location", frame=1)
        o.location.z -= rng.uniform(2, 4)
        o.location.x += rng.uniform(-0.5, 0.5)
        o.keyframe_insert("location", frame=F)
    tm = mat("tree", (0.02, 0.03, 0.03))
    for i in range(25):
        x, y = rng.uniform(-30, 30), rng.uniform(10, 40)
        box((x, y, 0), 0.4, 0.4, rng.uniform(4, 9), tm)
    camera([(0, (-1.5, -6, 1.6), (0, 0, 0.6)), (1, (-1, -4.2, 1.2), (0, 0, 0.6))], 45, F)


SCENES = dict(
    city_crowd=lambda r, F: city_canyon(r, F, crowd=900, confetti=True),
    city_vanish=lambda r, F: city_canyon(r, F, crowd=900, vanish=0.5, confetti=True),
    city_dark=lambda r, F: city_canyon(r, F, crowd=0, lights_off=1.0, cam="low"),
    city_low=lambda r, F: city_canyon(r, F, crowd=0, cam="low"),
    sky_plane=sky_plane,
    street_fire=lambda r, F: street_cars(r, F, fire=True),
    street_calm=lambda r, F: street_cars(r, F, fire=False, night=False, debris=False),
    vigil=vigil,
    prison=lambda r, F: corridor(r, F, tint=(0.55, 0.57, 0.6), bars=True),
    hospital=lambda r, F: corridor(r, F, tint=(0.85, 0.88, 0.9), bars=False, alarm=True),
    construction=construction,
    lab=lab,
    lab_close=lambda r, F: lab(r, F, close=True),
    park=park_day,
    campfire=campfire,
    snow_girl=snow_girl,
)


if __name__ == "__main__":
    name, out, secs = sys.argv[1], sys.argv[2], float(sys.argv[3])
    fps = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    samples = int(sys.argv[5]) if len(sys.argv) > 5 else 16
    s = reset()
    s.cycles.samples = samples
    F = max(2, int(secs * fps))
    s.frame_start, s.frame_end = 1, F
    SCENES[name](random.Random(7), F)
    if len(sys.argv) > 6 and sys.argv[6] == "preview":
        s.frame_set(F // 2 + 1)
        s.render.filepath = out
        bpy.ops.render.render(write_still=True)
    else:
        s.render.filepath = f"{out}/f_"
        bpy.ops.render.render(animation=True)
