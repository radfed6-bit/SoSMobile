package git.artdeell.mojo.mods;

import java.io.Serializable;

public class ModItem implements Serializable {
    private static final long serialVersionUID = 1L;

    public final ModInfo info;
    public boolean isActive;

    public ModItem(ModInfo info, boolean isActive) {
        this.info = info;
        this.isActive = isActive;
    }
}
