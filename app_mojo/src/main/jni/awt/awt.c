//
// Created by whbex on 20.08.2026.
//

#include <stdbool.h>
#include <pthread.h>
#include "awt.h"

jclass class_AWTBridge;

float inputXRatio = 0;
float inputYRatio = 0;

JavaVM* androidVM;
JavaVM* runtimeVM;

pthread_mutex_t vm_wait_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t vm_wait_cond = PTHREAD_COND_INITIALIZER;

_Atomic bool isVmConnected = false;

// This is used across all PojavExec AWT library
JNIEnv* JNIEnv_InputRuntime;

jint JNI_OnLoad(JavaVM* vm, void* reserved) {
    if (androidVM == NULL) {
        //Save dalvik global JavaVM pointer
        androidVM = vm;
        JNIEnv *env = NULL;
        (*vm)->GetEnv(vm, (void**)&env, JNI_VERSION_1_4);

        class_AWTBridge = (*env)->NewGlobalRef(env, (*env)->FindClass(env, "git/artdeell/mojo/awt/AWTBridge"));

        register_methods_util(env);
        register_methods_clipboard(env);
    } else if (runtimeVM != vm) {
        runtimeVM = vm;
        pthread_mutex_lock(&vm_wait_mutex);
        isVmConnected = true;
        pthread_cond_broadcast(&vm_wait_cond);
        pthread_mutex_unlock(&vm_wait_mutex);
    }

    return JNI_VERSION_1_4;
}


