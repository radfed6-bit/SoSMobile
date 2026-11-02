package git.artdeell.mojo.instances;

import java.io.File;

public class DisplayInstance {
    public transient File mInstanceRoot;
    public String name;
    public String versionId;
    public String version;
    public String icon;

    protected void sanitize() {
        sanitizeIcon();
    }

    public DisplayInstance() {
    }

    protected File getInstanceIconLocation() {
        return new File(mInstanceRoot, "icon.webp");
    }

    private void sanitizeIcon() {
        if(!InstanceIconProvider.hasStaticIcon(icon)) {
            icon = InstanceIconProvider.FALLBACK_ICON_NAME;
        }
    }
}
