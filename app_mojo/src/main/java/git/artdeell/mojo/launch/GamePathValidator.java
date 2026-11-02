package git.artdeell.mojo.launch;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Enumeration;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * Authoritative 9-step validation pipeline for Songs of Syx game directories.
 * Strictly aligns with GamePathValidatorOracle in tests/e2e/harness/oracles.py.
 */
public final class GamePathValidator {
    public static final long MIN_JAR_SIZE = 10L * 1024L * 1024L; // 10 MB threshold (canonical ~35.6 MB)

    private GamePathValidator() {}

    /**
     * Executes the authoritative 9-step validation pipeline on the given game path.
     *
     * @param pathStr Path to validate
     * @return PathValidationResult with detailed status and resolved components
     */
    public static PathValidationResult validatePath(String pathStr) {
        // Step 1: Check Empty / Whitespace
        if (pathStr == null || pathStr.trim().isEmpty()) {
            return PathValidationResult.failure(new File(""), "Game path cannot be empty.", null, null, null);
        }

        File gamePath = new File(pathStr.trim());
        try {
            gamePath = gamePath.getCanonicalFile();
        } catch (IOException e) {
            gamePath = gamePath.getAbsoluteFile();
        }

        // Step 2: Existence Check
        if (!gamePath.exists()) {
            return PathValidationResult.failure(gamePath, "Game directory does not exist: " + gamePath.getAbsolutePath(), null, null, null);
        }

        // Step 3: Directory Check
        if (!gamePath.isDirectory()) {
            return PathValidationResult.failure(gamePath, "Specified path is a file, not a directory: " + gamePath.getAbsolutePath(), null, null, null);
        }

        // Step 4: Executable JAR Existence
        File jarPath = new File(gamePath, "SongsOfSyx.jar");
        if (!jarPath.exists()) {
            return PathValidationResult.failure(gamePath, "Missing executable JAR: " + jarPath.getAbsolutePath(), null, null, null);
        }

        // Step 5: JAR Size Threshold
        long jarSize = jarPath.length();
        if (jarSize < MIN_JAR_SIZE) {
            return PathValidationResult.failure(
                    gamePath,
                    "SongsOfSyx.jar is truncated or corrupted (size: " + jarSize + " bytes, expected >= " + MIN_JAR_SIZE + " bytes).",
                    jarPath,
                    null,
                    null
            );
        }

        // Step 6: Core Assets Directory Check
        File baseDir = new File(gamePath, "base");
        if (!baseDir.exists() || !baseDir.isDirectory()) {
            return PathValidationResult.failure(gamePath, "Missing core game assets folder: " + baseDir.getAbsolutePath(), jarPath, null, null);
        }

        // Step 7: Data Archive Existence
        File dataZip = new File(baseDir, "data.zip");
        if (!dataZip.exists()) {
            return PathValidationResult.failure(gamePath, "Missing core data archive: " + dataZip.getAbsolutePath(), jarPath, baseDir, null);
        }

        // Step 8: Data Archive Readability and Integrity Check
        try (ZipFile zf = new ZipFile(dataZip)) {
            if (zf.size() == 0) {
                return PathValidationResult.failure(gamePath, "Corrupted base/data.zip archive.", jarPath, baseDir, dataZip);
            }
            Enumeration<? extends ZipEntry> entries = zf.entries();
            if (entries.hasMoreElements()) {
                ZipEntry entry = entries.nextElement();
                try (InputStream is = zf.getInputStream(entry)) {
                    byte[] buffer = new byte[1024];
                    is.read(buffer);
                }
            }
        } catch (Exception e) {
            String msg = e.getMessage();
            return PathValidationResult.failure(
                    gamePath,
                    (msg != null && msg.toLowerCase().contains("corrupt"))
                            ? "Corrupted base/data.zip archive."
                            : "Cannot read base/data.zip: " + (msg != null ? msg : e.getClass().getSimpleName()),
                    jarPath,
                    baseDir,
                    dataZip
            );
        }

        // Step 9: Scenario Script Discovery
        List<File> scenarioScripts = new ArrayList<>();
        File scriptDir = new File(baseDir, "script");
        if (scriptDir.exists() && scriptDir.isDirectory()) {
            File[] scriptFiles = scriptDir.listFiles((dir, name) -> name.toLowerCase().endsWith(".jar"));
            if (scriptFiles != null) {
                Arrays.sort(scriptFiles, Comparator.comparing(File::getName, String.CASE_INSENSITIVE_ORDER));
                scenarioScripts.addAll(Arrays.asList(scriptFiles));
            }
        }

        return PathValidationResult.success(gamePath, jarPath, baseDir, dataZip, scenarioScripts);
    }
}
