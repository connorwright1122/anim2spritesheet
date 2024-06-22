bl_info = {
    "name": "model2pixel",
    "author": "Connor Wright",
    "version": (1, 0, 1),
    "blender": (2, 80, 0),
    "location": "3D Viewport > Sidebar > Render category",
    "description": "Automated rendering of 3D animations as pixel art spritesheets with albedo and normal maps.",
    "category": "Development",
}

import bpy
import os
import sys
import subprocess
import platform

def isWindows():
    return os.name == 'nt'

def isMacOS():
    return os.name == 'posix' and platform.system() == "Darwin"

def isLinux():
    return os.name == 'posix' and platform.system() == "Linux"

def python_exec():
    
    if isWindows():
        return os.path.join(sys.prefix, 'bin', 'python.exe')
    elif isMacOS():
    
        try:
            # 2.92 and older
            path = bpy.app.binary_path_python
        except AttributeError:
            # 2.93 and later
            import sys
            path = sys.executable
        return os.path.abspath(path)
    elif isLinux():
        import sys
        return os.path.join(sys.prefix, 'bin', 'python3.11')
    else:
        print("sorry, still not implemented for ", os.name, " - ", platform.system)


def installModule(packageName):

    try:
        subprocess.call([python_exe, "import ", packageName])
    except:
        python_exe = python_exec()
       # upgrade pip
        subprocess.call([python_exe, "-m", "ensurepip"])
        subprocess.call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
       # install required packages
        subprocess.call([python_exe, "-m", "pip", "install", packageName])
        
installModule("pillow")
from PIL import Image

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
    bl_label = "model2pixel"  

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool

        row = layout.row()
        row.label(text="Render Settings")
    
        row = layout.row()
        row.prop(mytool, "render_base", text="Base")
        row.prop(mytool, "render_normal", text="Normal")
        
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

    
    
def swap_render_engine(new_engine):
    bpy.context.scene.render.engine = new_engine
    
    
def settings_base_render():
    swap_render_engine("BLENDER_EEVEE")
    scene = bpy.context.scene
    scene.render.resolution_x = scene.resolution_x
    scene.render.resolution_y = scene.resolution_y
    scene.frame_start = scene.keyframe_start
    scene.frame_end = scene.keyframe_end
    scene.frame_step = scene.keyframe_step
    scene.render.filter_size = 0
    scene.render.film_transparent = True
    scene.render.image_settings.compression = 0
    
    
def settings_normal_render():
    swap_render_engine("BLENDER_WORKBENCH")
    scene = bpy.context.scene
    scene.render.resolution_x = scene.resolution_x
    scene.render.resolution_y = scene.resolution_y
    scene.frame_start = scene.keyframe_start
    scene.frame_end = scene.keyframe_end
    scene.frame_step = scene.keyframe_step
    scene.render.filter_size = 0.01
    scene.render.film_transparent = True
    scene.render.image_settings.compression = 0
    scene.display.shading.studio_light = "check_normal+y.exr"
    scene.display.render_aa = "OFF"


def create_output_directory(subfolder_name):
    scene = bpy.context.scene
    parent_path = scene.render.filepath
    subfolder_path = os.path.join(parent_path, subfolder_name)
    os.makedirs(subfolder_path, exist_ok=True)
    scene.render.filepath = os.path.join(subfolder_path, "")


def pack_spritesheet(output_dir, subfolder_name, spritesheet_name):
    subfolder_path = os.path.join(output_dir, subfolder_name)
    images = [f for f in os.listdir(subfolder_path) if os.path.isfile(os.path.join(subfolder_path, f))]
    images.sort()  
    
    if not images:
        print("No images found to pack into a spritesheet.")
        return
    
    start_index = 0
    
    # to skip ds_store file
    '''
    if isMacOS():
        start_index = 1
        print("MacOS")
    else:
        print("Not mac")
    '''
    if images[0].endswith('.DS_Store'):
        start_index = 1
        print("MacOS")
        
    print(start_index)
    first_image_path = os.path.join(subfolder_path, images[start_index])
    with Image.open(first_image_path) as img:
        width,height = img.size
    
    
    columns = int((len(images) - start_index) * 0.5) + 1
    rows = int((len(images) - start_index) + columns - 1) // columns
    spritesheet = Image.new('RGBA', (columns * width, rows * height))
    
    
    for i in range(start_index, len(images)):
        image_filename = images[i]
      
        if image_filename.lower().endswith('.png'):
            image_path = os.path.join(subfolder_path, image_filename)
            with Image.open(image_path) as img:
                x = ((i - start_index) % columns) * width  
                y = ((i - start_index) // columns) * height
                spritesheet.paste(img, (x, y))

    
    spritesheet_path = os.path.join(output_dir, f"{spritesheet_name}.png")
    spritesheet.save(spritesheet_path)
    print(f"Spritesheet saved to: {spritesheet_path}")


class RENDER_OT_render_all(bpy.types.Operator):
    bl_idname = "render.all"
    bl_label = "Render All"

    def execute(self, context):
        scene = bpy.context.scene
        mytool = scene.my_tool
        temp_directory = scene.render.filepath
        output_dir = bpy.path.abspath(scene.render.filepath)
        
        if mytool.render_base:
            settings_base_render()
            create_output_directory("Base")
            bpy.ops.render.render(animation=True)
            scene.render.filepath = temp_directory
            pack_spritesheet(output_dir, "Base", "Base_Spritesheet")
            
        if mytool.render_normal:
            settings_normal_render()
            create_output_directory("Normal")
            bpy.ops.render.render(animation=True)
            scene.render.filepath = temp_directory
            pack_spritesheet(output_dir, "Normal", "Normal_Spritesheet")
        
        settings_base_render()
        
        self.report({'INFO'}, f"This is {self.bl_idname}")
        return {'FINISHED'}

class RENDER_OT_render_base(bpy.types.Operator):
    bl_idname = "render.base"
    bl_label = "Render Base"

    def execute(self, context):
        scene = bpy.context.scene
        settings_base_render()
        temp_directory = scene.render.filepath
        create_output_directory("Base")
        bpy.ops.render.render(animation=True)
        scene.render.filepath = temp_directory
        
        output_dir = bpy.path.abspath(scene.render.filepath)
        pack_spritesheet(output_dir, "Base", "Base_Spritesheet")
        
        
        self.report({'INFO'}, f"This is {self.bl_idname}")
        return {'FINISHED'}
    

class RENDER_OT_render_normal(bpy.types.Operator):
    bl_idname = "render.normal"
    bl_label = "Render Normal"

    def execute(self, context):
        settings_normal_render()
        temp_directory = bpy.context.scene.render.filepath
        create_output_directory("Normal")
        bpy.ops.render.render(animation=True)
        bpy.context.scene.render.filepath = temp_directory
        
        self.report({'INFO'}, f"This is {self.bl_idname}")
        return {'FINISHED'}



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





classes = (RENDER_OT_render_base, RENDER_OT_render_normal, RENDER_OT_render_all, RENDER_PT_model2pixel, SelectDirExample, Render_Settings)



def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.resolution_x = bpy.props.IntProperty(
        name="Resolution X",
        description="Resolution X",
        default=64,
        min=1
    )
    bpy.types.Scene.resolution_y = bpy.props.IntProperty(
        name="Resolution Y",
        description="Resolution Y",
        default=64,
        min=1
    )
    bpy.types.Scene.my_tool = PointerProperty(type=Render_Settings)
    
    bpy.types.Scene.keyframe_start = bpy.props.IntProperty(
        name="Start Frame",
        description="Keyframe Start",
        default=1,
        min=1
    )
    bpy.types.Scene.keyframe_end = bpy.props.IntProperty(
        name="End Frame",
        description="Keyframe End",
        default=100,
        min=1
    )
    bpy.types.Scene.keyframe_step = bpy.props.IntProperty(
        name="Step",
        description="Keyframe Step",
        default=1,
        min=1
    )




def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.resolution_x
    del bpy.types.Scene.resolution_y
    del bpy.types.Scene.my_tool

        
        
if __name__ == "__main__":
    register()