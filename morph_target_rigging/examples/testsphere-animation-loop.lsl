// Does a looping morph through the states of testsphere-animation-for-edit.dae

integer NUM_OF_FACES = 4;
string MORPH_ANIM = "morph_no_offset";
// determined by the animation we play
float MORPH_TIME = 2.5;

integer gFaceNum = 0;

syncAnimation() {
    // Restart the anim to make sure it's synced with face flipping
    // TODO: would be better to always explicitly use two different animations
    // to morph to and from rather than a single, looping morphing anim.
    // Using a looping anim causes the anim to look choppy if our timer doesn't
    // trigger exactly when we ask it to.
    llStopObjectAnimation(MORPH_ANIM);
    llSleep(0.05);
    llStartObjectAnimation(MORPH_ANIM);
}

applyCurrentFace() {
    // Hide all faces but the current one
    llSetLinkPrimitiveParamsFast(LINK_THIS, [
        PRIM_COLOR, ALL_SIDES, <0,0,0>, 0.0,
        PRIM_COLOR, gFaceNum, <1,1,1>, 1.0
    ]);
}

default {
    state_entry() {
        syncAnimation();
        applyCurrentFace();
        llSetTimerEvent();
    }

    timer() {
        gFaceNum = (gFaceNum + 1) % NUM_OF_FACES;
        applyCurrentFace();
        if (!gFaceNum) {
            // on the first frame, resync anim
            syncAnimation();
        }
    }
}
