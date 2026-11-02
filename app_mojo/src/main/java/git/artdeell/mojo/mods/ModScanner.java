package git.artdeell.mojo.mods;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * Filesystem scanner and parser for Songs of Syx mods.
 * Complies with Feature 13 and ModManagerOracle.discover_mods.
 */
public final class ModScanner {
    private static final Pattern VERSION_DIR_PATTERN = Pattern.compile("(?i)^V\\d+$");

    private ModScanner() {}

    /**
     * Discovers all mods across user mods directory and game mods directory.
     * User mods take precedence if folder names collide.
     */
    public static Map<String, ModInfo> discoverMods(File gameDir, File userHomeDir) {
        Map<String, ModInfo> discovered = new LinkedHashMap<>();

        // 1. User mods directory (<user_home>/.local/share/songsofsyx/mods)
        if (userHomeDir != null) {
            File userModsDir = new File(userHomeDir, ".local/share/songsofsyx/mods");
            scanDirectoryIntoMap(userModsDir, true, discovered);
        }

        // 2. Game mods directory (<game_dir>/mods)
        if (gameDir != null) {
            File gameModsDir = new File(gameDir, "mods");
            scanDirectoryIntoMap(gameModsDir, false, discovered);
        }

        return discovered;
    }

    public static List<ModInfo> scanDirectory(File modsDir, boolean isUserMod) {
        List<ModInfo> result = new ArrayList<>();
        if (modsDir == null || !modsDir.exists() || !modsDir.isDirectory()) {
            return result;
        }

        File[] subdirs = modsDir.listFiles(File::isDirectory);
        if (subdirs == null) {
            return result;
        }

        Arrays.sort(subdirs, Comparator.comparing(File::getName, String.CASE_INSENSITIVE_ORDER));
        for (File dir : subdirs) {
            if (dir.getName().startsWith(".")) continue;
            ModInfo info = scanSingleMod(dir, isUserMod);
            if (info != null) {
                result.add(info);
            }
        }
        return result;
    }

    private static void scanDirectoryIntoMap(File modsDir, boolean isUserMod, Map<String, ModInfo> map) {
        List<ModInfo> list = scanDirectory(modsDir, isUserMod);
        for (ModInfo mod : list) {
            if (!map.containsKey(mod.getFolderName())) {
                map.put(mod.getFolderName(), mod);
            }
        }
    }

    public static ModInfo scanSingleMod(File modDir, boolean isUserMod) {
        if (modDir == null || !modDir.exists() || !modDir.isDirectory()) {
            return null;
        }

        String folderName = modDir.getName();
        File infoFile = new File(modDir, "_Info.txt");

        ModInfo baseInfo;
        if (!infoFile.exists() || !infoFile.isFile()) {
            baseInfo = ModInfo.createInvalid(modDir, folderName, "Missing _Info.txt file", isUserMod);
        } else {
            String content = readFileToString(infoFile);
            if (content == null) {
                baseInfo = ModInfo.createInvalid(modDir, folderName, "Failed to read _Info.txt", isUserMod);
            } else {
                baseInfo = ModInfo.parseInfoContent(content, folderName, modDir, isUserMod);
            }
        }

        // Scan version subdirectories and script JARs
        List<String> targetVersions = new ArrayList<>();
        List<String> scriptJars = new ArrayList<>();

        File[] files = modDir.listFiles();
        if (files != null) {
            for (File file : files) {
                if (file.isDirectory() && VERSION_DIR_PATTERN.matcher(file.getName()).matches()) {
                    targetVersions.add(file.getName());
                    File scriptDir = new File(file, "script");
                    if (scriptDir.exists() && scriptDir.isDirectory()) {
                        File[] jars = scriptDir.listFiles((d, n) -> n.toLowerCase().endsWith(".jar"));
                        if (jars != null) {
                            Arrays.sort(jars, Comparator.comparing(File::getName, String.CASE_INSENSITIVE_ORDER));
                            for (File jar : jars) {
                                try {
                                    scriptJars.add(jar.getCanonicalPath());
                                } catch (Exception e) {
                                    scriptJars.add(jar.getAbsolutePath());
                                }
                            }
                        }
                    }
                }
            }
        }

        Collections.sort(targetVersions, String.CASE_INSENSITIVE_ORDER);
        Collections.sort(scriptJars, String.CASE_INSENSITIVE_ORDER);

        return new ModInfo(
                baseInfo.getFolderName(),
                baseInfo.getName(),
                baseInfo.getVersion(),
                baseInfo.getAuthor(),
                baseInfo.getDescription(),
                baseInfo.getInfoUrl(),
                modDir,
                targetVersions,
                scriptJars,
                baseInfo.isValid(),
                baseInfo.getErrorMessage(),
                isUserMod
        );
    }

    private static String readFileToString(File file) {
        StringBuilder sb = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(file), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line).append("\n");
            }
            return sb.toString();
        } catch (Exception e) {
            return null;
        }
    }
}
