"""previz2shot Blender addon: playblast -> CLI -> import result into VSE."""
import bpy, subprocess, sys, os, tempfile

def snap(v, m): return max(m, (v // m) * m)
def snap_frames(n): return ((n - 1) // 8) * 8 + 1  # LTX: 8k+1

class P2S_OT_render(bpy.types.Operator):
    bl_idname = "previz2shot.render"; bl_label = "Previz -> Shot"
    def execute(self, ctx):
        sc = ctx.scene; out = tempfile.mkdtemp(prefix="p2s_")
        sc.render.fps = 24
        sc.frame_end = sc.frame_start + snap_frames(sc.frame_end - sc.frame_start + 1) - 1
        sc.render.resolution_x, sc.render.resolution_y = 960, 544  # multiples of 64
        sc.render.filepath = os.path.join(out, "layout_")
        sc.render.image_settings.file_format = "FFMPEG"; sc.render.ffmpeg.format = "MPEG4"
        bpy.ops.render.opengl(animation=True)  # grey viewport playblast
        props = sc.p2s_prompt
        res = os.path.join(out, "shot.mp4")
        subprocess.run([sys.executable, "-m", "previz2shot", "run", "--layout", out, "--prompt", props, "--out", res], check=True)  # TODO: async/modal + progress
        sc.sequence_editor_create()
        sc.sequence_editor.sequences.new_movie("p2s_shot", res, channel=2, frame_start=sc.frame_start)
        return {"FINISHED"}

class P2S_PT_panel(bpy.types.Panel):
    bl_label = "previz2shot"; bl_space_type = "VIEW_3D"; bl_region_type = "UI"; bl_category = "previz2shot"
    def draw(self, ctx):
        self.layout.prop(ctx.scene, "p2s_prompt"); self.layout.operator("previz2shot.render")

def register():
    bpy.types.Scene.p2s_prompt = bpy.props.StringProperty(name="Style prompt")
    bpy.utils.register_class(P2S_OT_render); bpy.utils.register_class(P2S_PT_panel)
def unregister():
    bpy.utils.unregister_class(P2S_PT_panel); bpy.utils.unregister_class(P2S_OT_render); del bpy.types.Scene.p2s_prompt
