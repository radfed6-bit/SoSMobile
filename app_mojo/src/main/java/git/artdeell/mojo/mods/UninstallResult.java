package git.artdeell.mojo.mods;

import java.io.Serializable;

public class UninstallResult implements Serializable {
    private static final long serialVersionUID = 1L;

    public final boolean success;
    public final String message;

    public UninstallResult(boolean success, String message) {
        this.success = success;
        this.message = message;
    }
}
