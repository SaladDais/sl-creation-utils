#    Morph target to SL Weights
#    Mimics morph target animation using skeletal animation and bone repositioning
#    Copyright (C) 2021 Salad Dais

#    Incorporates parts of VertexColorToWeight
#    (c) 2015,2020 Michel J. Anders (varkenvarken)

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
import functools

import bpy
import bpy.utils.previews
from bpy.types import Operator
from mathutils import Vector
from typing import List

bl_info = {
    "name": "Morph Target to SL Weights",
    "description": "Morph target animation for Second Life Animesh",
    "author": "Salad Dais",
    "version": (0, 0, 8),
    "blender": (2, 93, 1),
    "location": "View3D > Weight Paint > Weights > Morph Target to SL Weights",
    "category": "Node",
}


VERTEX_GROUP_NAMES = [
    # +x / -X
    "mHipLeft",
    "mHipRight",
    # +Y / -Y
    "mHindLimb1Left",
    "mHindLimb1Right",
    # +Z / -Z
    "mTail1",
    "mGroin",
    # Null, influences need to add up to 100% so this gives unused
    # joint influence back to the pelvis (which should not move.)
    "mPelvis",
]


# Max amount in meters that we can move a vertex in total
# This limit is imposed by SL's animation format clamping positions on any
# given axis to 5m.
MAX_MOVEMENT = 5.0


def vec_motion_all_axes(coord: Vector) -> float:
    return sum([abs(x) for x in (coord.x, coord.y, coord.z)])


def vector_to_weights(coord: Vector) -> List[float]:
    # Assumes all components are -1.0 to 1.0
    weights = [0.0] * len(VERTEX_GROUP_NAMES)
    x_idx = 0
    y_idx = 2
    z_idx = 4
    if coord.x < 0.0:
        x_idx = 1
    if coord.y < 0.0:
        y_idx = 3
    if coord.z < 0.0:
        z_idx = 5
    # Calculate weight based on magnitude of each axis
    weights[x_idx] = abs(coord.x) / MAX_MOVEMENT
    weights[y_idx] = abs(coord.y) / MAX_MOVEMENT
    weights[z_idx] = abs(coord.z) / MAX_MOVEMENT
    # Unused available motion magnitude goes to the "null" joint
    weights[-1] = 1.0 - sum(weights)
    return weights


class WeightException(Exception):
    pass


def apply_pos_offset_weights(source_obj, target_obj):
    bpy.ops.object.mode_set(mode='OBJECT')

    # Set to active for bpy.ops.object.vertex_group_add()
    target_obj.select_set(True)
    bpy.context.view_layer.objects.active = target_obj
    last_active_vgroup = target_obj.vertex_groups.active

    # Get or create the vertex groups we need for morph target animation
    vertex_groups = []
    for vertex_group_name in VERTEX_GROUP_NAMES:
        found_group = None
        for vgroup in target_obj.vertex_groups:
            if vgroup.name == vertex_group_name:
                found_group = vgroup
                break
        if found_group is None:
            bpy.ops.object.vertex_group_add()
            found_group = target_obj.vertex_groups.active
            found_group.name = vertex_group_name
        vertex_groups.append(found_group)

    # Set the active vertex group back to what it was
    if last_active_vgroup:
        target_obj.vertex_groups.active = last_active_vgroup

    # Walk the list of vertices and position deltas to weights for a given
    # vert in mesh-local space
    for loop in target_obj.data.loops:
        vi = loop.vertex_index
        # co means position, does not take into account modifiers or object transforms
        # so you must apply both manually first!
        diff = source_obj.data.vertices[vi].co - target_obj.data.vertices[vi].co
        # Total movement on all axes must be less than MAX_MOVEMENT
        total_movement = vec_motion_all_axes(diff)
        if total_movement > MAX_MOVEMENT:
            raise WeightException(f"Vertex movement too great! {total_movement}")

        # Calculate weights for position delta and assign to the vertex groups.
        for vertex_group, group_weight in zip(vertex_groups, vector_to_weights(diff)):
            vertex_group.add([vi], group_weight, 'REPLACE')

    # Force an update
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

    bpy.context.view_layer.update()
    target_obj.select_set(False)


def validate_object_set(obj_list):
    # Same number of verts in each?
    if len(set(len(x.data.vertices) for x in obj_list)) != 1:
        raise WeightException(f"Vertex count mismatch between objects")

    if not all(x.type == 'MESH' for x in obj_list):
        raise WeightException(f"All objects must be mesh")


def restore_selection(f):
    @functools.wraps(f)
    def wrapper(self, context):
        # to restore object selections
        orig_active_object = context.active_object
        orig_selected_objects = context.selected_objects
        try:
            return f(self, context)
        finally:
            # restore object selections
            for obj in orig_selected_objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = orig_active_object
    return wrapper


class MorphTargetToSLWeights(Operator):
    bl_idname = "mesh.morphtargettoslweights_bake"
    bl_label = "Morph Target to SL Weights"
    bl_description = "Select source object, then target object"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        """
        Only visible in weight paint mode if the active object is a mesh.
        """
        p = (context.mode == 'PAINT_WEIGHT' and
             isinstance(context.active_object, bpy.types.Object) and
             isinstance(context.active_object.data, bpy.types.Mesh))
        return p

    @restore_selection
    def execute(self, context):
        orig_active_object = context.active_object
        orig_selected_objects = context.selected_objects
        if len(orig_selected_objects) != 2:
            self.report({'ERROR'}, f"Must have exactly two objects selected")
            return {'CANCELLED'}

        try:
            validate_object_set(orig_selected_objects)
        except WeightException as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        # Clear the selection
        for obj in orig_selected_objects:
            obj.select_set(False)

        target_obj = orig_active_object
        source_obj = [x for x in orig_selected_objects if x != orig_active_object][0]

        try:
            apply_pos_offset_weights(source_obj, target_obj)
        except WeightException as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        return {'FINISHED'}


def copy_to_origin(obj: bpy.types.Object, offset_z: float = 0.0) -> bpy.types.Object:
    new_obj = obj.copy()
    new_obj.data = obj.data.copy()
    bpy.context.collection.objects.link(new_obj)
    new_obj.matrix_world.translation = (0.0, 0.0, offset_z)
    return new_obj


def join_objects(objects: List[bpy.types.Object]):
    ctx = bpy.context.copy()
    ctx['active_object'] = objects[0]
    ctx['selected_objects'] = objects
    ctx['selected_editable_objects'] = objects
    bpy.ops.object.join(ctx)  # noqa: typing stubs don't know about context overrides


class SLMorphTargetAnimation(Operator):
    bl_idname = "object.slmorphtargetanimation"
    bl_label = "SL Morph Target Animation from Nodes"
    bl_description = "Make a morph target animation set, ordered by node name"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        p = (context.mode == 'OBJECT' and
             isinstance(context.active_object, bpy.types.Object) and
             isinstance(context.active_object.data, bpy.types.Mesh))
        return p

    @restore_selection
    def execute(self, context):
        orig_selected_objects = context.selected_objects

        if len(orig_selected_objects) < 2:
            self.report({'ERROR'}, f"Must have more than one object selected!")
            return {'CANCELLED'}

        # TODO: figure out the other cases later
        if len(orig_selected_objects) % 3 != 0:
            self.report({'ERROR'}, f"Number of nodes must be divisible by three!")
            return {'CANCELLED'}

        try:
            validate_object_set(orig_selected_objects)
        except WeightException as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        seen_materials = set()
        for obj in orig_selected_objects:
            for slot in obj.material_slots:
                if slot.material.name in seen_materials:
                    self.report({'ERROR'}, f"Objects must not share materials!")
                    return {'CANCELLED'}
                seen_materials.add(slot.material.name)

        # Clear the selection
        for obj in orig_selected_objects:
            obj.select_set(False)

        to_weight = sorted(orig_selected_objects, key=lambda x: x.name)
        weighted = []
        offset_z = 0.0
        while to_weight:
            # We'll end up with two meshes for every 3 keyframes,
            # left and right which both morph towards mid.
            # basic flow for animating is:
            # * show left face
            # * animate to 100% morphed
            # * show right face
            # * animate back down to 0% morphed
            # If you want this to loop properly then last frame of a set should be the
            # same as the first frame as the next set. currently you have to duplicate manually.
            left, mid, right = to_weight[:3]
            left_clone = copy_to_origin(left, offset_z)
            right_clone = copy_to_origin(right, offset_z)
            apply_pos_offset_weights(mid, left_clone)
            bpy.ops.object.mode_set(mode='OBJECT')
            apply_pos_offset_weights(mid, right_clone)
            bpy.ops.object.mode_set(mode='OBJECT')
            weighted.extend((left_clone, right_clone))
            to_weight = to_weight[3:]
            # Vertices at the same position will be merged at some point
            # in the creation pipeline even though they have different weights! Need
            # to have the position differ slightly so that doesn't happen.
            # Not clear if it's the Collada exporter, colladadom or the llmesh
            # conversion stuff that's doing it.
            offset_z += 0.00005

        join_objects(weighted)
        return {'FINISHED'}


########################################################################
# MAIN & REGISTER
########################################################################


def menu_func_weight(self, _context):
    self.layout.operator(MorphTargetToSLWeights.bl_idname, text="Morph Target To SL Weights", icon='PLUGIN')


def menu_func_object(self, _context):
    self.layout.operator(SLMorphTargetAnimation.bl_idname, text="SL Morph Target Animation from Nodes", icon="PLUGIN")


classes = (
    MorphTargetToSLWeights,
    SLMorphTargetAnimation,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.VIEW3D_MT_paint_weight.append(menu_func_weight)
    bpy.types.VIEW3D_MT_object.append(menu_func_object)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    bpy.types.VIEW3D_MT_paint_weight.remove(menu_func_weight)
    bpy.types.VIEW3D_MT_object.remove(menu_func_object)


if __name__ == "__main__":
    register()
