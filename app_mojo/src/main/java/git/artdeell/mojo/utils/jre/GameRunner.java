package git.artdeell.mojo.utils.jre;

import android.content.Context;
import android.os.Environment;
import android.util.Log;
import android.widget.Toast;

import git.artdeell.mojo.tasks.AsyncAssetManager;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import git.artdeell.mojo.Architecture;
import git.artdeell.mojo.Logger;
import git.artdeell.mojo.Tools;
import git.artdeell.mojo.instances.Instance;
import git.artdeell.mojo.utils.lifecycle.LifecycleAwareAlertDialog;
import git.artdeell.mojo.multirt.MultiRTUtils;
import git.artdeell.mojo.multirt.Runtime;
import git.artdeell.mojo.prefs.LauncherPreferences;
import git.artdeell.mojo.game.renderer.GameRenderer;
import git.artdeell.mojo.game.renderer.RenderSpec;
import git.artdeell.mojo.utils.FileUtils;
import git.artdeell.mojo.utils.JREUtils;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import git.artdeell.mojo.R;

public class GameRunner {

    private static boolean showDialog(AppCompatActivity activity, int message) throws InterruptedException {
        LifecycleAwareAlertDialog.DialogCreator dialogCreator = ((alertDialog, dialogBuilder) ->
                dialogBuilder.setMessage(activity.getString(message))
                        .setCancelable(false)
                        .setPositiveButton(android.R.string.ok, (d, w)->{}));
        return LifecycleAwareAlertDialog.haltOnDialog(activity.getLifecycle(), activity, dialogCreator);
    }

    public static void launchGame(final AppCompatActivity activity,
                                  Instance instance, String versionId, File[] classpath, GameRenderer gameRenderer) throws Throwable {
        int freeDeviceMemory = Tools.getFreeDeviceMemory(activity);
        int localeString;
        int freeAddressSpace = Architecture.is32BitsDevice() ? Tools.getMaxContinuousAddressSpaceSize() : -1;
        Log.i("MemStat", "Free RAM: " + freeDeviceMemory + " Addressable: " + freeAddressSpace);
        boolean showAddressMemoryWarning = freeDeviceMemory > freeAddressSpace && freeAddressSpace != -1;
        if(showAddressMemoryWarning) {
            freeDeviceMemory = freeAddressSpace;
            localeString = R.string.address_memory_warning_msg;
        } else {
            localeString = R.string.memory_warning_msg;
        }

        if(LauncherPreferences.PREF_RAM_ALLOCATION > freeDeviceMemory && (showAddressMemoryWarning || LauncherPreferences.PREF_SHOW_MEMORY_WARNING_DIALOG)) {
            int finalDeviceMemory = freeDeviceMemory;
            LifecycleAwareAlertDialog.DialogCreator dialogCreator = (dialog, builder) -> {
                builder.setMessage(activity.getString(localeString, finalDeviceMemory, LauncherPreferences.PREF_RAM_ALLOCATION))
                        .setPositiveButton(android.R.string.ok, (d, w) -> {
                        });

                if (!showAddressMemoryWarning) {
                    builder.setNegativeButton(R.string.option_do_not_show_again, (d, w) -> {
                        LauncherPreferences.DEFAULT_PREF.edit().putBoolean("showMemoryWarning", false).apply();
                        Toast.makeText(activity, R.string.notification_permission_toast, Toast.LENGTH_SHORT).show();
                    });
                }
            };

            if (LifecycleAwareAlertDialog.haltOnDialog(activity.getLifecycle(), activity, dialogCreator)) {
                return;
            }
        }

        int ramMb = LauncherPreferences.PREF_RAM_ALLOCATION;
        if (ramMb < git.artdeell.mojo.launch.SyxLaunchConfig.MIN_RAM_MB) ramMb = git.artdeell.mojo.launch.SyxLaunchConfig.DEFAULT_RAM_MB;
        if (ramMb > git.artdeell.mojo.launch.SyxLaunchConfig.MAX_REASONABLE_RAM_MB) ramMb = git.artdeell.mojo.launch.SyxLaunchConfig.MAX_REASONABLE_RAM_MB;

        String gameDir = LauncherPreferences.getGameDirectory();
        if (gameDir == null && instance != null) {
            gameDir = instance.getGameDirectory().getAbsolutePath();
        }
        if (gameDir == null) {
            gameDir = new File(Environment.getExternalStorageDirectory(), "SoSMobile").getAbsolutePath();
        }

        AsyncAssetManager.extractDefaultSettings(activity);

        List<String> customArgs = new ArrayList<>();
        if (LauncherPreferences.PREF_CUSTOM_JAVA_ARGS != null && !LauncherPreferences.PREF_CUSTOM_JAVA_ARGS.trim().isEmpty()) {
            customArgs.addAll(JREUtils.parseJavaArguments(LauncherPreferences.PREF_CUSTOM_JAVA_ARGS));
        }
        if (instance != null && Tools.isValidString(instance.jvmArgs)) {
            customArgs.addAll(JREUtils.parseJavaArguments(instance.getLaunchArgs()));
        }

        git.artdeell.mojo.launch.SyxLaunchConfig syxConfig = git.artdeell.mojo.launch.SyxLaunchConfig.buildLaunchConfig(
                gameDir,
                Tools.DIR_GAME_HOME,
                Tools.NATIVE_LIB_DIR,
                Tools.DIR_CACHE.getAbsolutePath(),
                ramMb,
                null,
                customArgs
        );

        int requiredJavaVersion = 17;
        Runtime runtime = MultiRTUtils.forceReread(pickRuntime(instance, requiredJavaVersion));

        ArrayList<String> launchClassPath = new ArrayList<>();
        if (classpath != null && classpath.length > 0) {
            for (File classpathEntry : classpath) {
                if (classpathEntry != null) {
                    launchClassPath.add(classpathEntry.getAbsolutePath());
                }
            }
        } else {
            launchClassPath.addAll(syxConfig.getClasspath());
        }

        List<String> javaArgList = new ArrayList<>(syxConfig.getJavaArgs());

        File versionSpecificNativesDir = new File(Tools.DIR_CACHE, "natives/" + versionId);
        if(versionSpecificNativesDir.exists()) {
            String dirPath = versionSpecificNativesDir.getAbsolutePath();
            javaArgList.add("-Djava.library.path=" + dirPath + ":" + Tools.NATIVE_LIB_DIR);
            javaArgList.add("-Djna.boot.library.path=" + dirPath);
            javaArgList.add("-Dorg.lwjgl.librarypath=" + dirPath + ":" + Tools.NATIVE_LIB_DIR);
        } else {
            javaArgList.add("-Djava.library.path=" + Tools.NATIVE_LIB_DIR);
            javaArgList.add("-Djna.boot.library.path=" + Tools.NATIVE_LIB_DIR);
            javaArgList.add("-Dorg.lwjgl.librarypath=" + Tools.NATIVE_LIB_DIR);
        }

        File lwjglExtractDir = new File(Tools.DIR_CACHE, "lwjgl_native/" + versionId);
        if (lwjglExtractDir.exists()) {
            File[] oldFiles = lwjglExtractDir.listFiles();
            if (oldFiles != null) {
                for (File f : oldFiles) {
                    try {
                        f.delete();
                    } catch (Exception ignored) {}
                }
            }
        }
        FileUtils.ensureDirectory(lwjglExtractDir);

        File nativeDir = new File(Tools.NATIVE_LIB_DIR);
        if (nativeDir.exists() && nativeDir.isDirectory()) {
            File[] nativeLibs = nativeDir.listFiles((dir, name) -> name.startsWith("liblwjgl"));
            if (nativeLibs != null) {
                for (File lib : nativeLibs) {
                    File target = new File(lwjglExtractDir, lib.getName());
                    try {
                        FileUtils.copyFile(lib, target);
                    } catch (Exception ignored) {}
                }
            }
        }

        javaArgList.add("-Dorg.lwjgl.system.SharedLibraryExtractPath=" + lwjglExtractDir.getAbsolutePath());
        javaArgList.add("-Dorg.lwjgl.glfw.libname=libglfw.so");
        javaArgList.add("-Dorg.lwjgl.stb.libname=" + Tools.NATIVE_LIB_DIR + "/liblwjgl_stb.so");
        javaArgList.add("-Dorg.lwjgl.tinyfd.libname=" + Tools.NATIVE_LIB_DIR + "/liblwjgl_tinyfd.so");
        javaArgList.add("-Dorg.lwjgl.nuklear.libname=" + Tools.NATIVE_LIB_DIR + "/liblwjgl_nuklear.so");
        javaArgList.add("-Dorg.lwjgl.freetype.libname=" + Tools.NATIVE_LIB_DIR + "/libfreetype.so");
        javaArgList.add("-Djava.awt.headless=true");
        javaArgList.add("-Dorg.lwjgl.util.NoHashChecks=true");

        gameRenderer.setupEnvironment(activity);
        JREUtils.chdir(syxConfig.getWorkingDir());

        if(!gameRenderer.maybeSetupRenderer()) {
            if(showDialog(activity, R.string.gr_err_renderer_load_Failed)) return;
            System.exit(0);
        }

        int finalRam = ramMb;
        activity.runOnUiThread(() -> Toast.makeText(activity, activity.getString(R.string.autoram_info_msg, finalRam), Toast.LENGTH_SHORT).show());

        List<String> launchArgs = new ArrayList<>(syxConfig.getAppArgs());
        String mainClass = git.artdeell.mojo.launch.SyxLaunchConfig.CANONICAL_MAIN_CLASS;

        try {
            JavaRunner.nativeSetupExit(activity);
            JavaRunner.startJvm(runtime, javaArgList, launchClassPath, mainClass, launchArgs);
        } catch (VMLoadException e) {
            LifecycleAwareAlertDialog.DialogCreator dialogCreator = (dialog, builder) ->
                builder.setMessage(e.toString(activity)).setPositiveButton(android.R.string.ok, (d, w)->{});

            if(LifecycleAwareAlertDialog.haltOnDialog(activity.getLifecycle(), activity, dialogCreator)) {
                return;
            }
        }

        Tools.restartLauncherActivity(activity);
        Tools.fullyExit();
    }

    public static @NonNull String pickRuntime(Instance instance, int targetJavaVersion) {
        String runtime = Tools.getSelectedRuntime(instance);
        String profileRuntime = instance != null ? instance.selectedRuntime : null;
        Runtime pickedRuntime = runtime != null ? MultiRTUtils.read(runtime) : null;
        if(runtime == null || pickedRuntime == null || pickedRuntime.javaVersion == 0 || pickedRuntime.javaVersion < targetJavaVersion) {
            Runtime internalRuntime = MultiRTUtils.read("Internal");
            String preferredRuntime = (internalRuntime != null && internalRuntime.javaVersion >= targetJavaVersion)
                    ? "Internal"
                    : MultiRTUtils.getNearestJreName(targetJavaVersion);
            if(preferredRuntime == null) throw new RuntimeException("Songs of Syx requires Java 17 or Java 21 runtime.");
            if(profileRuntime != null && instance != null) {
                instance.selectedRuntime = preferredRuntime;
                instance.maybeWrite();
            }
            runtime = preferredRuntime;
        }
        return runtime;
    }
}
