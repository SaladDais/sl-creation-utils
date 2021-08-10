# Example morph target animation creator
# Written against Hippolyzer @ v0.7.0
# `pip install hippolyzer` in a venv to run, or you can load it as a hippolyzer addon.
import argparse

from hippolyzer.lib.base.anim_utils import shift_keyframes, smooth_pos
from hippolyzer.lib.base.datatypes import Quaternion, Vector3
from hippolyzer.lib.base.llanim import Animation, Joint, RotKeyframe, PosKeyframe
from hippolyzer.lib.proxy.addons import AddonManager

# Each joint only moves in a specific direction along each axis
# This is just by convention, these could be reordered as needed.
JOINT_DIR_MAPPING = {
    "mHipLeft": Vector3(1, 0, 0),
    "mHipRight": Vector3(-1, 0, 0),
    "mHindLimb1Left": Vector3(0, 1, 0),
    "mHindLimb1Right": Vector3(0, -1, 0),
    "mTail1": Vector3(0, 0, 1),
    "mGroin": Vector3(0, 0, -1),
}

# When a joint is moved to 5.0 along its defined direction, the
# morph is 100% complete for all translations in that direction.
MAX_MAGNITUDE = 5.0


def build_morph_anim(axis_slop: int = 0) -> Animation:
    anim = Animation(
        base_priority=5,
        duration=5.0,
        loop_out_point=5.0,
        loop=True,
    )
    no_rot_keyframes = [RotKeyframe(0, Quaternion())]
    # Keep the null joint fixed at 0 pos, 0 rot
    null_joint = Joint(
        priority=5,
        pos_keyframes=[
            PosKeyframe(0, Vector3(0, 0, 0)),
        ],
        rot_keyframes=no_rot_keyframes,
    )

    # Doesn't necessarily need to stick to the origin since all the joints stem from this
    # and will move along with it, but keep things simple.
    anim.joints["mPelvis"] = null_joint
    # The hind limbs we use stem from this joint so make sure it's stuck to the origin
    anim.joints["mHindLimbsRoot"] = null_joint

    joint_num = 0
    for joint_name, coord_vec in JOINT_DIR_MAPPING.items():
        # Keep both sides of each axis in sync, but allow animation for an axis
        # to lag behind others to give the morph some slop. Unlike typical morph
        # target animations we can control morphing along individual axes independently.
        keyframe_offset = (joint_num // 2) * axis_slop
        # 100% morphed position for this joint
        end_pos = coord_vec * MAX_MAGNITUDE
        anim.joints[joint_name] = Joint(
            priority=5,
            pos_keyframes=shift_keyframes([
                # Slow start and stop for the morph
                *smooth_pos(Vector3(), end_pos, inter_frames=10, time=0.0, duration=2.5),
                # Animate back to the morph basis state
                *smooth_pos(end_pos, Vector3(), inter_frames=10, time=2.5, duration=2.5),
            ], keyframe_offset),
            rot_keyframes=no_rot_keyframes,
        )
        joint_num += 1
    return anim


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--axis_slop', type=int, help='delay in keyframes per axis', default=0)
    parser.add_argument('output_file')
    args = parser.parse_args()

    anim = build_morph_anim(args.axis_slop)
    with open(args.output_file, "wb") as f:
        f.write(anim.to_bytes())


if __name__ == "__main__":
    # Being used as a script
    main()
elif AddonManager.SESSION_MANAGER:
    # Being imported as an addon for Hippolyzer

    import local_anim  # noqa
    AddonManager.hot_reload(local_anim, require_addons_loaded=True)

    class MorphTargetAnimator(local_anim.BaseAnimHelperAddon):
        ANIM_NAME = "morph_anim"

        def build_anim(self) -> Animation:
            return build_morph_anim()


    addons = [MorphTargetAnimator()]
