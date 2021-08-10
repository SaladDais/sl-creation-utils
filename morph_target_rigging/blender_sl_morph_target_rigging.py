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


import bpy
import bpy.utils.previews
from bpy.types import Operator, Panel, WindowManager
from mathutils import Vector, Color
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


def vec_max_component(coord: Vector) -> float:
    return sum([abs(x) for x in coord])


def vector_to_weights(coord: Vector) -> List[float]:
    # Assumes all components are -1.0 to 1.0
    weights = [0.0] * len(VERTEX_GROUP_NAMES)
    x_idx = 0
    y_idx = 2
    z_idx = 4
    if coord[0] < 0.0:
        x_idx = 1
    if coord[1] < 0.0:
        y_idx = 3
    if coord[2] < 0.0:
        z_idx = 5
    # Calculate weight based on magnitude of each axis
    weights[x_idx] = abs(coord[0]) / MAX_MOVEMENT
    weights[y_idx] = abs(coord[1]) / MAX_MOVEMENT
    weights[z_idx] = abs(coord[2]) / MAX_MOVEMENT
    # Unused available motion magnitude goes to the "null" joint
    weights[-1] = 1.0 - sum(weights)
    return weights


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
             isinstance(bpy.context.active_object, bpy.types.Object) and
             isinstance(bpy.context.active_object.data, bpy.types.Mesh))
        return p

    def execute(self, context):
        # to restore object selections
        orig_active_object = context.active_object
        orig_selected_objects = context.selected_objects

        if len(orig_selected_objects) != 2:
            self.report({'ERROR'}, f"Must have two objects selected")
            return {'CANCELLED'}

        # Same number of verts in each?
        if len(set(len(x.data.vertices) for x in orig_selected_objects)) != 1:
            self.report({'ERROR'}, f"Vertex count mismatch between objects")
            return {'CANCELLED'}

        if not all(x.type == 'MESH' for x in orig_selected_objects):
            self.report({'ERROR'}, f"All objects must be mesh")
            return {'CANCELLED'}

        for orig_obj in orig_selected_objects:
            orig_obj.select_set(False)

        obj = orig_active_object
        other_obj = [x for x in orig_selected_objects if x != orig_active_object][0]

        bpy.ops.object.mode_set(mode='OBJECT')

        # Set to active for bpy.ops.object.vertex_group_add()
        bpy.context.view_layer.objects.active = obj
        last_active_vgroup = obj.vertex_groups.active

        # Get or create the vertex groups we need for morph target animation
        vertex_groups = []
        for vertex_group_name in VERTEX_GROUP_NAMES:
            found_group = None
            for vgroup in obj.vertex_groups:
                if vgroup.name == vertex_group_name:
                    found_group = vgroup
                    break
            if found_group is None:
                bpy.ops.object.vertex_group_add()
                found_group = obj.vertex_groups.active
                found_group.name = vertex_group_name
            vertex_groups.append(found_group)

        # Set the active vertex group back to what it was
        if last_active_vgroup:
            obj.vertex_groups.active = last_active_vgroup

        # Walk the list of vertices and position deltas to weights for a given
        # vert in mesh-local space
        for loop in obj.data.loops:
            vi = loop.vertex_index
            # co means position, does not take into account modifiers or object transforms
            # so you must apply both manually first!
            diff = other_obj.data.vertices[vi].co - obj.data.vertices[vi].co
            comp_max = vec_max_component(diff)
            if comp_max > MAX_MOVEMENT:
                self.report({'ERROR'}, f"Position difference too great! {diff}")
                return {'CANCELLED'}

            # Calculate weights for position delta and assign to the vertex groups.
            for vertex_group, group_weight in zip(vertex_groups, vector_to_weights(diff)):
                vertex_group.add([vi], group_weight, 'REPLACE')

        # Force an update
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

        bpy.context.view_layer.update()

        obj.select_set(False)

        # restore object selections
        for orig_obj in orig_selected_objects:
            orig_obj.select_set(True)
        bpy.context.view_layer.objects.active = orig_active_object

        return {'FINISHED'}


########################################################################
# MAIN & REGISTER
########################################################################


def menu_func_weight(self, _context):
    self.layout.operator(MorphTargetToSLWeights.bl_idname, text="Morph Target To SL Weights", icon='PLUGIN')


classes = (
    MorphTargetToSLWeights,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.VIEW3D_MT_paint_weight.append(menu_func_weight)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    bpy.types.VIEW3D_MT_paint_weight.remove(menu_func_weight)


if __name__ == "__main__":
    register()
