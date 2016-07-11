import os
import sys

import bpy
from io_object_mu import *
from io_object_mu import import_craft

class CommandLineImporter():
    def execute(self, context, filepath, colliders):
        return import_mu.import_mu(self, context, filepath, colliders, use_classic_material=True)

    def report(self, type, message):
        print("[{}] {}".format(','.join(type), message))

class CommandLineCraftImporter():
    def execute(self, context, filepath, colliders):
        return import_craft.import_craft(context, filepath, colliders, use_classic_material=True)

def main():
    import argparse

    # parse command line arguments
    argv = sys.argv
    argv = [] if "--" not in argv else argv[argv.index("--") + 1:]

    usage_text = """Run blender in background mode with this script:
    blender --background --python " + __file__ + " -- [options]"""

    parser = argparse.ArgumentParser(description=usage_text)
    parser.add_argument("-i",
                        "--input",
                        dest="input_file",
                        metavar='FILE|PATH',
                        help="Import .mu/.craft file")
    parser.add_argument("-o",
                        "--output",
                        dest="output_file",
                        metavar='FILE|PATH',
                        help="Save blender file")
    parser.add_argument("-c",
                        "--colliders",
                        dest="colliders",
                        default=False,
                        action='store_true',
                        help="Create colliders")

    args = parser.parse_args(argv)
    register()
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
    main()
