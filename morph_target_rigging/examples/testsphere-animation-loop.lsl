// Does a looping morph through the states of testsphere-animation-for-edit.dae

integer NUM_OF_FACES = 4;

string MORPH_UP_ANIM = "morph_smooth_toward_100";
string MORPH_DOWN_ANIM = "morph_smooth_toward_0";
// determined by the animations we play
float MORPH_TIME = 2.5;

integer gFaceNum = 0;

startCurrentMorph() {
    // Hide all faces but the current one
    llSetLinkPrimitiveParamsFast(LINK_THIS, [
        PRIM_COLOR, ALL_SIDES, <0,0,0>, 0.0,
        PRIM_COLOR, gFaceNum, <1,1,1>, 1.0
    ]);

    if (gFaceNum % 2) {
        llStartObjectAnimation(MORPH_DOWN_ANIM);
        llStopObjectAnimation(MORPH_UP_ANIM);
    } else {
        llStartObjectAnimation(MORPH_UP_ANIM);
        llStopObjectAnimation(MORPH_DOWN_ANIM);
    }
}

stopAllAnims() {
    list names = llGetObjectAnimationNames();
    integer i = llGetListLength(names);
    while(i-- > 0) {
        llStopObjectAnimation(llList2String(names, i));
    }
}

default {
    state_entry() {
        stopAllAnims();
        startCurrentMorph();
        llSetTimerEvent(MORPH_TIME);
    }

    timer() {
        gFaceNum = (gFaceNum + 1) % NUM_OF_FACES;
        startCurrentMorph();
    }
}
