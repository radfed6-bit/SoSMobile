//
// Created by maks on 20.09.2025.
//

#include <jni.h>
#include <stdbool.h>
#include <dlfcn.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <limits.h>
#include <jvm_hooks/jvm_hooks.h>
#include "elf_hinter.h"
#include "load_stages.h"

#define TAG __FILE_NAME__
#include <log.h>

extern bool apiRequiresHints();

// Java 21 style hook
typedef jboolean (*NativeLibraries_load)(JNIEnv *env, jclass cls, jobject lib, jstring name, jboolean isBuiltin, jboolean throwExceptionIfFail);

// Java 17 style hook
typedef jboolean (*j17_NativeLibraries_load)(JNIEnv *env, jclass cls, jobject lib, jstring name, jboolean isBuiltin, jboolean isJNI, jboolean throwExceptionIfFail);

// Java 8 style hook
typedef void(*ClassLoader_00024NativeLibrary_load)(JNIEnv *env, jobject this, jstring name, jboolean isBuiltin);

union {
    NativeLibraries_load j21;
    j17_NativeLibraries_load j17;
    ClassLoader_00024NativeLibrary_load j8;
    void* generic;
} original_func;

static char native_lib_dir[PATH_MAX] = {0};

static void init_native_lib_dir() {
    if(native_lib_dir[0] != 0) return;
    Dl_info info;
    if(dladdr((void*)init_native_lib_dir, &info) && info.dli_fname != NULL) {
        char buf[PATH_MAX];
        strncpy(buf, info.dli_fname, sizeof(buf) - 1);
        buf[sizeof(buf) - 1] = 0;
        char* last_slash = strrchr(buf, '/');
        if(last_slash != NULL) {
            *last_slash = 0;
            strncpy(native_lib_dir, buf, sizeof(native_lib_dir) - 1);
            native_lib_dir[sizeof(native_lib_dir) - 1] = 0;
            LOGI("Detected native library directory via dladdr: %s", native_lib_dir);
            return;
        }
    }
    const char* ld = getenv("LD_LIBRARY_PATH");
    if(ld != NULL) {
        const char* colon = strchr(ld, ':');
        size_t len = colon ? (size_t)(colon - ld) : strlen(ld);
        if(len > 0 && len < sizeof(native_lib_dir)) {
            memcpy(native_lib_dir, ld, len);
            native_lib_dir[len] = 0;
            LOGI("Detected native library directory via LD_LIBRARY_PATH: %s", native_lib_dir);
        }
    }
}

static jstring resolve_native_library(JNIEnv *env, jstring name, char resolved_path[PATH_MAX]) {
    init_native_lib_dir();
    const char *name_n = (*env)->GetStringUTFChars(env, name, NULL);
    if(name_n == NULL) {
        resolved_path[0] = 0;
        return name;
    }

    const char* filename = strrchr(name_n, '/');
    if(filename == NULL) filename = name_n;
    else filename++;

    char soname[256];
    if(strncmp(filename, "lib", 3) != 0) {
        snprintf(soname, sizeof(soname), "lib%s.so", filename);
    } else {
        strncpy(soname, filename, sizeof(soname) - 1);
        soname[sizeof(soname) - 1] = 0;
    }

    bool redirected = false;
    if(native_lib_dir[0] != 0) {
        char candidate[PATH_MAX];
        snprintf(candidate, sizeof(candidate), "%s/%s", native_lib_dir, soname);
        if(access(candidate, R_OK) == 0) {
            if(strcmp(name_n, candidate) != 0) {
                LOGI("Redirecting native library load: %s -> %s", name_n, candidate);
                strncpy(resolved_path, candidate, PATH_MAX - 1);
                resolved_path[PATH_MAX - 1] = 0;
                redirected = true;
            }
        }
    }

    if(!redirected) {
        strncpy(resolved_path, name_n, PATH_MAX - 1);
        resolved_path[PATH_MAX - 1] = 0;
    }

    (*env)->ReleaseStringUTFChars(env, name, name_n);

    if(redirected) {
        return (*env)->NewStringUTF(env, resolved_path);
    }
    return name;
}

static void library_preload_hook(JNIEnv *env, const char* name) {
    const char* lib_filename = strrchr(name, '/');
    if(lib_filename == NULL) lib_filename = name;
    else lib_filename++;
    if(strcmp(lib_filename, "liblwjgl.so") == 0) {
        LOGI("Running LWJGL preload hooks...");
        installLwjglDlopenHook(env);
        installEMUIIteratorMititgation(env);
    }
}

#define NATIVES_HOOK(CALLTHROUGH, RESULT, RESULT_RETURN) \
do { \
    char resolved_path[PATH_MAX]; \
    jstring target_name = resolve_native_library(env, name, resolved_path); \
    library_preload_hook(env, resolved_path); \
    const bool hintsRequired = apiRequiresHints(); \
    hinter_t hinter; \
    if (hintsRequired) hinter_process(&hinter, resolved_path); \
    RESULT CALLTHROUGH; \
    if (hintsRequired) hinter_free(&hinter); \
    if (target_name != name) { \
        (*env)->DeleteLocalRef(env, target_name); \
    } \
    RESULT_RETURN \
} while(0);


static jboolean hook_NativeLibraries_load(JNIEnv *env, jclass cls, jobject lib, jstring name, jboolean isBuiltin, jboolean throwExceptionIfFail) {
    NATIVES_HOOK(original_func.j21(env, cls, lib, target_name, isBuiltin, throwExceptionIfFail), jboolean result =, return result;)
}

static jboolean hook_j17_NativeLibraries_load(JNIEnv *env, jclass cls, jobject lib, jstring name, jboolean isBuiltin, jboolean isJNI, jboolean throwExceptionIfFail) {
    NATIVES_HOOK(original_func.j17(env, cls, lib, target_name, isBuiltin, isJNI, throwExceptionIfFail), jboolean result =, return result;)
}

static void hook_ClassLoader_00024NativeLibrary_load(JNIEnv *env, jobject this, jstring name, jboolean isBuiltin) {
    NATIVES_HOOK(original_func.j8(env, this, target_name, isBuiltin),,)
}

static bool testMethod(JNIEnv *vm_env, jclass hookClass, const char* sign, JNINativeMethod* hookMethod) {
    jmethodID hookMethod_j17 = (*vm_env)->GetStaticMethodID(vm_env, hookClass, hookMethod->name, sign);
    if(hookMethod_j17 != NULL) {
        hookMethod->signature = sign;
        return true;
    }else {
        (*vm_env)->ExceptionClear(vm_env);
        return false;
    }
}

bool installClassLoaderHooks(JNIEnv *env, JNIEnv* vm_env) {
    void* libjava = dlopen("libjava.so", RTLD_NOLOAD);
    if(libjava == NULL) {
        throwException(env, STAGE_FIND_HOOKS_NATIVE, JNI_ERR, "Failed to find libjava.so after VM startup");
        return false;
    }
    jclass hookClass;
    JNINativeMethod hookMethod;
    hookClass = (*vm_env)->FindClass(vm_env,"java/lang/ClassLoader$NativeLibrary");
    if(hookClass != NULL) {
        hookMethod.name = "load";
        hookMethod.signature = "(Ljava/lang/String;Z)V";
        hookMethod.fnPtr = hook_ClassLoader_00024NativeLibrary_load;
        original_func.j8 = dlsym(libjava, "Java_java_lang_ClassLoader_00024NativeLibrary_load");
    }else {
        (*vm_env)->ExceptionClear(vm_env);
        hookClass = (*vm_env)->FindClass(vm_env, "jdk/internal/loader/NativeLibraries");
        if(hookClass == NULL) goto err;
        hookMethod.name = "load";
        original_func.generic = dlsym(libjava, "Java_jdk_internal_loader_NativeLibraries_load");
        if(testMethod(vm_env, hookClass, "(Ljdk/internal/loader/NativeLibraries$NativeLibraryImpl;Ljava/lang/String;ZZZ)Z", &hookMethod)) {
            hookMethod.fnPtr = hook_j17_NativeLibraries_load;
        }else if(testMethod(vm_env, hookClass, "(Ljdk/internal/loader/NativeLibraries$NativeLibraryImpl;Ljava/lang/String;ZZ)Z", &hookMethod)) {
            hookMethod.fnPtr = hook_NativeLibraries_load;
        }else {
            throwException(env, STAGE_FIND_HOOKS, JNI_ERR, "Cannot find hook target.");
        }
    }
    jint result = (*vm_env)->RegisterNatives(vm_env, hookClass, &hookMethod, 1);
    if(result != JNI_OK) {
        if((*vm_env)->ExceptionCheck(vm_env)) (*vm_env)->ExceptionDescribe(vm_env);
        throwException(env, STAGE_INSERT_HOOKS, result, "Cannot register hooks");
        return false;
    }
    return true;
    err:
    throwException(env, STAGE_FIND_HOOKS, JNI_ERR, "Cannot find hook target.");
    return false;
}