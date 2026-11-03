bl_info = {
    "name": "anim2spritesheet",
    "author": "Connor Wright",
    "version": (1, 2, 0),
    "blender": (4, 0, 0),
    "location": "3D Viewport > Sidebar > Render",
    "description": "Automated rendering of 3D animations as pixel art spritesheets with albedo, normal, and emissive maps.",
    "category": "Render",
}

import bpy
import os
import json
import math
import shutil
import struct
import tempfile
import uuid
import zlib
from contextlib import contextmanager

preview_collection = None


def read_png(path):
    """Read the non-interlaced RGBA8 PNGs produced by this exporter, losslessly."""
    with open(path, 'rb') as source:
        data = source.read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError("Not a PNG: " + path)
    offset, compressed, dimensions = 8, bytearray(), None
    while offset < len(data):
        size = struct.unpack('>I', data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + size]
        checksum = data[offset + 8 + size:offset + 12 + size]
        if len(checksum) != 4 or struct.unpack('>I', checksum)[0] != zlib.crc32(kind + payload):
            raise ValueError("Corrupt PNG: " + path)
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            if (depth, color, compression, filtering, interlace) != (8, 6, 0, 0, 0):
                raise ValueError("Expected non-interlaced RGBA8 PNG: " + path)
            dimensions = width, height
        elif kind == b'IDAT':
            compressed.extend(payload)
        elif kind == b'IEND':
            break
        offset += size + 12
    if dimensions is None:
        raise ValueError("Missing PNG header")
    width, height = dimensions
    stride = width * 4
    raw = zlib.decompress(compressed)
    if len(raw) != height * (stride + 1):
        raise ValueError("Incorrect PNG data length")
    pixels, previous = bytearray(), bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        mode, row = raw[start], bytearray(raw[start + 1:start + stride + 1])
        if mode > 4:
            raise ValueError("Unsupported PNG filter")
        for x in range(stride):
            left = row[x - 4] if x >= 4 else 0
            up = previous[x]
            corner = previous[x - 4] if x >= 4 else 0
            if mode == 0:
                predictor = 0
            elif mode == 1:
                predictor = left
            elif mode == 2:
                predictor = up
            elif mode == 3:
                predictor = (left + up) // 2
            else:
                estimate = left + up - corner
                distances = [abs(estimate - v) for v in (left, up, corner)]
                predictor = (left, up, corner)[distances.index(min(distances))]
            row[x] = (row[x] + predictor) & 255
        pixels.extend(row)
        previous = row
    return width, height, pixels


def write_png(path, width, height, pixels):
    if len(pixels) != width * height * 4:
        raise ValueError("Incorrect RGBA buffer size")
    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload))
    stride = width * 4
    raw = b''.join(b'\0' + pixels[y * stride:(y + 1) * stride] for y in range(height))
    with open(path, 'wb') as target:
        target.write(b'\x89PNG\r\n\x1a\n')
        target.write(chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)))
        target.write(chunk(b'IDAT', zlib.compress(raw)))
        target.write(chunk(b'IEND', b''))


from bpy.types import (Panel,
                       Operator,
                       AddonPreferences,
                       PropertyGroup,
                       )
from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       EnumProperty,
                       PointerProperty,
                       )




class RENDER_PT_model2pixel(bpy.types.Panel):  
    bl_space_type = "VIEW_3D"  
    bl_region_type = "UI"  

    bl_category = "Render"  
    bl_label = "anim2spritesheet"  

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool

        row = layout.row()
        row.label(text="Render Settings")
    
        row = layout.row()
        row.prop(mytool, "render_base", text="Base")
        row.prop(mytool, "render_normal", text="Normal")
        row.prop(mytool, "render_emission", text="Emission")
        
        row = layout.row()
        row.prop(scene, "resolution_x")
        row.prop(scene, "resolution_y")
        
        row = layout.row()
        row.prop(scene, "keyframe_start")
        row.prop(scene, "keyframe_end")
        row.prop(scene, "keyframe_step")

        row = layout.row()
        row.label(text="Output")
        
        row = layout.row()
        row.prop(scene.render, "filepath", text="")
        
        row = layout.row()
        row.operator("render.all", text="Render")

        ## Preview
        layout.separator()
        box = layout.box()
        box.label(text="Pixel Preview")
        box.operator("render.pixel_preview", text="Refresh Preview", icon='FILE_REFRESH')
        
        global preview_collection
        preview = preview_collection.get("pixel_snapshot")
        if preview:
            # Displays the pixelated thumbnail onto the N-panel
            box.template_icon(icon_value=preview.icon_id, scale=10)

    
    
def eevee_engine():
    return 'BLENDER_EEVEE_NEXT' if (4, 2, 0) <= bpy.app.version < (5, 0, 0) else 'BLENDER_EEVEE'


@contextmanager
def preserved_render_state(context):
    scene = context.scene
    groups = [
        (scene, ('frame_start', 'frame_end', 'frame_step')),
        (scene.render, ('engine', 'filepath', 'resolution_x', 'resolution_y',
                        'resolution_percentage', 'filter_size', 'film_transparent',
                        'use_file_extension', 'use_overwrite', 'use_border',
                        'use_crop_to_border', 'pixel_aspect_x', 'pixel_aspect_y',
                        'use_compositing', 'use_sequencer', 'use_multiview')),
        (scene.render.image_settings,
         (('media_type',) if hasattr(scene.render.image_settings, 'media_type') else ()) +
         ('file_format', 'color_mode', 'color_depth', 'compression')),
        (scene.display.shading, ('light', 'studio_light')),
        (scene.display, ('render_aa',)),
    ]
    space = context.space_data
    if space and space.type == 'VIEW_3D':
        groups.extend([(space.shading, ('type', 'render_pass')),
                       (space.overlay, ('show_overlays',))])
    if context.region_data:
        groups.append((context.region_data, ('view_perspective',)))
    saved = [(obj, attr, getattr(obj, attr)) for obj, attrs in groups for attr in attrs]
    frame, subframe = scene.frame_current, scene.frame_subframe
    try:
        yield
    finally:
        # Restore the engine before its dependent settings.
        for obj, attr, value in saved:
            setattr(obj, attr, value)
        scene.frame_set(frame, subframe=subframe)


def configure_render(scene, map_name):
    render = scene.render
    render.engine = 'BLENDER_WORKBENCH' if map_name == 'Normal' else eevee_engine()
    render.resolution_x, render.resolution_y = scene.resolution_x, scene.resolution_y
    render.resolution_percentage = 100
    render.pixel_aspect_x = render.pixel_aspect_y = 1
    render.use_border = render.use_crop_to_border = False
    render.use_compositing = render.use_sequencer = render.use_multiview = False
    render.use_file_extension = render.use_overwrite = True
    render.filter_size = 0.01
    render.film_transparent = True
    if hasattr(render.image_settings, 'media_type'):
        render.image_settings.media_type = 'IMAGE'
    render.image_settings.file_format = 'PNG'
    render.image_settings.color_mode = 'RGBA'
    render.image_settings.color_depth = '8'
    render.image_settings.compression = 15
    if map_name == 'Normal':
        scene.display.shading.light = 'MATCAP'
        scene.display.shading.studio_light = 'check_normal+y.exr'
        scene.display.render_aa = 'OFF'


def pack_spritesheet(paths, destination):
    if not paths:
        raise ValueError('No frames were rendered')
    width, height, _ = read_png(paths[0])
    columns = math.ceil(math.sqrt(len(paths)))
    rows = math.ceil(len(paths) / columns)
    sheet_width = columns * width
    buffer_size = sheet_width * rows * height * 4
    if buffer_size > 256 * 1024 * 1024:
        raise ValueError('Atlas exceeds the 256 MiB pixel buffer limit; reduce frames or resolution')
    pixels = bytearray(buffer_size)
    for index, path in enumerate(paths):
        frame_width, frame_height, source = read_png(path)
        if (frame_width, frame_height) != (width, height):
            raise ValueError('Rendered frames have inconsistent dimensions')
        for y in range(height):
            target = (((index // columns) * height + y) * sheet_width + (index % columns) * width) * 4
            pixels[target:target + width * 4] = source[y * width * 4:(y + 1) * width * 4]
    write_png(destination, sheet_width, rows * height, pixels)
    return {'columns': columns, 'rows': rows, 'frame_size': [width, height]}


def validate_export(context, maps):
    scene = context.scene
    if not scene.camera:
        raise ValueError('Set an active scene camera before rendering')
    if not maps:
        raise ValueError('Select at least one output map')
    if scene.keyframe_end < scene.keyframe_start:
        raise ValueError('End frame must be at least the start frame')
    if not scene.render.filepath.strip():
        raise ValueError('Choose an output directory')
    if 'Emission' in maps and (not context.space_data or context.space_data.type != 'VIEW_3D' or not context.region_data):
        raise ValueError('Emission currently requires a 3D viewport camera view')


def render_frame(context, map_name, path):
    scene = context.scene
    scene.render.filepath = path
    if map_name == 'Emission':
        context.region_data.view_perspective = 'CAMERA'
        context.space_data.shading.type = 'RENDERED'
        context.space_data.shading.render_pass = 'EMISSION'
        context.space_data.overlay.show_overlays = False
        result = bpy.ops.render.opengl(write_still=True, view_context=True)
    else:
        result = bpy.ops.render.render(write_still=True)
    if 'FINISHED' not in result:
        raise RuntimeError('Render canceled; previous exports are unchanged')
    if not os.path.isfile(path):
        raise RuntimeError('Renderer did not produce the expected PNG')


def export_maps(operator, context, maps):
    stage = None
    try:
        validate_export(context, maps)
        output = bpy.path.abspath(context.scene.render.filepath)
        os.makedirs(output, exist_ok=True)
        stage = tempfile.mkdtemp(prefix='.model2pixel-', dir=output)
        scene = context.scene
        samples = list(range(scene.keyframe_start, scene.keyframe_end + 1, scene.keyframe_step))
        manifest = {'schema_version': 1, 'samples': samples, 'maps': {}}
        with preserved_render_state(context):
            for map_name in maps:
                configure_render(scene, map_name)
                folder = os.path.join(stage, map_name)
                os.mkdir(folder)
                paths = []
                for index, frame in enumerate(samples):
                    scene.frame_set(frame)
                    path = os.path.join(folder, f'{index:06d}.png')
                    render_frame(context, map_name, path)
                    paths.append(path)
                sheet = map_name + '_Spritesheet.png'
                metadata = pack_spritesheet(paths, os.path.join(stage, sheet))
                metadata.update({'sheet': sheet, 'frames': [os.path.relpath(path, stage) for path in paths]})
                manifest['maps'][map_name] = metadata
        with open(os.path.join(stage, 'manifest.json'), 'w') as target:
            json.dump(manifest, target, indent=2)
        published = os.path.join(output, 'export-' + uuid.uuid4().hex)
        os.rename(stage, published)
        stage = None
        operator.report({'INFO'}, 'Export saved to ' + published)
        return {'FINISHED'}
    except Exception as error:
        operator.report({'ERROR'}, str(error))
        return {'CANCELLED'}
    finally:
        if stage:
            shutil.rmtree(stage)


class RENDER_OT_render_all(bpy.types.Operator):
    bl_idname = 'render.all'
    bl_label = 'Render All'
    bl_description = 'Render selected maps into a new export folder'

    def execute(self, context):
        settings = context.scene.my_tool
        maps = [name for name, enabled in [('Base', settings.render_base),
                ('Normal', settings.render_normal), ('Emission', settings.render_emission)] if enabled]
        return export_maps(self, context, maps)


class RENDER_OT_render_base(bpy.types.Operator):
    bl_idname = 'render.base'
    bl_label = 'Render Base'

    def execute(self, context):
        return export_maps(self, context, ['Base'])


class RENDER_OT_render_normal(bpy.types.Operator):
    bl_idname = 'render.normal'
    bl_label = 'Render Normal'

    def execute(self, context):
        return export_maps(self, context, ['Normal'])


class RENDER_OT_pixel_preview(bpy.types.Operator):
    bl_idname = 'render.pixel_preview'
    bl_label = 'Generate Pixel Preview'
    bl_description = 'Render the current frame at the export dimensions'

    def execute(self, context):
        try:
            validate_export(context, ['Base'])
            with tempfile.TemporaryDirectory(prefix='model2pixel-preview-') as folder:
                path = os.path.join(folder, 'preview.png')
                with preserved_render_state(context):
                    configure_render(context.scene, 'Base')
                    render_frame(context, 'Base', path)
                global preview_collection
                preview_collection.clear()
                preview_collection.load('pixel_snapshot', path, 'IMAGE')
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
            return {'FINISHED'}
        except Exception as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}


class SelectDirExample(bpy.types.Operator):
    """Create render for all characters"""
    bl_idname = "render.select_dir"
    bl_label = "Select Output Folder"
    bl_options = {'REGISTER'}

    # Define this to tell 'fileselect_add' that we want a directoy
    directory: bpy.props.StringProperty(
        name="Outdir Path",
        description="Where I will save my stuff"
        )

    # Filters folders
    filter_folder: bpy.props.BoolProperty(
        default=True,
        options={"HIDDEN"}
        )

    def execute(self, context):
        scene = bpy.context.scene
        scene.render.filepath = self.directory
        print("Selected dir: '" + self.directory + "'")
        return {'FINISHED'}

    def invoke(self, context, event):
        # Open browser, take reference to 'self' read the path to selected
        # file, put path in predetermined self fields.
        # See: https://docs.blender.org/api/current/bpy.types.WindowManager.html#bpy.types.WindowManager.fileselect_add
        context.window_manager.fileselect_add(self)
        # Tells Blender to hang on for the slow user input
        return {'RUNNING_MODAL'}


class Render_Settings(PropertyGroup):
    '''
    bl_idname = "render.settings"
    bl_label = "Render Settings"
    bl_options = {'REGISTER'}
    '''
        
    render_base : BoolProperty(
        name="Enable or Disable",
        description="Render base / albedo color spritesheet",
        default = True
        )
        
    render_normal : BoolProperty(
        name="Enable or Disable",
        description="Render normal map spritesheet",
        default = True
        )
        
    render_emission : BoolProperty(
        name="Enable or Disable",
        description="Render emission map spritesheet",
        default = True
        )



classes = (RENDER_OT_render_base, RENDER_OT_render_normal, RENDER_OT_render_all, RENDER_OT_pixel_preview, RENDER_PT_model2pixel, SelectDirExample, Render_Settings)



def register():
    global preview_collection
    import bpy.utils.previews
    preview_collection = bpy.utils.previews.new()

    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.resolution_x = bpy.props.IntProperty(
        name="Res X",
        description="X resolution of output images",
        default=64,
        min=1
    )
    bpy.types.Scene.resolution_y = bpy.props.IntProperty(
        name="Res Y",
        description="Y resolution of output images",
        default=64,
        min=1
    )
    bpy.types.Scene.my_tool = PointerProperty(type=Render_Settings)
    
    bpy.types.Scene.keyframe_start = bpy.props.IntProperty(
        name="Start",
        description="Initial keyframe to begin render at",
        default=1,
        min=1
    )
    bpy.types.Scene.keyframe_end = bpy.props.IntProperty(
        name="End",
        description="Ending keyframe to stop render at",
        default=100,
        min=1
    )
    bpy.types.Scene.keyframe_step = bpy.props.IntProperty(
        name="Step",
        description="Number of frames to skip per step (1 = default)",
        default=1,
        min=1
    )




def unregister():
    global preview_collection
    bpy.utils.previews.remove(preview_collection)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.resolution_x
    del bpy.types.Scene.resolution_y
    del bpy.types.Scene.keyframe_start
    del bpy.types.Scene.keyframe_end
    del bpy.types.Scene.keyframe_step
    del bpy.types.Scene.my_tool

        
        
if __name__ == "__main__":
    register()