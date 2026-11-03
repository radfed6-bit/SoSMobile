//
// Created by maks on 06.01.2025.
//

#include "jvm_hooks.h"

#include <android/api-level.h>

#include <dlfcn.h>
#include <string.h>
#include <stdlib.h>

#define TAG __FILE_NAME__
#include <log.h>

#include <mojoexec.h>

/**
 * Implementation of ndlopen(), ndlerror(), ndlsym(), and ndlclose()
 * for LWJGL 3 DynamicLinkLoader compatibility on Android ARM64.
 */
static jlong ndlopen_bugfix(__attribute__((unused)) JNIEnv *env,
                     __attribute__((unused)) jclass class,
                     jlong filename_ptr,
                     jint jmode) {
    const char* filename = (const char*) filename_ptr;
    if(filename == NULL) return 0;

    // Override vulkan loading to let us load vulkan ourselves
    if(strstr(filename, "libvulkan.so") != NULL) {
        printf("LWJGL linkerhook: replacing load for libvulkan.so with custom driver\n");
        return (jlong) mojoexec_acq_vulkan_handle();
    }
    // Load renderer using egl_acquire
    if(strstr(filename, "libGLMojo.so") != NULL) {
        printf("LWJGL linkerhook: replacing OpenGL with renderspec driver\n");
        return (jlong) mojoexec_acq_egl_handle();
    }

    int mode = (int)jmode;
    void* handle = dlopen(filename, mode);
    if(handle == NULL && strstr(filename, "libglfw.so") != NULL) {
        printf("LWJGL linkerhook: fallback loading native libglfw.so\n");
        handle = dlopen("libglfw.so", mode);
    }
    return (jlong) handle;
}

static jlong ndlerror_hook(__attribute__((unused)) JNIEnv *env,
                           __attribute__((unused)) jclass class) {
    const char* err = dlerror();
    return (jlong) err;
}

static jlong ndlsym_hook(__attribute__((unused)) JNIEnv *env,
                         __attribute__((unused)) jclass class,
                         jlong handle,
                         jlong name_ptr) {
    if(name_ptr == 0 || handle == 0) return 0;
    const char *name = (const char *) name_ptr;
    return (jlong) dlsym((void *) handle, name);
}

static jint ndlclose_hook(__attribute__((unused)) JNIEnv *env,
                          __attribute__((unused)) jclass class,
                          jlong handle) {
    if(handle == 0) return 0;
    return (jint) dlclose((void *) handle);
}

JNIEXPORT jlong JNICALL Java_org_lwjgl_system_linux_DynamicLinkLoader_ndlopen(JNIEnv *env, jclass clazz, jlong filename_ptr, jint mode) {
    return ndlopen_bugfix(env, clazz, filename_ptr, mode);
}

JNIEXPORT jlong JNICALL Java_org_lwjgl_system_linux_DynamicLinkLoader_ndlerror(JNIEnv *env, jclass clazz) {
    return ndlerror_hook(env, clazz);
}

JNIEXPORT jlong JNICALL Java_org_lwjgl_system_linux_DynamicLinkLoader_ndlsym(JNIEnv *env, jclass clazz, jlong handle, jlong name_ptr) {
    return ndlsym_hook(env, clazz, handle, name_ptr);
}

JNIEXPORT jint JNICALL Java_org_lwjgl_system_linux_DynamicLinkLoader_ndlclose(JNIEnv *env, jclass clazz, jlong handle) {
    return ndlclose_hook(env, clazz, handle);
}

/**
 * Install the LWJGL dlopen/dlerror/dlsym/dlclose hooks.
 * This guarantees complete JNI symbol resolution across all LWJGL 3.3.x/3.4.x versions.
 */
void installLwjglDlopenHook(JNIEnv *env) {
    LOGI("Installing LWJGL dlopen() hook and DynamicLinkLoader bridges");
    jclass dynamicLinkLoader = (*env)->FindClass(env, "org/lwjgl/system/linux/DynamicLinkLoader");
    if(dynamicLinkLoader == NULL) {
        LOGE("Failed to find the target class org/lwjgl/system/linux/DynamicLinkLoader");
        (*env)->ExceptionClear(env);
        return;
    }
    JNINativeMethod ndlMethods[] = {
            {"ndlopen", "(JI)J", (void *) &ndlopen_bugfix},
            {"ndlerror", "()J", (void *) &ndlerror_hook},
            {"ndlsym", "(JJ)J", (void *) &ndlsym_hook},
            {"ndlclose", "(J)I", (void *) &ndlclose_hook}
    };
    if((*env)->RegisterNatives(env, dynamicLinkLoader, ndlMethods, 4) != 0) {
        LOGE("Failed to register the hooked DynamicLinkLoader methods");
        (*env)->ExceptionClear(env);
    } else {
        LOGI("Successfully registered all 4 DynamicLinkLoader native methods");
    }
}