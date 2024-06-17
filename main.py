bl_info = {
    "name": "model2pixel",
    "author": "Connor Wright",
    "version": (0, 0, 1),
    "blender": (2, 80, 0),
    "location": "3D Viewport > Sidebar > Render category",
    "description": "My custom operator buttons",
    "category": "Development",
}

import bpy




class RENDER_PT_model2pixel(bpy.types.Panel):  # class naming convention ‘CATEGORY_PT_name’

    # where to add the panel in the UI
    bl_space_type = "VIEW_3D"  # 3D Viewport area (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/space_type_items.html#rna-enum-space-type-items)
    bl_region_type = "UI"  # Sidebar region (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/region_type_items.html#rna-enum-region-type-items)

    bl_category = "Render"  # found in the Sidebar
    bl_label = "model2pixel"  # found at the top of the Panel

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        row = layout.row()
        row.prop(scene, "resolution_x")
        row.prop(scene, "resolution_y")

        row = layout.row()
        row.operator("render.base", text="Render Base")
        row = layout.row()
        row.operator("render.normal", text="Render Normal")
        #row = layout.row()
        #row.operator("object.shade_smooth", text="Shade Smooth")
        row = layout.row()
        #row.prop(scene, "scene.render.filepath", text="")
        row.prop(scene.render, "filepath", text="Output Directory")
        #row.operator("render.select_dir", text="Output Directory")
        #row.prop(scene, "render.select_dir")
        





    
    
def swap_render_engine(new_engine):
    bpy.context.scene.render.engine = new_engine
    
    
    
def settings_base_render():
    swap_render_engine("BLENDER_EEVEE")
    scene = bpy.context.scene
    scene.render.resolution_x = scene.resolution_x
    scene.render.resolution_y = scene.resolution_y
    scene.render.filter_size = 0.01
    scene.render.film_transparent = True
    scene.render.image_settings.compression = 0
    
    
def settings_normal_render():
    swap_render_engine("BLENDER_WORKBENCH")
    scene = bpy.context.scene
    scene.render.resolution_x = scene.resolution_x
    scene.render.resolution_y = scene.resolution_y
    scene.render.filter_size = 0.01
    scene.render.film_transparent = True
    scene.render.image_settings.compression = 0
    scene.display.shading.studio_light = "check_normal+y.exr"



def create_output_directory(subfolder_name):
    parent_path = scene.render.filepath
    subfolder_path = os.path.join(parent_path, subfolder_name)
    os.makedirs(subfolder_path, exist_ok=True)
    #scene.render.filepath = os.path.join(subfolder_path, "")



class RENDER_OT_render_base(bpy.types.Operator):
    bl_idname = "render.base"
    bl_label = "Render Base"

    def execute(self, context):
        settings_base_render()
        create_output_directory("Base")
        self.report({'INFO'}, f"This is {self.bl_idname}")
        return {'FINISHED'}
    

class RENDER_OT_render_normal(bpy.types.Operator):
    bl_idname = "render.normal"
    bl_label = "Render Normal"

    def execute(self, context):
        settings_normal_render()
        create_output_directory("Normal")
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
        #context.scene.output_directory = self.directory
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







classes = (RENDER_OT_render_base, RENDER_OT_render_normal, RENDER_PT_model2pixel, SelectDirExample)



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



def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.resolution_x
    del bpy.types.Scene.resolution_y
        
        
if __name__ == "__main__":
    register()