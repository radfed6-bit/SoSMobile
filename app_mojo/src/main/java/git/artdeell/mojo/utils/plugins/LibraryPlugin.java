package git.artdeell.mojo.utils.plugins;

import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.util.Log;

import java.io.File;

public class LibraryPlugin {
    private static final String TAG = "LibraryPlugin";

    // Known plugins constants
    public static final String ID_ANGLE_PLUGIN = "git.mojo.angle";
    public static final String ID_FFMPEG_PLUGIN = "git.mojo.ffmpeg";
    public static final String ID_ZINK_PLUGIN = "git.mojo.zink";
    public static final String ID_MESA_PLUGIN = "git.mojo.mesa";

    private String appId;
    private String libraryPath;
    private LibraryPlugin(String app, String libraryPath){
        this.appId = app;
        this.libraryPath = libraryPath;
    }
    public static LibraryPlugin discoverPlugin(Context ctx, String appId){
        if (ctx == null) return null;
        String libraryPath;
        try {
            PackageInfo pluginPackage = ctx.getPackageManager().getPackageInfo(appId, PackageManager.GET_SHARED_LIBRARY_FILES);
            libraryPath = pluginPackage.applicationInfo.nativeLibraryDir;
            if (new File(libraryPath).exists()) {
                return new LibraryPlugin(appId, libraryPath);
            }
        } catch (Exception ignored) {
        }

        // Fallback: Check for bundled/internal plugin assets in the app itself
        File internalDir = getInternalPluginDir(ctx, appId);
        if (internalDir != null && extractBundledPluginIfNeeded(ctx, appId, internalDir)) {
            return new LibraryPlugin(appId, internalDir.getAbsolutePath());
        }

        Log.e(TAG, "Plugin discover failed for: " + appId);
        return null;
    }

    private static String getArchSubdir() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
            for (String abi : android.os.Build.SUPPORTED_ABIS) {
                if ("arm64-v8a".equals(abi)) return "arm64-v8a";
                if ("armeabi-v7a".equals(abi)) return "armeabi-v7a";
                if ("x86_64".equals(abi)) return "x86_64";
                if ("x86".equals(abi)) return "x86";
            }
        }
        return "arm64-v8a";
    }

    private static File getInternalPluginDir(Context ctx, String appId) {
        if (ctx == null) return null;
        return new File(ctx.getFilesDir(), "plugins/" + appId + "/lib/" + getArchSubdir());
    }

    private static boolean extractBundledPluginIfNeeded(Context ctx, String appId, File targetDir) {
        String assetPath = "plugins/" + appId + "/" + getArchSubdir();
        try {
            String[] files = ctx.getAssets().list(assetPath);
            if (files == null || files.length == 0) {
                return targetDir.exists() && targetDir.list() != null && targetDir.list().length > 0;
            }
            if (!targetDir.exists()) {
                targetDir.mkdirs();
            }
            for (String fileName : files) {
                File targetFile = new File(targetDir, fileName);
                if (targetFile.exists() && targetFile.length() > 0) {
                    continue;
                }
                try (java.io.InputStream in = ctx.getAssets().open(assetPath + "/" + fileName);
                     java.io.FileOutputStream out = new java.io.FileOutputStream(targetFile)) {
                    byte[] buffer = new byte[65536];
                    int read;
                    while ((read = in.read(buffer)) != -1) {
                        out.write(buffer, 0, read);
                    }
                }
                targetFile.setReadable(true, false);
                targetFile.setExecutable(true, false);
            }
            return true;
        } catch (Exception e) {
            Log.e(TAG, "Failed extracting bundled plugin " + appId, e);
            return targetDir.exists() && targetDir.list() != null && targetDir.list().length > 0;
        }
    }

    public String getId(){
        return appId;
    }

    public String getLibraryPath(){
        return libraryPath;
    }
    public String resolveAbsolutePath(String library) {
        return new File(libraryPath, library).getAbsolutePath();
    }
    public File resolve(String library) {
        return new File(libraryPath, library);
    }

    public boolean checkLibraries(String... libs){
        for(String lib : libs){
            if(!(new File(libraryPath, lib).exists())) return false;
        }
        return true;
    }
}
