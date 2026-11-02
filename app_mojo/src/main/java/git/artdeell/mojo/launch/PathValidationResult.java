package git.artdeell.mojo.launch;

import java.io.File;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Result model representing the outcome of a Songs of Syx game directory validation.
 */
public final class PathValidationResult implements Serializable {
    private static final long serialVersionUID = 1L;

    public final boolean isValid;
    public final File gamePath;
    public final String errorMessage;
    public final File jarPath;
    public final File baseDir;
    public final File dataZipPath;
    public final List<File> scenarioScripts;

    public PathValidationResult(
            boolean isValid,
            File gamePath,
            String errorMessage,
            File jarPath,
            File baseDir,
            File dataZipPath,
            List<File> scenarioScripts) {
        this.isValid = isValid;
        this.gamePath = gamePath;
        this.errorMessage = errorMessage;
        this.jarPath = jarPath;
        this.baseDir = baseDir;
        this.dataZipPath = dataZipPath;
        this.scenarioScripts = scenarioScripts != null
                ? Collections.unmodifiableList(new ArrayList<>(scenarioScripts))
                : Collections.emptyList();
    }

    public static PathValidationResult success(File gamePath, File jarPath, File baseDir, File dataZipPath, List<File> scripts) {
        return new PathValidationResult(true, gamePath, null, jarPath, baseDir, dataZipPath, scripts);
    }

    public static PathValidationResult failure(File gamePath, String errorMessage, File jarPath, File baseDir, File dataZipPath) {
        return new PathValidationResult(false, gamePath, errorMessage, jarPath, baseDir, dataZipPath, null);
    }

    @Override
    public String toString() {
        return "PathValidationResult{" +
                "isValid=" + isValid +
                ", gamePath=" + gamePath +
                ", errorMessage='" + errorMessage + '\'' +
                ", jarPath=" + jarPath +
                ", baseDir=" + baseDir +
                ", dataZipPath=" + dataZipPath +
                ", scenarioScripts=" + scenarioScripts.size() +
                '}';
    }
}
