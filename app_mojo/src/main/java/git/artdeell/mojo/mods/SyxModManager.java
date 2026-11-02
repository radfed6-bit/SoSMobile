package git.artdeell.mojo.mods;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipException;
import java.util.zip.ZipFile;

/**
 * High-level Mod Manager Service providing discovery, safe ZIP installation,
 * uninstallation, and configuration synchronization.
 * Strictly adheres to Feature 13, 14, 15, and 16 specifications and test oracles.
 */
public final class SyxModManager {
    private SyxModManager() {}

    public static File getUserModsDir(File userHome) {
        if (userHome == null) {
            userHome = new File(System.getProperty("user.home", "."));
        }
        return new File(userHome, ".local/share/songsofsyx/mods");
    }

    public static File getGameModsDir(File gameDir) {
        if (gameDir == null) {
            return new File("mods");
        }
        return new File(gameDir, "mods");
    }

    public static File getSettingsFile(File userHome) {
        return SyxModSettings.getSettingsFile(userHome);
    }

    public static List<ModInfo> discoverMods(File gameDir, File userHome) {
        Map<String, ModInfo> map = ModScanner.discoverMods(gameDir, userHome);
        return new ArrayList<>(map.values());
    }

    public static List<ModInfo> getInstalledMods(File gameDir, File userHome) {
        Map<String, ModInfo> map = ModScanner.discoverMods(gameDir, userHome);
        List<String> activeMods = SyxModSettings.loadActiveMods(userHome);
        for (ModInfo mod : map.values()) {
            if (activeMods.contains(mod.getFolderName())) {
                mod.setActive(true);
            }
        }
        return new ArrayList<>(map.values());
    }

    public static List<String> loadActiveMods(File userHome) {
        return SyxModSettings.loadActiveMods(userHome);
    }

    public static boolean saveActiveMods(File userHome, List<String> activeMods) {
        return SyxModSettings.saveActiveMods(userHome, activeMods);
    }

    public static boolean toggleMod(File userHome, String modName, boolean active) {
        return SyxModSettings.setModActive(userHome, modName, active);
    }

    /**
     * Extracts ZIP archive to mod directory with Zip-Slip path traversal prevention and root folder normalization.
     * Aligns with ModManagerOracle.install_mod_zip in tests/e2e/harness/oracles.py.
     */
    public static InstallResult installModZip(File zipPath, File targetModsDir) {
        if (zipPath == null || !zipPath.exists() || !zipPath.isFile()) {
            return new InstallResult(false, null, "Not a valid ZIP file.");
        }

        if (targetModsDir != null) {
            targetModsDir.mkdirs();
        } else {
            return new InstallResult(false, null, "Target mods directory is null.");
        }

        ZipFile zipFile = null;
        try {
            zipFile = new ZipFile(zipPath);
        } catch (ZipException ze) {
            return new InstallResult(false, null, "Not a valid ZIP file: " + ze.getMessage());
        } catch (IOException e) {
            return new InstallResult(false, null, "Not a valid ZIP file: " + e.getMessage());
        }

        try {
            // Step 1: Zip-Slip Security Pre-Scan
            Enumeration<? extends ZipEntry> entries = zipFile.entries();
            Set<String> topDirs = new HashSet<>();
            boolean hasInfoAtRootOrTop = false;

            while (entries.hasMoreElements()) {
                ZipEntry entry = entries.nextElement();
                String name = entry.getName();

                // Path traversal check
                if (name.startsWith("/") || name.startsWith("\\") || name.contains("..")) {
                    return new InstallResult(false, null, "Security error: ZIP path traversal detected.");
                }

                try {
                    Path normalized = Paths.get(name).normalize();
                    if (normalized.startsWith("..") || normalized.isAbsolute()) {
                        return new InstallResult(false, null, "Security error: ZIP path traversal detected.");
                    }
                } catch (Exception pe) {
                    return new InstallResult(false, null, "Security error: ZIP path traversal detected.");
                }

                String[] parts = name.split("[/\\\\]");
                if (parts.length > 0 && !parts[0].isEmpty()) {
                    topDirs.add(parts[0]);
                }
                if (name.equalsIgnoreCase("_Info.txt") || name.toLowerCase().endsWith("/_info.txt")) {
                    hasInfoAtRootOrTop = true;
                }
            }

            // Step 2: Determine Destination Mod Directory
            boolean hasSingleRootMod = topDirs.size() == 1 && hasInfoAtRootOrTop;
            File modFolder;

            if (hasSingleRootMod) {
                // Extract directly to targetModsDir so top folder becomes targetModsDir/<topDir>
                String rootDirName = topDirs.iterator().next();
                modFolder = new File(targetModsDir, rootDirName);
                extractAllEntries(zipFile, targetModsDir);
            } else {
                // Flat archive or multiple folders: wrap in folder named after the ZIP
                String modName = zipPath.getName().replaceFirst("[.][^.]+$", "");
                modFolder = new File(targetModsDir, modName);
                modFolder.mkdirs();
                extractAllEntries(zipFile, modFolder);
            }

            // Step 3: Validate _Info.txt exists
            File infoFile = new File(modFolder, "_Info.txt");
            if (!infoFile.exists()) {
                // Check if nested in an immediate subdirectory
                File[] subs = modFolder.listFiles(File::isDirectory);
                if (subs != null) {
                    for (File sub : subs) {
                        if (new File(sub, "_Info.txt").exists()) {
                            return new InstallResult(true, sub.getName(), "Mod installed successfully.");
                        }
                    }
                }
                // Missing _Info.txt -> rollback extraction
                deleteRecursively(modFolder);
                return new InstallResult(false, null, "Installed mod is missing required _Info.txt file.");
            }

            return new InstallResult(true, modFolder.getName(), "Mod installed successfully.");
        } catch (SecurityException se) {
            return new InstallResult(false, null, "Security error: ZIP path traversal detected.");
        } catch (Exception e) {
            return new InstallResult(false, null, "Extraction failed: " + e.getMessage());
        } finally {
            try {
                if (zipFile != null) zipFile.close();
            } catch (IOException ignored) {}
        }
    }

    private static void extractAllEntries(ZipFile zipFile, File destinationDir) throws IOException {
        String canonicalDestDirPath = destinationDir.getCanonicalPath();
        Enumeration<? extends ZipEntry> entries = zipFile.entries();

        while (entries.hasMoreElements()) {
            ZipEntry entry = entries.nextElement();
            File destFile = new File(destinationDir, entry.getName());
            String canonicalDestFilePath = destFile.getCanonicalPath();

            if (!canonicalDestFilePath.startsWith(canonicalDestDirPath + File.separator) && !canonicalDestFilePath.equals(canonicalDestDirPath)) {
                throw new SecurityException("Security error: ZIP path traversal detected.");
            }

            if (entry.isDirectory()) {
                destFile.mkdirs();
            } else {
                File parent = destFile.getParentFile();
                if (parent != null) parent.mkdirs();
                try (InputStream is = zipFile.getInputStream(entry);
                     OutputStream os = new FileOutputStream(destFile)) {
                    byte[] buffer = new byte[8192];
                    int len;
                    while ((len = is.read(buffer)) > 0) {
                        os.write(buffer, 0, len);
                    }
                }
            }
        }
    }

    /**
     * Safely deletes mod directory and purges it from LauncherSettings.txt.
     * Aligns with ModManagerOracle.uninstall_mod in tests/e2e/harness/oracles.py.
     */
    public static UninstallResult uninstallMod(String modName, File targetModsDir, File userHome) {
        if (modName == null || modName.trim().isEmpty()) {
            return new UninstallResult(false, "Mod name is empty.");
        }

        if (targetModsDir == null) {
            return new UninstallResult(false, "Target mods directory is null.");
        }

        File modFolder = new File(targetModsDir, modName);
        if (!modFolder.exists()) {
            return new UninstallResult(false, "Mod directory does not exist: " + modName);
        }

        try {
            // Guard against deleting outside mods directory
            if (!modFolder.getCanonicalFile().getParentFile().equals(targetModsDir.getCanonicalFile())) {
                return new UninstallResult(false, "Security error: Cannot delete folder outside mods directory.");
            }

            // Recursive deletion
            boolean deleted = deleteRecursively(modFolder);
            if (!deleted && modFolder.exists()) {
                return new UninstallResult(false, "Failed to delete mod folder: " + modName);
            }

            // Purge from LauncherSettings.txt
            if (userHome != null) {
                SyxModSettings.removeModFromActive(userHome, modName);
            }

            return new UninstallResult(true, "Mod " + modName + " removed successfully.");
        } catch (Exception e) {
            return new UninstallResult(false, "Failed to delete mod folder: " + e.getMessage());
        }
    }

    public static boolean deleteRecursively(File file) {
        if (file == null || !file.exists()) {
            return false;
        }
        if (file.isDirectory()) {
            File[] children = file.listFiles();
            if (children != null) {
                for (File child : children) {
                    deleteRecursively(child);
                }
            }
        }
        return file.delete();
    }
}
