package git.artdeell.mojo.mods;

import java.io.File;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Data model representing Songs of Syx mod metadata, filesystem status, and activation state.
 * Fully complies with Feature 13 and ModMetadata oracle in tests/e2e/harness/models.py.
 */
public class ModInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    private static final Pattern INFO_PATTERN = Pattern.compile("([A-Za-z0-9_]+)\\s*:\\s*\"([^\"]*)\"\\s*,?");

    private final String folderName;
    private final String name;
    private final String version;
    private final String author;
    private final String description;
    private final String infoUrl;
    private final File modDirectory;
    private final List<String> targetVersions;
    private final List<String> scriptJars;
    private final boolean isValid;
    private final String errorMessage;
    private final boolean isUserMod;
    private boolean isActive;

    public ModInfo(
            String folderName,
            String name,
            String version,
            String author,
            String description,
            String infoUrl,
            File modDirectory,
            List<String> targetVersions,
            List<String> scriptJars,
            boolean isValid,
            String errorMessage,
            boolean isUserMod) {
        this.folderName = folderName != null ? folderName : "";
        this.name = name != null && !name.trim().isEmpty() ? name : this.folderName;
        this.version = version != null ? version : "unknown";
        this.author = author != null ? author : "unknown";
        this.description = description != null ? description : "";
        this.infoUrl = infoUrl != null ? infoUrl : "";
        this.modDirectory = modDirectory;
        this.targetVersions = targetVersions != null ? Collections.unmodifiableList(new ArrayList<>(targetVersions)) : Collections.emptyList();
        this.scriptJars = scriptJars != null ? Collections.unmodifiableList(new ArrayList<>(scriptJars)) : Collections.emptyList();
        this.isValid = isValid;
        this.errorMessage = errorMessage;
        this.isUserMod = isUserMod;
        this.isActive = false;
    }

    public String getFolderName() {
        return folderName;
    }

    public String getName() {
        return name;
    }

    public String getVersion() {
        return version;
    }

    public String getAuthor() {
        return author;
    }

    public String getDescription() {
        return description;
    }

    public String getInfoUrl() {
        return infoUrl;
    }

    public File getModDirectory() {
        return modDirectory;
    }

    public List<String> getTargetVersions() {
        return targetVersions;
    }

    public List<String> getScriptJars() {
        return scriptJars;
    }

    public boolean isValid() {
        return isValid;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public boolean isUserMod() {
        return isUserMod;
    }

    public boolean isActive() {
        return isActive;
    }

    public void setActive(boolean active) {
        this.isActive = active;
    }

    public boolean supportsVersion(String versionPrefix) {
        if (versionPrefix == null) return false;
        String normalized = versionPrefix.toUpperCase();
        for (String v : targetVersions) {
            if (v != null && v.toUpperCase().equals(normalized)) {
                return true;
            }
        }
        return false;
    }

    public boolean hasScripts() {
        return !scriptJars.isEmpty();
    }

    /**
     * Parses raw _Info.txt file content according to info/MAKE_A_MOD.txt specification.
     */
    public static ModInfo parseInfoContent(String content, String folderName, File modDirectory, boolean isUserMod) {
        String name = null;
        String version = "0.1";
        String author = "Unknown Author";
        String desc = "";
        String info = "";

        if (content != null) {
            Matcher matcher = INFO_PATTERN.matcher(content);
            while (matcher.find()) {
                String key = matcher.group(1).toUpperCase();
                String val = matcher.group(2);
                switch (key) {
                    case "NAME":
                        name = val;
                        break;
                    case "VERSION":
                        version = val;
                        break;
                    case "AUTHOR":
                        author = val;
                        break;
                    case "DESC":
                        desc = val;
                        break;
                    case "INFO":
                        info = val;
                        break;
                }
            }
        }

        boolean valid = name != null && !name.trim().isEmpty();
        if (name == null || name.trim().isEmpty()) {
            name = (folderName != null && !folderName.trim().isEmpty()) ? folderName : "Unknown Mod";
        }

        String errorMsg = valid ? null : "Missing NAME field in _Info.txt";

        return new ModInfo(
                folderName,
                name,
                version,
                author,
                desc,
                info,
                modDirectory,
                Collections.emptyList(),
                Collections.emptyList(),
                valid,
                errorMsg,
                isUserMod
        );
    }

    public static ModInfo createInvalid(File modDirectory, String folderName, String errorMessage, boolean isUserMod) {
        return new ModInfo(
                folderName,
                folderName != null ? folderName : "Unknown Mod",
                "unknown",
                "unknown",
                "",
                "",
                modDirectory,
                Collections.emptyList(),
                Collections.emptyList(),
                false,
                errorMessage,
                isUserMod
        );
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        ModInfo modInfo = (ModInfo) o;
        return Objects.equals(folderName, modInfo.folderName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(folderName);
    }

    @Override
    public String toString() {
        return "ModInfo{name='" + name + "', folder='" + folderName + "', version='" + version + "', valid=" + isValid + "}";
    }
}
