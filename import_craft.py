import os
import bpy
import import_mu
from cfgnode import ConfigNode
VERBOSE = True


def print_blender_data_stats(label):
    nbobj = len(bpy.data.objects)
    nbmat = len(bpy.data.materials)
    nbtex = len(bpy.data.textures)
    nbimg = len(bpy.data.images)

    print ('Loading stats ({}) :\
            \n - {} objects \n - {} materials \
            \n - {} textures \n - {} images \
            \n'.format(label, nbobj, nbmat, nbtex, nbimg))


def rename_textures(ob):
    for index, tex in enumerate(bpy.data.textures):
        texname = tex.name
        if not texname.endswith('texture'):
            tex.name = '{}{}_texture'.format(ob.name, index)


def rename_materials(ob):
    select_children(ob)
    for obj in bpy.context.selected_objects:
        for index, mat in enumerate(obj.material_slots):
            if not mat.material.name.endswith('material'):
                mat.material.name = '{}{}_material'.format(obj.name, index)


def rename_images(ob):
    for index, img in enumerate(bpy.data.images):
        imgname = img.name
        if not imgname.endswith('image'):
            img.name = ob.name + imgname + '_image'
            img.name = '{}{}_image'.format(ob.name, index)


def select_children(obj):
    bpy.context.scene.objects.active = obj
    obj.select = True
    bpy.ops.object.select_grouped(extend=True)


def unselect_all_objects():
    for obj in bpy.context.selected_objects:
        obj.select = False


def duplicate_object_hierarchy(obj):
    unselect_all_objects()
    select_children(obj)
    bpy.ops.object.duplicate(linked=True)
    return bpy.context.scene.objects.active


def remove_object_list(array):
    unselect_all_objects()
    for ob in array:
        select_children(ob)
    bpy.ops.object.delete()


def read_vector(value):
    # Unity is Y-Up, blender is Z-up
    values_str = value.split(',')
    return (float(values_str[0]), float(values_str[2]), float(values_str[1]))


def read_quaternion(value):
    # Unity is xyzw, blender is wxyz. However, Unity is left-handed and
    # blender is right handed. To convert between LH and RH (either
    # direction), just swap y and z and reverse the rotation direction.
    quat_str = value.split(',')
    return (float(quat_str[3]), -float(quat_str[0]), -float(quat_str[2]), -float(quat_str[1]))


def get_extension(filepath):
    ''' returns the extention of the file, without the dot'''
    ext = os.path.splitext(filepath)[-1]
    return ext[1:]


class CraftReader(object):
    def __init__(self):
        self.ship_name = ""
        # Set of required models
        self.prefabs = []
        self.nb_total_parts = 0

    def rename_data_elements(self, ob):
        ''' Rename the datas to avoid overriding while loading parts '''
        unselect_all_objects()
        rename_materials(ob)
        rename_textures(ob)
        rename_images(ob)

    def smooth_object_meshes(self, ob):
        select_children(ob)
        children = bpy.context.selected_objects
        unselect_all_objects()
        for child in children:
            if child.type == "MESH":
                bpy.context.scene.objects.active = child
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.faces_shade_smooth()
                # Need to come back to OBJECT mode to avoid context error
                bpy.ops.object.mode_set(mode='OBJECT')

    def read_parts_models(self, prefabs_dict, colliders):
        for part in prefabs_dict.values():
            unselect_all_objects()
            result = import_mu.import_mu(self, bpy.context, part['mu'], colliders)
            if not result == {'FINISHED'}:
                print('Warning : Error while importing file {}'.format(part['mu']))
                return
            part['object'] = bpy.context.scene.objects.active
            self.smooth_object_meshes(part['object'])
            self.rename_data_elements(part['object'])

    def apply_craft_transformations(self, part_node, blender_object):
        ''' Apply .craft file transformations '''
        blender_object.location = part_node['pos']
        blender_object.rotation_mode = 'QUATERNION'
        blender_object.rotation_quaternion = part_node['rot']

    def generate_parts(self, parts, root, prefabs_dict):
        ''' Generate parts and set it according to corresponding data'''
        for part in parts:
            bpy.context.scene.objects.active = prefabs_dict[part['name']]['object']
            obj = prefabs_dict[part['name']]['object']

            # Duplicate the prefab and apply the transform
            duplicated = duplicate_object_hierarchy(obj)
            self.apply_craft_transformations(part, duplicated)
            bpy.context.scene.objects.active = duplicated
            duplicated.name = part['name'] + '_' + part['key']
            # Pars that have a rescaleFactor parameter need to
            # be rescaled by 1.25
            # see http://wiki.kerbalspaceprogram.com/wiki/CFG_File_Documentation#Asset_Parameters
            if 'rescaleFactor' not in prefabs_dict[part['name']]:
                duplicated.scale = (1.25, 1.25, 1.25)
            duplicated.parent = root
            part['object'] = duplicated

        unselect_all_objects()

    def read_craft_node(self, node, parts_files):
        ''' reads a node and generate the corresponding part'''
        part = dict()
        # A part is PART{} with 'PART' as node[0], so we directly read node[1]
        for label, value in node[1].values:
            if label == 'part':
                self.nb_total_parts += 1
                part_name = value.rsplit('_', 1)[0].replace('.', '_')
                if part_name in parts_files:
                    part['name'] = part_name
                    part['key'] = value.rsplit('_', 1)[1]
                    if part_name not in self.prefabs:
                        self.prefabs.append(part_name)
                else:
                    print('Warning: [CraftReader::read_craft_node] part {} was \
                           avoided since the mu is missing'.format(value))
                    return None

            elif label in ['pos', 'mir']:
                part[label] = read_vector(value)
            elif label in ['rot', 'attRot']:
                part[label] = read_quaternion(value)
            else:
                part[label] = value

        return part

    def read_craft_file(self, filepath, parts_files):
        ''' Read craft file nodes and returns parts list'''
        with open(filepath, 'r') as craft_file:
            craft_data = craft_file.read()

        cfgnode = ConfigNode.load(craft_data)
        # The first value must be the ship name
        self.ship_name = cfgnode.values[0][1]

        craft_parts = []
        for node in cfgnode.nodes:
            part = self.read_craft_node(node, parts_files)
            if part is not None:
                craft_parts.append(part)

        return craft_parts

    def set_craft_data(self, parts, prefabs_dict):
        ''' Generate parts blender object from craft parts list '''
        # Contains the generated prefab's blender objects
        # to be deleted at the end
        originals = []
        if VERBOSE:
            print_blender_data_stats('originals')
        for obj in bpy.context.scene.objects:
            if obj.parent is None:
                originals.append(obj)

        # create root node with craft(ship) name
        root = bpy.data.objects.new(self.ship_name, object_data=None)
        bpy.context.scene.objects.link(root)
        unselect_all_objects()

        self.generate_parts(parts, root, prefabs_dict)
        remove_object_list(originals)

        return {'FINISHED'}


def read_cfg_file(filepath):
    ''' reads the fields of a part.cfg file '''
    with open(filepath, 'r') as partcfg:
        try:
            partcfg_data = partcfg.read()
            cfgnode = ConfigNode.load(partcfg_data)
            return cfgnode
        except UnicodeDecodeError:
            print('Bad encoding found while loading part.cfg')
            return None


def parse_cfg_node(cfgnode, cfgpath, root, files, parts_files):
    ''' Reads the cfg nodes and get the part data'''
    # The cfg is a PART node containing all the data
    # See http://wiki.kerbalspaceprogram.com/wiki/CFG_File_Documentation
    partname = ""
    meshpath = None
    rescalefactor = None

    # The mesh can be defined by a MODEL node -> parsing nodes
    # if cfgnode.nodes[0[1].nodes is not None:
    if cfgnode.nodes[0][1] is not None:
        for node in cfgnode.nodes[0][1].nodes:
            if node[0] == 'MODEL':
                candidate = os.path.join(cfgpath, os.path.split(node[1].values[0][1])[-1] + '.mu')
                if os.path.isfile(candidate):
                    meshpath = candidate
                else:
                    print('The corresponding mu file "{}" is not found. Looking for mesh field'.format(candidate))

    # The mesh can also be defined by 'mesh' token. Also retrieving relevant part data
    for label, value in cfgnode.nodes[0][1].values:
        if label == 'name':
            partname = value.strip().replace('.', '_')
        if meshpath is None and label == 'mesh':
            mupath = os.path.join(cfgpath, value)
            if not os.path.isfile(mupath) or not get_extension(value) == 'mu':
                print('Warning: [CraftReader::parse_cfg_node] The model for {} doesn''t exist or is not \
                       a mu file (not supported). Looking for substitution mu file'.format(partname))
                for f in files:
                    if f.endswith('mu'):
                        print('Warning: [CraftReader::parse_cfg_node] a substitution mu file was used. \
                               The result may be altered')
                        meshpath = os.path.join(root, f)
            else:
                meshpath = mupath
        if label == 'rescaleFactor':
            rescalefactor = value
    if meshpath:
        parts_files[partname] = dict()
        parts_files[partname]['mu'] = meshpath
        if rescalefactor:
            parts_files[partname]['rescaleFactor'] = rescalefactor


def check_parts_in_directory(directory):
    ''' Scan the directory for parts (pairs of .cfg and .mu files) '''
    parts_files = dict()
    for root, dirs, files in os.walk(directory):
        for name in files:
            if get_extension(name) == 'cfg':
                cfg_file_path = os.path.join(root, name)
                cfgnode = read_cfg_file(cfg_file_path)
                if cfgnode is not None:
                    # path in cfg files are incomplete, so we need to join the full path of the cfg file
                    cfg_directory = os.path.split(cfg_file_path)[0]
                    parse_cfg_node(cfgnode, cfg_directory, root, files, parts_files)

    return parts_files


def import_craft(context, craft_file_path, colliders):
    ''' Read a.craft file, retrieve .mu parts and build the ship'''
    directory = os.path.dirname(os.path.realpath(craft_file_path))
    available_parts_files = check_parts_in_directory(directory)

    creader = CraftReader()
    parts_craft = creader.read_craft_file(craft_file_path, available_parts_files)

    used_parts_files = dict()
    for partfile in available_parts_files:
        if partfile in creader.prefabs:
            used_parts_files[partfile] = available_parts_files[partfile]

    # Read mu files
    creader.read_parts_models(used_parts_files, colliders)

    print('INFO : {} were found \n  - {} were used\
           \n  - The final ship has {} parts'.format(len(available_parts_files),
                                                     len(used_parts_files), len(parts_craft)))
    print ('Warning : {} parts were skipped'.format(creader.nb_total_parts - len(parts_craft)))

    # Build craft object
    result = creader.set_craft_data(parts_craft, used_parts_files)
    if VERBOSE:
        print_blender_data_stats('generated')

    return result
