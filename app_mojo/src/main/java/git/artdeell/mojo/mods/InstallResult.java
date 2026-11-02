package git.artdeell.mojo.mods;

import java.io.Serializable;

public class InstallResult implements Serializable {
    private static final long serialVersionUID = 1L;

    public final boolean success;
    public final String modName;
    public final String errorMessage;

    public InstallResult(boolean success, String modName, String errorMessage) {
        this.success = success;
        this.modName = modName;
        this.errorMessage = errorMessage;
    }
}
