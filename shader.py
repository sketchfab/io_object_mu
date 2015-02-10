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

# <pep8 compliant>

import bpy
import functools
from mu import MuEnum


def create_texture_slot(mat, texture, use_alpha):
    ''' Create the slot and set the texture '''
    if texture.name not in bpy.data.textures:
        print("Warning : the texture {} doesn't exist".format(texture.name))
        return None
    slot = mat.texture_slots.add()
    slot.texture = bpy.data.textures[texture.name]
    slot.texture_coords = 'UV'
    slot.texture.image.use_alpha = use_alpha

    return slot


def set_diffuse(mumat, mat, textures, use_alpha):
    ''' Set diffuse channel '''
    slot = create_texture_slot(mat, textures[mumat.mainTex.index], use_alpha)
    if slot:
        slot.use_map_color_diffuse = True
        slot.diffuse_color_factor = 1
        mat.diffuse_intensity = 1
        if use_alpha:
            mat.use_transparency = True
            mat.transparency_method = 'Z_TRANSPARENCY'
            slot.use_map_alpha = True
            slot.alpha_factor = 1
            slot.blend_type = 'MULTIPLY'


def set_specular(mumat, mat, textures, use_alpha):
    ''' Set KSP specular conversion channel '''
    slot = create_texture_slot(mat, textures[mumat.mainTex.index], True)
    if slot:
        mat.specular_color = mumat.specColor[0:-1]
        mat.specular_hardness = mumat.shininess
        mat.specular_intensity = 0

        slot = create_texture_slot(mat, textures[mumat.mainTex.index], True)
        slot.use_map_hardness = 1
        slot.texture.use_alpha = use_alpha
        slot.texture.image.use_alpha = False


def set_emissive(mumat, mat, textures):
    ''' Set KSP emissive channel '''
    slot = create_texture_slot(mat, textures[mumat.emissive.index], True)
    if slot:
        slot.use_map_emission = True
        slot.use_map_color_diffuse = False
        mat.diffuse_intensity = 0


def set_bump(mumat, mat, textures):
    ''' Set bump channel '''
    slot = create_texture_slot(mat, textures[mumat.bumpMap.index], False)
    if slot:
        slot.use_map_normal = True
        slot.use_map_color_diffuse = False
        slot.texture.use_alpha = False
        slot.normal_factor = 0.3


def make_material(mumat, mutextures):
    mat = bpy.data.materials.new(mumat.name)
    shader = MuEnum.ShaderNames[mumat.type]

    set_diff = functools.partial(set_diffuse, mumat, mat, mutextures)
    set_spec = functools.partial(set_specular, mumat, mat, mutextures)

    if shader == 'KSP/Specular':
        set_spec(False)
    elif shader == 'KSP/Bumped':
        set_diff(False)
        set_bump(mumat, mat, mutextures)
    elif shader == 'KSP/Bumped Specular':
        set_spec(False)
        set_bump(mumat, mat, mutextures)
    elif shader == 'KSP/Emissive/Diffuse':
        set_diff(False)
        set_emissive(mumat, mat, mutextures)
    elif shader == 'KSP/Emissive/Specular':
        set_spec(False)
        set_emissive(mumat, mat, mutextures)
    elif shader == 'KSP/Emissive/Bumped Specular':
        set_spec(False)
        set_emissive(mumat, mat, mutextures)
        set_bump(mumat, mat, mutextures)
    elif shader == 'KSP/Alpha/Cutoff':
        set_diff(True)
    elif shader == 'KSP/Alpha/Cutoff Bumped':
        set_diff(True)
        set_bump(mumat, mat, mutextures)
    elif shader == 'KSP/Alpha/Translucent':
        set_diff(True)
    elif shader == 'KSP/Alpha/Translucent Specular':
        set_spec(True)
    elif shader == 'KSP/Alpha/Unlit Transparent':
        set_diff(True)
        mat.emmit = 1
    elif shader == 'KSP/Unlit':
        set_diff(False)
        mat.emmit = 1
    elif shader == 'KSP/Diffuse':
        set_diff(False)

    return mat


class MuMaterialPanel(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'
    bl_label = 'Mu Shader'

    @classmethod
    def poll(cls, context):
        return context.material is not None

    def drawtex(self, layout, texprop):
        box = layout.box()
        box.prop(texprop, "tex")
        box.prop(texprop, "scale")
        box.prop(texprop, "offset")

    def draw(self, context):
        layout = self.layout
        matprops = context.material.mumatprop
        row = layout.row()
        col = row.column()
        col.prop(matprops, "shader")
        if matprops.shader == 'KSP/Specular':
            self.drawtex(col, matprops.mainTex)
            col.prop(matprops, "specColor")
            col.prop(matprops, "shininess")
        elif matprops.shader == 'KSP/Bumped':
            self.drawtex(col, matprops.mainTex)
            self.drawtex(col, matprops.bumpMap)
        elif matprops.shader == 'KSP/Bumped Specular':
            self.drawtex(col, matprops.mainTex)
            self.drawtex(col, matprops.bumpMap)
            col.prop(matprops, "specColor")
            col.prop(matprops, "shininess")
        elif matprops.shader == 'KSP/Emissive/Diffuse':
            self.drawtex(col, matprops.mainTex)
            self.drawtex(col, matprops.emissive)
            col.prop(matprops, "emissiveColor")
        elif matprops.shader == 'KSP/Emissive/Specular':
            self.drawtex(col, matprops.mainTex)
            col.prop(matprops, "specColor")
            col.prop(matprops, "shininess")
            self.drawtex(col, matprops.emissive)
            col.prop(matprops, "emissiveColor")
        elif matprops.shader == 'KSP/Emissive/Bumped Specular':
            self.drawtex(col, matprops.mainTex)
            self.drawtex(col, matprops.bumpMap)
            col.prop(matprops, "specColor")
            col.prop(matprops, "shininess")
            self.drawtex(col, matprops.emissive)
            col.prop(matprops, "emissiveColor")
        elif matprops.shader == 'KSP/Alpha/Cutoff':
            self.drawtex(col, matprops.mainTex)
            col.prop(matprops, "cutoff")
        elif matprops.shader == 'KSP/Alpha/Cutoff Bumped':
            self.drawtex(col, matprops.mainTex)
            self.drawtex(col, matprops.bumpMap)
            col.prop(matprops, "cutoff")
        elif matprops.shader == 'KSP/Alpha/Translucent':
            self.drawtex(col, matprops.mainTex)
        elif matprops.shader == 'KSP/Alpha/Translucent Specular':
            self.drawtex(col, matprops.mainTex)
            col.prop(matprops, "gloss")
            col.prop(matprops, "specColor")
            col.prop(matprops, "shininess")
        elif matprops.shader == 'KSP/Alpha/Unlit Transparent':
            self.drawtex(col, matprops.mainTex)
            col.prop(matprops, "color")
        elif matprops.shader == 'KSP/Unlit':
            self.drawtex(col, matprops.mainTex)
            col.prop(matprops, "color")
        elif matprops.shader == 'KSP/Diffuse':
            self.drawtex(col, matprops.mainTex)
