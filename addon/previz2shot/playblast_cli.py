"""previz2shot playblast: grey Workbench layout clips for LTX Layout-To-Render.

Standalone:
  blender -b scene.blend -P playblast_cli.py -- --camera CAM_wide --out out.mp4 --frames 121 --res 960x544
  blender -b scene.blend -P playblast_cli.py -- --all-cameras --out-dir playblast/ --frames 121 --res 960x544
Writes <name>.mp4 (H.264, 24 fps) and <name>_f0.png (first frame) per camera.
Default: per-class greys via object color (road 0.30, grass 0.55, sky 0.85, barriers 0.75, car 0.60, trees 0.45, booth 0.65); --flat for one grey.
Wheel spin added at runtime if separate wheel objects exist. The .blend on disk is never saved.
Rules: width/height multiple of 32 (960x544 = half of 1920x1088, which is a multiple of 64), frames = 8k+1 (121 -> frame_end = start+120).
"""
import bpy, sys, os, glob, shutil, argparse

DEFAULT_CAMS = ["CAM_wide", "CAM_car_close", "CAM_bar", "CAM_hero"]
GREY = (0.6, 0.6, 0.6)

def parse(argv):
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser("playblast_cli")
    p.add_argument("--camera", action="append", help="camera name (repeatable)")
    p.add_argument("--all-cameras", action="store_true", help=f"use {DEFAULT_CAMS} (those that exist)")
    p.add_argument("--out", help="output mp4 (single camera)")
    p.add_argument("--out-dir", help="output folder (multi camera); files <camera>.mp4")
    p.add_argument("--frames", type=int, default=121)
    p.add_argument("--res", default="960x544")
    p.add_argument("--start", type=int, default=None, help="default: scene frame_start")
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--flat", action="store_true", help="old mode: one grey for everything")
    p.add_argument("--no-wheel-spin", action="store_true")
    a = p.parse_args(argv)
    w, h = (int(x) for x in a.res.lower().split("x"))
    # LTX: final res multiple of 64 (1920x1088); stage-1 res = half of it -> multiple of 32 (960x544)
    if w % 32 or h % 32: raise SystemExit(f"--res {a.res}: width/height must be multiples of 32 (64 for full-res)")
    if (a.frames - 1) % 8: raise SystemExit(f"--frames {a.frames}: must be 8k+1 (e.g. 49, 97, 121)")
    a.w, a.h = w, h
    return a

# per-class greys (layout readability for LTX): collection name first, then object/material name
CLASS_GREY = [  # (keywords, grey)
    (("barrier",), 0.75),  # before "road": barrier meshes are named concrete_road_barrier
    (("tyre", "tire"), 0.35),
    (("road", "centerline", "asphalt"), 0.30),
    (("curb",), 0.70),
    (("grass", "ground", "terrain"), 0.55),
    (("barrier",), 0.75),
    (("tyre", "tire"), 0.35),
    (("car", "race", "kart", "wheel"), 0.60),
    (("tree", "shrub", "bush"), 0.45),
    (("bar", "booth", "counter", "wall", "roof", "sign", "floor", "pillar", "shelf", "table", "stool", "crate", "lamp", "bottle"), 0.65),
    (("character", "bartender", "driver", "mechanic"), 0.62),
]
COLL_GREY = {"track": None, "car": 0.60, "trees": 0.45, "bar": 0.65, "characters": 0.62, "props": None}
SKY_GREY = 0.85

def _grey_for(o):
    names = [o.name.lower()] + [m.name.lower() for m in getattr(o.data, "materials", []) if m]
    p = o.parent
    while p is not None:
        names.append(p.name.lower()); p = p.parent
    for kws, g in CLASS_GREY:
        if any(k in n for n in names for k in kws): return g
    for c in o.users_collection:
        g = COLL_GREY.get(c.name.lower())
        if g is not None: return g
    return 0.6

def apply_class_greys(sc):
    counts = {}
    for o in sc.objects:
        if o.type not in {"MESH", "CURVE", "FONT", "SURFACE", "META"}: continue
        g = _grey_for(o); o.color = (g, g, g, 1.0)
        counts[g] = counts.get(g, 0) + 1
    print("[p2s] class greys:", {k: counts[k] for k in sorted(counts)})

def _wheel_mesh(w):
    if w.type == "MESH": return w
    for c in w.children_recursive:
        if c.type == "MESH": return c
    return None

def add_wheel_markers(sc, wheels, grey=0.12):
    """Dark off-centre marker + one spoke on each wheel face so spin reads in grey Workbench.
    Built in the wheel mesh's local space and parented to it (runtime only)."""
    from mathutils import Vector
    n = 0
    for w in wheels:
        m = _wheel_mesh(w)
        if m is None: continue
        bb = [Vector(c) for c in m.bound_box]
        lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        c = (lo + hi) / 2; size = hi - lo
        ax = min(range(3), key=lambda i: size[i])          # axle = thinnest local axis
        u, v = [i for i in range(3) if i != ax]
        R = min(size[u], size[v]) / 2
        verts, faces = [], []
        def box(center, half):
            b = len(verts)
            for dx in (-1, 1):
                for dy in (-1, 1):
                    for dz in (-1, 1):
                        verts.append(tuple(center[i] + (dx, dy, dz)[i] * half[i] for i in range(3)))
            faces.extend([(b+0,b+1,b+3,b+2),(b+4,b+6,b+7,b+5),(b+0,b+4,b+5,b+1),(b+2,b+3,b+7,b+6),(b+0,b+2,b+6,b+4),(b+1,b+5,b+7,b+3)])
        for side in (-1, 1):                                # both faces of the wheel
            face = c.copy(); face[ax] = (hi[ax] if side > 0 else lo[ax]) + side * size[ax] * 0.04
            # spoke: from centre to rim along u
            ctr = face.copy(); ctr[u] += R * 0.45
            half = Vector((0, 0, 0)); half[u] = R * 0.45; half[v] = R * 0.09; half[ax] = size[ax] * 0.04
            box(ctr, half)
            # blob near rim on the spoke side (breaks 180 deg symmetry)
            blob = face.copy(); blob[u] += R * 0.72; blob[v] += R * 0.15
            hb = Vector((0, 0, 0)); hb[u] = R * 0.16; hb[v] = R * 0.22; hb[ax] = size[ax] * 0.05
            box(blob, hb)
        me = bpy.data.meshes.new(f"p2s_marker_{w.name}"); me.from_pydata(verts, [], faces); me.update()
        o = bpy.data.objects.new(f"p2s_marker_{w.name}", me)
        for col in m.users_collection: col.objects.link(o)
        o.parent = m; o.matrix_parent_inverse.identity()
        o.color = (grey, grey, grey, 1.0); n += 1
    print(f"[p2s] wheel markers: {n}")
    return n

def add_wheel_spin(sc, start, end):
    """Spin wheel objects by distance travelled (runtime only, .blend on disk untouched)."""
    wheels = [o for o in sc.objects if "wheel" in o.name.lower() and o.type in {"MESH", "EMPTY"}]
    # keep only top-most wheel objects (not their child meshes)
    wheels = [w for w in wheels if not (w.parent and "wheel" in w.parent.name.lower())]
    if not wheels:
        print("[p2s] wheel spin: skipped (no separate wheel objects; car is a single mesh)"); return 0
    import mathutils
    add_wheel_markers(sc, wheels)
    for w in wheels:
        m = _wheel_mesh(w)
        if m is None: continue
        rel = w.matrix_world.inverted() @ m.matrix_world          # mesh corners in the wheel's local frame
        pts = [rel @ mathutils.Vector(c) for c in m.bound_box]
        dims = mathutils.Vector([max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3)])
        axis = min(range(3), key=lambda i: dims[i])               # thinnest local dim = axle
        ws = w.matrix_world.to_scale()
        r = max(0.05, max(dims[i] * abs(ws[i]) for i in range(3) if i != axis) * 0.5)
        base = w.matrix_basis.to_quaternion(); w.rotation_mode = "QUATERNION"
        local_axis = mathutils.Vector([1.0 if i == axis else 0.0 for i in range(3)])
        dist = 0.0; prev = None
        for f in range(start, end + 1):
            sc.frame_set(f); pos = w.matrix_world.translation.copy()
            if prev is not None: dist += (pos - prev).length
            prev = pos
            w.rotation_quaternion = base @ mathutils.Quaternion(local_axis, dist / r)  # spin about the wheel's own axle
            w.keyframe_insert("rotation_quaternion", frame=f)
        print(f"[p2s] wheel spin: {w.name} axis={'XYZ'[axis]} r={r:.2f} dist={dist:.1f}")
    sc.frame_set(start)
    return len(wheels)

def setup_grey(sc, a):
    sc.render.engine = "BLENDER_WORKBENCH"
    s = sc.display.shading
    s.light = "STUDIO"
    if a.flat: s.color_type = "SINGLE"; s.single_color = GREY
    else: s.color_type = "OBJECT"; apply_class_greys(sc)
    for attr, val in (("show_shadows", False), ("show_cavity", False), ("show_object_outline", False),
                      ("show_specular_highlight", False), ("show_xray", False), ("use_dof", False)):
        if hasattr(s, attr): setattr(s, attr, val)
    if hasattr(s, "background_type"): s.background_type = "WORLD"
    if sc.world is None: sc.world = bpy.data.worlds.new("p2s_world")
    sc.world.color = (0.25,) * 3 if a.flat else (SKY_GREY,) * 3
    sc.display.render_aa = "8"
    r = sc.render
    r.film_transparent = False
    r.use_stamp = False
    for k in [k for k in dir(r) if k.startswith("use_stamp")]:
        try: setattr(r, k, False)
        except Exception: pass
    r.resolution_x, r.resolution_y, r.resolution_percentage = a.w, a.h, 100
    r.pixel_aspect_x = r.pixel_aspect_y = 1
    r.fps, r.fps_base = a.fps, 1.0
    r.use_motion_blur = False
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    sc.view_settings.exposure = 0; sc.view_settings.gamma = 1
    r.use_compositing = False; r.use_sequencer = False
    # hide non-geometry clutter (empties/lights/cameras never render in Workbench; text objects are geometry and stay)
    start = a.start if a.start is not None else sc.frame_start
    sc.frame_start, sc.frame_end = start, start + a.frames - 1
    if not a.no_wheel_spin: add_wheel_spin(sc, sc.frame_start, sc.frame_end)
    return start

def render_cam(sc, cam_name, mp4, png, start):
    cam = bpy.data.objects.get(cam_name)
    if cam is None or cam.type != "CAMERA":
        print(f"[p2s] skip: no camera {cam_name}"); return False
    sc.camera = cam
    os.makedirs(os.path.dirname(os.path.abspath(mp4)), exist_ok=True)
    r = sc.render
    # first frame PNG
    if hasattr(r.image_settings, "media_type"): r.image_settings.media_type = "IMAGE"  # Blender 5.x
    r.image_settings.file_format = "PNG"; r.image_settings.color_mode = "RGB"
    sc.frame_set(start); r.filepath = png
    bpy.ops.render.render(write_still=True)
    # H.264 mp4
    if hasattr(r.image_settings, "media_type"): r.image_settings.media_type = "VIDEO"  # Blender 5.x
    r.image_settings.file_format = "FFMPEG"
    r.ffmpeg.format = "MPEG4"; r.ffmpeg.codec = "H264"
    r.ffmpeg.constant_rate_factor = "HIGH"; r.ffmpeg.ffmpeg_preset = "GOOD"
    r.ffmpeg.gopsize = 12; r.ffmpeg.audio_codec = "NONE"
    tmp = os.path.splitext(os.path.abspath(mp4))[0] + "_tmp_"
    r.filepath = tmp; r.use_file_extension = True
    bpy.ops.render.render(animation=True)
    made = sorted(glob.glob(glob.escape(tmp) + "*"))
    if not made: raise RuntimeError(f"no movie written for {cam_name}")
    if os.path.exists(mp4): os.remove(mp4)
    shutil.move(made[-1], mp4)
    print(f"[p2s] {cam_name}: {mp4} + {png}")
    return True

def main():
    a = parse(sys.argv)
    sc = bpy.context.scene
    start = setup_grey(sc, a)
    cams = list(a.camera or [])
    if a.all_cameras: cams += [c for c in DEFAULT_CAMS if c not in cams]
    if not cams: cams = [sc.camera.name] if sc.camera else []
    if not cams: raise SystemExit("no camera")
    if len(cams) == 1 and a.out:
        jobs = [(cams[0], a.out)]
    else:
        d = a.out_dir or (os.path.dirname(a.out) if a.out else "//playblast")
        d = bpy.path.abspath(d)
        jobs = [(c, os.path.join(d, f"{c}.mp4")) for c in cams]
    ok = 0
    for c, mp4 in jobs:
        ok += render_cam(sc, c, mp4, os.path.splitext(mp4)[0] + "_f0.png", start)
    print(f"[p2s] done {ok}/{len(jobs)} cameras, frames {sc.frame_start}-{sc.frame_end}, {a.w}x{a.h}@{a.fps}")

if __name__ == "__main__":
    main()
