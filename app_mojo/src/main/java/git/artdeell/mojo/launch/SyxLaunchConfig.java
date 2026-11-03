package git.artdeell.mojo.launch;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.Serializable;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import git.artdeell.mojo.mods.SyxModSettings;

/**
 * Authoritative Launch Environment Configuration & Classpath Assembly for Songs of Syx on ARM64 Android.
 * Strictly aligns with LaunchConfigBuilderOracle in tests/e2e/harness/oracles.py.
 */
public class SyxLaunchConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    public static final String CANONICAL_MAIN_CLASS = "init.MainProcess";
    public static final int MIN_RAM_MB = 512;
    public static final int DEFAULT_RAM_MB = 2048;
    public static final int MAX_REASONABLE_RAM_MB = 16384;

    private final String mainClass;
    private final String vmPath;
    private final List<String> javaArgs;
    private final List<String> appArgs;
    private final List<String> classpath;
    private final String workingDir;
    private final Map<String, String> systemProperties;

    public SyxLaunchConfig(
            String mainClass,
            String vmPath,
            List<String> javaArgs,
            List<String> appArgs,
            List<String> classpath,
            String workingDir,
            Map<String, String> systemProperties) {
        this.mainClass = mainClass;
        this.vmPath = vmPath;
        this.javaArgs = Collections.unmodifiableList(new ArrayList<>(javaArgs));
        this.appArgs = Collections.unmodifiableList(new ArrayList<>(appArgs));
        this.classpath = Collections.unmodifiableList(new ArrayList<>(classpath));
        this.workingDir = workingDir;
        this.systemProperties = Collections.unmodifiableMap(new LinkedHashMap<>(systemProperties));
    }

    public String getMainClass() {
        return mainClass;
    }

    public String getVmPath() {
        return vmPath;
    }

    public List<String> getJavaArgs() {
        return javaArgs;
    }

    public List<String> getAppArgs() {
        return appArgs;
    }

    public List<String> getClasspath() {
        return classpath;
    }

    public String getWorkingDir() {
        return workingDir;
    }

    public Map<String, String> getSystemProperties() {
        return systemProperties;
    }

    /**
     * Builds a complete SyxLaunchConfig from parameters.
     */
    public static SyxLaunchConfig buildLaunchConfig(
            String gameDir,
            String userHomeDir,
            String appNativeDir,
            String cacheDir,
            int ramMb,
            List<String> activeMods,
            List<String> customJvmArgs) {

        if (ramMb < MIN_RAM_MB) {
            throw new IllegalArgumentException("RAM must be at least " + MIN_RAM_MB + "MB, got " + ramMb + "MB");
        }
        if (ramMb > MAX_REASONABLE_RAM_MB) {
            throw new IllegalArgumentException("RAM exceeds reasonable limit (" + MAX_REASONABLE_RAM_MB + "MB): " + ramMb + "MB");
        }

        File gameDirFile = new File(gameDir);
        try {
            gameDirFile = gameDirFile.getCanonicalFile();
        } catch (IOException e) {
            gameDirFile = gameDirFile.getAbsoluteFile();
        }

        File userHomeDirFile = new File(userHomeDir);
        try {
            userHomeDirFile = userHomeDirFile.getCanonicalFile();
        } catch (IOException e) {
            userHomeDirFile = userHomeDirFile.getAbsoluteFile();
        }

        String resolvedGameDir = gameDirFile.getAbsolutePath();
        String resolvedHomeDir = userHomeDirFile.getAbsolutePath();

        if (appNativeDir == null || appNativeDir.isEmpty()) {
            appNativeDir = "/data/data/git.artdeell.mojo/lib";
        }
        if (cacheDir == null || cacheDir.isEmpty()) {
            cacheDir = "/data/data/git.artdeell.mojo/cache";
        }

        // Ensure default settings file exists in resolvedHomeDir to prevent DataError at startup
        File settingsFile = SyxModSettings.getSettingsFile(new File(resolvedHomeDir));
        if (!settingsFile.exists() || settingsFile.length() == 0) {
            SyxModSettings.saveActiveMods(new File(resolvedHomeDir), Collections.emptyList());
        }

        // If activeMods was not explicitly supplied, try reading from LauncherSettings.txt
        if (activeMods == null) {
            activeMods = loadActiveMods(resolvedHomeDir);
        }

        // 1. Classpath Assembly
        List<String> classpath = assembleClasspath(resolvedGameDir, resolvedHomeDir, activeMods, cacheDir);

        // 2. System Properties
        Map<String, String> sysProps = new LinkedHashMap<>();
        sysProps.put("os.name", "Linux");
        sysProps.put("file.encoding", "UTF-8");
        sysProps.put("user.dir", resolvedGameDir);
        sysProps.put("user.home", resolvedHomeDir);
        sysProps.put("java.io.tmpdir", cacheDir);
        sysProps.put("org.lwjgl.system.SharedLibraryExtractPath", cacheDir + "/lwjgl_native");
        sysProps.put("org.lwjgl.system.allocator", "system");
        sysProps.put("org.lwjgl.opengl.libname", "libGLMojo.so");
        sysProps.put("org.lwjgl.glfw.libname", "libglfw.so");
        sysProps.put("org.lwjgl.stb.libname", appNativeDir + "/liblwjgl_stb.so");
        sysProps.put("org.lwjgl.tinyfd.libname", appNativeDir + "/liblwjgl_tinyfd.so");
        sysProps.put("org.lwjgl.nuklear.libname", appNativeDir + "/liblwjgl_nuklear.so");
        sysProps.put("org.lwjgl.librarypath", appNativeDir);
        sysProps.put("java.library.path", appNativeDir);
        sysProps.put("jna.boot.library.path", appNativeDir);
        sysProps.put("java.awt.headless", "true");
        sysProps.put("org.lwjgl.util.NoHashChecks", "true");
        sysProps.put("cacio.managed.screensize", "1920x1080");
        sysProps.put("awt.toolkit", "com.github.caciocavallosilano.cacio.ctc.CTCToolkit");
        sysProps.put("java.awt.graphicsenv", "com.github.caciocavallosilano.cacio.ctc.CTCGraphicsEnvironment");

        // 3. JVM Arguments
        List<String> javaArgs = new ArrayList<>();
        javaArgs.add("-Xms" + MIN_RAM_MB + "m");
        javaArgs.add("-Xmx" + ramMb + "m");
        javaArgs.add("-XX:+UseCompressedOops");
        javaArgs.add("-server");
        javaArgs.add("-Dfml.earlyprogresswindow=false");
        javaArgs.add("-XX:+UseSerialGC");
        javaArgs.add("-Dfile.encoding=UTF-8");
        javaArgs.add("-Dos.name=Linux");
        javaArgs.add("-Duser.dir=" + resolvedGameDir);
        javaArgs.add("-Duser.home=" + resolvedHomeDir);
        javaArgs.add("-Djava.awt.headless=true");
        javaArgs.add("-Djava.library.path=" + appNativeDir);
        javaArgs.add("-Dorg.lwjgl.librarypath=" + appNativeDir);
        javaArgs.add("-Dorg.lwjgl.glfw.libname=libglfw.so");
        javaArgs.add("-Dorg.lwjgl.opengl.libname=libGLMojo.so");
        javaArgs.add("-Dorg.lwjgl.stb.libname=" + appNativeDir + "/liblwjgl_stb.so");
        javaArgs.add("-Dorg.lwjgl.tinyfd.libname=" + appNativeDir + "/liblwjgl_tinyfd.so");
        javaArgs.add("-Dorg.lwjgl.nuklear.libname=" + appNativeDir + "/liblwjgl_nuklear.so");
        javaArgs.add("-Dorg.lwjgl.system.SharedLibraryExtractPath=" + cacheDir + "/lwjgl_native");
        javaArgs.add("-Dorg.lwjgl.util.NoHashChecks=true");
        javaArgs.add("-cp");
        javaArgs.add(String.join(File.pathSeparator, classpath));

        if (customJvmArgs != null && !customJvmArgs.isEmpty()) {
            javaArgs.addAll(customJvmArgs);
        }

        String vmPath = appNativeDir + "/libmojort.so";

        return new SyxLaunchConfig(
                CANONICAL_MAIN_CLASS,
                vmPath,
                javaArgs,
                Collections.emptyList(),
                classpath,
                resolvedGameDir,
                sysProps
        );
    }

    /**
     * Assembles the classpath in deterministic priority order:
     * 1. <game_dir>/SongsOfSyx.jar
     * 2. <game_dir>/base/script/*.jar (sorted)
     * 3. Active Mod Script JARs (in user-defined order)
     * 4. Headless AWT Helper JARs (if present)
     */
    public static List<String> assembleClasspath(
            String resolvedGameDir,
            String resolvedHomeDir,
            List<String> activeMods,
            String cacheDir) {

        List<String> cp = new ArrayList<>();

        // 1. Primary Game JAR
        File mainJar = new File(resolvedGameDir, "SongsOfSyx.jar");
        cp.add(mainJar.getAbsolutePath());

        // 2. Built-in base scenario scripts (base/script/*.jar)
        File baseScriptDir = new File(resolvedGameDir, "base/script");
        if (baseScriptDir.exists() && baseScriptDir.isDirectory()) {
            File[] scripts = baseScriptDir.listFiles((dir, name) -> name.toLowerCase().endsWith(".jar"));
            if (scripts != null) {
                Arrays.sort(scripts, Comparator.comparing(File::getName, String.CASE_INSENSITIVE_ORDER));
                for (File script : scripts) {
                    try {
                        cp.add(script.getCanonicalPath());
                    } catch (IOException e) {
                        cp.add(script.getAbsolutePath());
                    }
                }
            }
        }

        // 3. Mod Script JARs
        if (activeMods != null && !activeMods.isEmpty()) {
            File userModsRoot = new File(resolvedHomeDir, ".local/share/songsofsyx/mods");
            File gameModsRoot = new File(resolvedGameDir, "mods");

            for (String modName : activeMods) {
                File modDir = new File(userModsRoot, modName);
                if (!modDir.exists() || !modDir.isDirectory()) {
                    modDir = new File(gameModsRoot, modName);
                }
                if (!modDir.exists() || !modDir.isDirectory()) {
                    continue;
                }

                File[] versionDirs = modDir.listFiles(f -> f.isDirectory() && (f.getName().startsWith("V") || f.getName().startsWith("v")));
                if (versionDirs != null) {
                    Arrays.sort(versionDirs, Comparator.comparing(File::getName, String.CASE_INSENSITIVE_ORDER).reversed());
                    for (File vDir : versionDirs) {
                        File modScriptDir = new File(vDir, "script");
                        if (modScriptDir.exists() && modScriptDir.isDirectory()) {
                            File[] modJars = modScriptDir.listFiles((dir, name) -> name.toLowerCase().endsWith(".jar"));
                            if (modJars != null) {
                                Arrays.sort(modJars, Comparator.comparing(File::getName, String.CASE_INSENSITIVE_ORDER));
                                for (File modJar : modJars) {
                                    try {
                                        cp.add(modJar.getCanonicalPath());
                                    } catch (IOException e) {
                                        cp.add(modJar.getAbsolutePath());
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // 4. Caciocavallo AWT Helper JARs (if present in cache)
        if (cacheDir != null) {
            File cacioDir = new File(cacheDir, "caciocavallo17");
            if (cacioDir.exists() && cacioDir.isDirectory()) {
                File[] cacioJars = cacioDir.listFiles((dir, name) -> name.toLowerCase().endsWith(".jar"));
                if (cacioJars != null) {
                    Arrays.sort(cacioJars, Comparator.comparing(File::getName, String.CASE_INSENSITIVE_ORDER));
                    for (File cJar : cacioJars) {
                        cp.add(cJar.getAbsolutePath());
                    }
                }
            }
        }

        return cp;
    }

    /**
     * Defensive parser for LauncherSettings.txt to load active mods list.
     * Delegates to SyxModSettings for authoritative RFC-8259 JSON and desktop format support.
     */
    public static List<String> loadActiveMods(String userHomeDir) {
        File home = (userHomeDir != null && !userHomeDir.trim().isEmpty()) ? new File(userHomeDir) : null;
        return git.artdeell.mojo.mods.SyxModSettings.loadActiveMods(home);
    }
}
