# vim:ts=4:et
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# copied from io_scene_obj

# <pep8 compliant>

bl_info = {
    "name": "Mu model format (KSP)",
    "author": "Bill Currie",
    "blender": (2, 7, 0),
    "api": 35622,
    "location": "File > Import-Export",
    "description": "Import-Export KSP Mu format files. (.mu)",
    "warning": "not even alpha",
    "wiki_url": "",
    "tracker_url": "",
#    "support": 'OFFICIAL',
    "category": "Import-Export"}

# To support reload properly, try to access a package var, if it's there,
# reload everything
if "bpy" in locals():
    import imp
    if "import_mu" in locals():
        imp.reload(import_mu)
    if "export_mu" in locals():
        imp.reload(export_mu)


import bpy
from bpy.props import BoolProperty, FloatProperty, StringProperty, EnumProperty
from bpy.props import FloatVectorProperty, PointerProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper, path_reference_mode, axis_conversion

import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import collider, properties, shader
import import_craft

class ImportMu(bpy.types.Operator, ImportHelper):
    '''Load a KSP Mu (.mu) File'''
    bl_idname = "import_object.ksp_mu"
    bl_label = "Import Mu"

    filename_ext = ".mu"
    filter_glob = StringProperty(default="*.mu", options={'HIDDEN'})

    create_colliders = BoolProperty(name="Create Colliders",
            description="Disable to import only visual and hierarchy elements",
                                    default=True)

    def execute(self, context):
        import import_mu
        keywords = self.as_keywords (ignore=("filter_glob",))
        return import_mu.import_mu(self, context, **keywords)

class ExportMu(bpy.types.Operator, ExportHelper):
    '''Save a KSP Mu (.mu) File'''
    bl_idname = "export_object.ksp_mu"
    bl_label = "Export Mu"

    filename_ext = ".mu"
    filter_glob = StringProperty(default="*.mu", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return (context.active_object != None
                and (not context.active_object.data
                     or type(context.active_object.data) == bpy.types.Mesh))

    def execute(self, context):
        import export_mu
        keywords = self.as_keywords (ignore=("check_existing", "filter_glob"))
        return export_mu.export_mu(self, context, **keywords)

"""
class MDLPanel(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'
    bl_label = 'QF MDL'

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        layout.prop(obj.qfmdl, "eyeposition")
        layout.prop(obj.qfmdl, "synctype")
        layout.prop(obj.qfmdl, "rotate")
        layout.prop(obj.qfmdl, "effects")
        layout.prop(obj.qfmdl, "script")
        layout.prop(obj.qfmdl, "xform")
        layout.prop(obj.qfmdl, "md16")
"""

def menu_func_import(self, context):
    self.layout.operator(ImportMu.bl_idname, text="KSP Mu (.mu)")


def menu_func_export(self, context):
    self.layout.operator(ExportMu.bl_idname, text="KSP Mu (.mu)")


def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_import.append(menu_func_import)
    bpy.types.INFO_MT_file_export.append(menu_func_export)

    properties.register()
    bpy.types.INFO_MT_add.append(collider.menu_func)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_import.remove(menu_func_import)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)
    properties.unregister()
    bpy.types.INFO_MT_add.remove(collider.menu_func)


class CommandLineImporter():
    def execute(self, context, filepath, colliders):
        import import_mu
        return import_mu.import_mu(self, context, filepath, colliders)

    def report(self, type, message):
        print("[{}] {}".format(','.join(type), message))

class CommandLineCraftImporter():
    def execute(self, context, filepath, colliders):
        return import_craft.import_craft(context, filepath, colliders)


def main():
    import sys
    import argparse

    # parse command line arguments
    argv = sys.argv
    argv = [] if "--" not in argv else argv[argv.index("--") + 1:]

    usage_text = """Run blender in background mode with this script:
    blender --background --python " + __file__ + " -- [options]"""

    parser = argparse.ArgumentParser(description=usage_text)
    parser.add_argument("-i", "--input", dest="input_file", metavar='FILE|PATH', help="Import .mu/.craft file")
    parser.add_argument("-o", "--output", dest="output_file", metavar='FILE|PATH', help="Save blender file")
    parser.add_argument("-c", "--colliders", dest="colliders", default=False, action='store_true', help="Create colliders")
    # parser.add_argument("-a", "--enable-animation", dest="enable_animation", action="store_const", const=True, default=False, help="Enable saving of animations")
    # parser.add_argument("-m", "--apply-modifiers", dest="apply_modifiers", action="store_const", const=True, default=False, help="Apply modifiers before exporting")
    # parser.add_argument("-j", "--json-materials", dest="json_materials", action="store_const", const=True, default=False, help="Store materials into JSON format")

    args = parser.parse_args(argv)

    if args.input_file is not None:
        # remove objects from default scene (cube and light)
        for obj in bpy.context.scene.objects:
            bpy.context.scene.objects.unlink(obj)
        for obj in bpy.data.objects:
            bpy.data.objects.remove(obj)

        # Check the file extension
        extension = args.input_file.split('.')[-1]
        if extension == 'craft':
            importer = CommandLineCraftImporter()
            result = importer.execute(bpy.context, args.input_file, args.colliders)
        else:
            importer = CommandLineImporter()
            result = importer.execute(bpy.context, args.input_file, args.colliders)

        if "FINISHED" not in result:
            sys.exit(1)

    if args.output_file is not None:
        bpy.ops.wm.save_as_mainfile(filepath=args.output_file)

if __name__ == "__main__":
    register()
    main()
