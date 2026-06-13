bl_info = {
    "name": "Stitch Maker - Knit/Crochet Pattern Designer",
    "blender": (3, 0, 0),
    "category": "Add Mesh",
    "version": (1, 0, 0),
    "author": "boyperfect-maker",
    "description": "Create and design knitting/crochet patterns with pixel grid stitching, ray casting, and export capabilities",
    "location": "View3D > Sidebar > Stitch Maker",
    "doc_url": "https://github.com/boyperfect-maker/perfect-maker",
    "tracker_url": "https://github.com/boyperfect-maker/perfect-maker/issues",
}

import bpy
import json
import os
from pathlib import Path
from mathutils import Vector
import numpy as np
from PIL import Image
from bpy.props import (
    StringProperty,
    BoolProperty,
    FloatProperty,
    IntProperty,
    FloatVectorProperty,
)
from bpy.types import (
    Panel,
    Operator,
    PropertyGroup,
    Scene,
    Object,
)


# ==================== PROPERTIES ====================

class StitchProperties(PropertyGroup):
    """Store stitch tool settings"""
    
    stitch_tool_active: BoolProperty(
        name="Stitch Tool Active",
        description="Enable/disable stitch tool",
        default=False
    )
    
    stitch_color: FloatVectorProperty(
        name="Stitch Color",
        subtype='COLOR',
        min=0.0,
        max=1.0,
        default=(1.0, 0.0, 1.0, 1.0),
        size=4
    )
    
    stitch_opacity: FloatProperty(
        name="Stitch Opacity",
        min=0.1,
        max=1.0,
        default=0.8,
        step=1
    )
    
    stitch_thickness: IntProperty(
        name="Stitch Thickness",
        min=1,
        max=10,
        default=2
    )
    
    thread_color: FloatVectorProperty(
        name="Thread Color",
        subtype='COLOR',
        min=0.0,
        max=1.0,
        default=(1.0, 0.0, 0.0, 1.0),
        size=4
    )
    
    image_path: StringProperty(
        name="Image Path",
        subtype='FILE_PATH',
        description="Path to pixel art image"
    )
    
    texture_path: StringProperty(
        name="Texture Path",
        subtype='FILE_PATH',
        description="Path to texture image"
    )


def register_properties():
    """Register property groups"""
    bpy.utils.register_class(StitchProperties)
    Scene.stitch_props = bpy.props.PointerProperty(type=StitchProperties)


def unregister_properties():
    """Unregister property groups"""
    del Scene.stitch_props
    bpy.utils.unregister_class(StitchProperties)


# ==================== OPERATORS ====================

class STITCH_OT_LoadImage(Operator):
    """Load pixel art image and create grid"""
    bl_idname = "stitch.load_image"
    bl_label = "Load Pixel Art"
    
    filter_glob: StringProperty(default="*.png;*.jpg;*.jpeg", options={'HIDDEN'})
    
    filepath: StringProperty(
        name="File Path",
        description="Path to image file",
        subtype='FILE_PATH'
    )
    
    def execute(self, context):
        props = context.scene.stitch_props
        props.image_path = self.filepath
        
        # Create pixel grid from image
        create_pixel_grid(self.filepath, context)
        
        self.report({'INFO'}, f"Loaded image: {self.filepath}")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class STITCH_OT_LoadTexture(Operator):
    """Load texture image"""
    bl_idname = "stitch.load_texture"
    bl_label = "Load Texture"
    
    filter_glob: StringProperty(default="*.png;*.jpg;*.jpeg", options={'HIDDEN'})
    
    filepath: StringProperty(
        name="File Path",
        description="Path to texture file",
        subtype='FILE_PATH'
    )
    
    def execute(self, context):
        props = context.scene.stitch_props
        props.texture_path = self.filepath
        apply_texture(self.filepath, context)
        
        self.report({'INFO'}, f"Loaded texture: {self.filepath}")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class STITCH_OT_ToggleTool(Operator):
    """Toggle stitch tool on/off"""
    bl_idname = "stitch.toggle_tool"
    bl_label = "Toggle Stitch Tool"
    
    def execute(self, context):
        props = context.scene.stitch_props
        props.stitch_tool_active = not props.stitch_tool_active
        
        status = "ON" if props.stitch_tool_active else "OFF"
        self.report({'INFO'}, f"Stitch Tool: {status}")
        return {'FINISHED'}


class STITCH_OT_CreateStitch(Operator):
    """Create a dashed stitch line"""
    bl_idname = "stitch.create_stitch"
    bl_label = "Create Stitch"
    
    # Store stitch points
    stitch_start: FloatVectorProperty(name="Start Point")
    stitch_end: FloatVectorProperty(name="End Point")
    
    def execute(self, context):
        props = context.scene.stitch_props
        
        # Create dashed line object
        create_dashed_stitch(
            self.stitch_start,
            self.stitch_end,
            props.stitch_color,
            props.stitch_opacity,
            props.stitch_thickness,
            context
        )
        
        self.report({'INFO'}, "Stitch created!")
        return {'FINISHED'}


class STITCH_OT_ClearStitches(Operator):
    """Clear all stitches"""
    bl_idname = "stitch.clear_stitches"
    bl_label = "Clear Stitches"
    
    def execute(self, context):
        # Delete all stitch objects
        for obj in bpy.data.objects:
            if obj.name.startswith("Stitch_"):
                bpy.data.objects.remove(obj, do_unlink=True)
        
        self.report({'INFO'}, "All stitches cleared!")
        return {'FINISHED'}


class STITCH_OT_ExportPNG(Operator):
    """Export stitches as PNG"""
    bl_idname = "stitch.export_png"
    bl_label = "Export as PNG"
    
    filepath: StringProperty(
        name="File Path",
        description="Path to save PNG",
        subtype='FILE_PATH'
    )
    
    def execute(self, context):
        # Render to image
        export_viewport_to_png(self.filepath, context)
        
        self.report({'INFO'}, f"Exported to: {self.filepath}")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class STITCH_OT_ExportJSON(Operator):
    """Export stitch data as JSON"""
    bl_idname = "stitch.export_json"
    bl_label = "Export as JSON"
    
    filepath: StringProperty(
        name="File Path",
        description="Path to save JSON",
        subtype='FILE_PATH'
    )
    
    def execute(self, context):
        # Collect stitch data
        export_stitches_json(self.filepath, context)
        
        self.report({'INFO'}, f"Exported to: {self.filepath}")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class STITCH_OT_ChangeThreadColor(Operator):
    """Change thread color of selected mesh"""
    bl_idname = "stitch.change_thread_color"
    bl_label = "Change Thread Color"
    
    def execute(self, context):
        props = context.scene.stitch_props
        obj = context.active_object
        
        if obj and obj.data.materials:
            mat = obj.data.materials[0]
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            bsdf.inputs[0].default_value = props.thread_color
            self.report({'INFO'}, "Thread color updated!")
        else:
            self.report({'WARNING'}, "No material found!")
        
        return {'FINISHED'}


def register_operators():
    """Register all operators"""
    operators = [
        STITCH_OT_LoadImage,
        STITCH_OT_LoadTexture,
        STITCH_OT_ToggleTool,
        STITCH_OT_CreateStitch,
        STITCH_OT_ClearStitches,
        STITCH_OT_ExportPNG,
        STITCH_OT_ExportJSON,
        STITCH_OT_ChangeThreadColor,
    ]
    for cls in operators:
        bpy.utils.register_class(cls)


def unregister_operators():
    """Unregister all operators"""
    operators = [
        STITCH_OT_ChangeThreadColor,
        STITCH_OT_ExportJSON,
        STITCH_OT_ExportPNG,
        STITCH_OT_ClearStitches,
        STITCH_OT_CreateStitch,
        STITCH_OT_ToggleTool,
        STITCH_OT_LoadTexture,
        STITCH_OT_LoadImage,
    ]
    for cls in operators:
        bpy.utils.unregister_class(cls)


# ==================== UTILITY FUNCTIONS ====================

def create_pixel_grid(image_path, context):
    """Load image and create pixel grid in Blender"""
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return
    
    try:
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # Create collection for pixel grid
        grid_collection = bpy.data.collections.new("PixelGrid")
        context.scene.collection.children.link(grid_collection)
        
        height, width = img_array.shape[:2]
        pixel_size = 1.0
        
        for y in range(height):
            for x in range(width):
                # Get pixel color
                if img_array.shape[2] == 4:  # RGBA
                    r, g, b, a = img_array[y, x]
                    if a == 0:  # Skip transparent
                        continue
                else:  # RGB
                    r, g, b = img_array[y, x][:3]
                
                # Normalize color
                color = (r / 255.0, g / 255.0, b / 255.0, 1.0)
                
                # Create plane mesh
                bpy.ops.mesh.primitive_plane_add(
                    size=pixel_size,
                    location=(
                        (x - width / 2) * pixel_size,
                        (height / 2 - y) * pixel_size,
                        0
                    )
                )
                
                obj = context.active_object
                obj.name = f"Pixel_{x}_{y}"
                
                # Create material
                mat = bpy.data.materials.new(name=f"PixelMat_{x}_{y}")
                mat.use_nodes = True
                bsdf = mat.node_tree.nodes["Principled BSDF"]
                bsdf.inputs[0].default_value = color
                
                obj.data.materials.append(mat)
                
                # Move to collection
                for coll in obj.users_collection:
                    coll.objects.unlink(obj)
                grid_collection.objects.link(obj)
        
        print(f"Created pixel grid: {width}x{height}")
    
    except Exception as e:
        print(f"Error loading image: {e}")


def create_dashed_stitch(start, end, color, opacity, thickness, context):
    """Create a dashed stitch line between two points"""
    
    # Create curve for stitch
    curve_data = bpy.data.curves.new(name="StitchCurve", type='CURVE')
    curve_data.dimensions = '3D'
    
    polyline = curve_data.splines.new('BEZIER')
    polyline.points.add(1)
    polyline.points[0].co = (*start, 1)
    polyline.points[1].co = (*end, 1)
    polyline.resolution_u = 12
    
    curve_obj = bpy.data.objects.new(f"Stitch_{len(bpy.data.objects)}", curve_data)
    context.collection.objects.link(curve_obj)
    
    # Create material for stitch
    mat = bpy.data.materials.new(name="StitchMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs[0].default_value = color
    bsdf.inputs[18].default_value = opacity  # Alpha
    
    curve_data.materials.append(mat)
    
    # Set curve thickness
    curve_data.resolution_u = thickness * 2
    curve_data.bevel_depth = 0.1 * thickness
    
    print(f"Created stitch from {start} to {end}")


def apply_texture(texture_path, context):
    """Apply texture to pixel grid"""
    if not os.path.exists(texture_path):
        print(f"Texture not found: {texture_path}")
        return
    
    try:
        texture_img = bpy.data.images.load(texture_path)
        
        # Apply to all pixel materials
        for mat in bpy.data.materials:
            if "PixelMat" in mat.name:
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links
                
                # Add image texture node
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.image = texture_img
                
                bsdf = nodes["Principled BSDF"]
                links.new(tex_node.outputs[0], bsdf.inputs[0])
        
        print(f"Applied texture: {texture_path}")
    
    except Exception as e:
        print(f"Error applying texture: {e}")


def export_viewport_to_png(filepath, context):
    """Export current viewport as PNG"""
    try:
        # Set up rendering
        context.scene.render.filepath = filepath
        context.scene.render.image_settings.file_format = 'PNG'
        context.scene.render.resolution_x = 1920
        context.scene.render.resolution_y = 1080
        
        # Render
        bpy.ops.render.render(write_still=True)
        
        print(f"Exported PNG: {filepath}")
    
    except Exception as e:
        print(f"Error exporting PNG: {e}")


def export_stitches_json(filepath, context):
    """Export all stitch data to JSON"""
    try:
        stitches = []
        
        for obj in bpy.data.objects:
            if obj.name.startswith("Stitch_"):
                stitch_data = {
                    "name": obj.name,
                    "location": list(obj.location),
                    "rotation": list(obj.rotation_euler),
                    "scale": list(obj.scale),
                    "color": list(context.scene.stitch_props.stitch_color),
                    "opacity": context.scene.stitch_props.stitch_opacity,
                    "thickness": context.scene.stitch_props.stitch_thickness,
                }
                stitches.append(stitch_data)
        
        export_data = {
            "timestamp": str(bpy.context.scene.frame_current),
            "stitch_count": len(stitches),
            "stitches": stitches
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Exported JSON: {filepath}")
    
    except Exception as e:
        print(f"Error exporting JSON: {e}")


# ==================== UI PANELS ====================

class STITCH_PT_MainPanel(Panel):
    """Main stitch maker panel"""
    bl_label = "Stitch Maker"
    bl_idname = "STITCH_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Stitch Maker'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.stitch_props
        
        # File loading
        layout.label(text="Image & Texture:", icon='IMAGE_DATA')
        layout.operator("stitch.load_image", text="Load Pixel Art")
        layout.operator("stitch.load_texture", text="Load Texture")
        
        # Stitch tool
        layout.separator()
        layout.label(text="Stitch Tool:", icon='BRUSH_DATA')
        layout.prop(props, "stitch_tool_active", text="Tool Active")
        layout.operator("stitch.toggle_tool", text="Toggle Stitch Tool")
        
        # Color controls
        layout.separator()
        layout.label(text="Colors:", icon='COLOR')
        layout.prop(props, "stitch_color", text="Stitch Color")
        layout.prop(props, "thread_color", text="Thread Color")
        layout.operator("stitch.change_thread_color", text="Apply Thread Color")
        
        # Stitch settings
        layout.separator()
        layout.label(text="Settings:", icon='SETTINGS')
        layout.prop(props, "stitch_opacity", text="Opacity")
        layout.prop(props, "stitch_thickness", text="Thickness")
        
        # Stitch operations
        layout.separator()
        layout.label(text="Operations:", icon='TOOL_SETTINGS')
        layout.operator("stitch.clear_stitches", text="Clear All Stitches", icon='TRASH')
        
        # Export
        layout.separator()
        layout.label(text="Export:", icon='EXPORT')
        layout.operator("stitch.export_png", text="Export as PNG", icon='RENDER_RESULT')
        layout.operator("stitch.export_json", text="Export as JSON", icon='TEXT')


class STITCH_PT_DebugPanel(Panel):
    """Debug panel for troubleshooting"""
    bl_label = "Debug Info"
    bl_idname = "STITCH_PT_debug"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Stitch Maker'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.stitch_props
        
        layout.label(text="Tool Status:")
        layout.label(text=f"Active: {props.stitch_tool_active}")
        layout.label(text=f"Color: {props.stitch_color}")
        layout.label(text=f"Opacity: {props.stitch_opacity}")
        layout.label(text=f"Thickness: {props.stitch_thickness}")
        
        layout.separator()
        layout.label(text="Objects in Scene:")
        layout.label(text=f"Total: {len(bpy.data.objects)}")
        
        stitch_count = len([o for o in bpy.data.objects if o.name.startswith("Stitch_")])
        layout.label(text=f"Stitches: {stitch_count}")


def register_ui():
    """Register UI panels"""
    bpy.utils.register_class(STITCH_PT_MainPanel)
    bpy.utils.register_class(STITCH_PT_DebugPanel)


def unregister_ui():
    """Unregister UI panels"""
    bpy.utils.unregister_class(STITCH_PT_DebugPanel)
    bpy.utils.unregister_class(STITCH_PT_MainPanel)


# ==================== REGISTRATION ====================

def register():
    """Register addon"""
    register_properties()
    register_operators()
    register_ui()
    print("✓ Stitch Maker addon registered successfully!")


def unregister():
    """Unregister addon"""
    unregister_ui()
    unregister_operators()
    unregister_properties()
    print("✓ Stitch Maker addon unregistered!")


if __name__ == "__main__":
    register()
