package git.artdeell.mojo.launch;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.Settings;
import androidx.annotation.NonNull;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import java.io.File;

/**
 * Storage permission helper implementing the 4 canonical storage permission states
 * for SoSMobile on Android:
 * - GRANTED_MANAGE_EXTERNAL_STORAGE (API 30+)
 * - GRANTED_LEGACY (API 23-29)
 * - APP_SPECIFIC_ONLY (Path is inside getExternalFilesDir() / getExternalCacheDir())
 * - DENIED (Shared storage access requested but permissions not granted)
 */
public final class StoragePermissions {
    public static final int REQUEST_CODE_LEGACY_STORAGE = 1001;
    public static final int REQUEST_CODE_MANAGE_STORAGE = 1002;

    public enum State {
        GRANTED_MANAGE_EXTERNAL_STORAGE,
        GRANTED_LEGACY,
        APP_SPECIFIC_ONLY,
        DENIED
    }

    private StoragePermissions() {}

    /**
     * Resolves the permission state for a specific target directory.
     *
     * @param context Android context
     * @param targetPath Target directory or file
     * @return Resolved StoragePermissions.State
     */
    public static State getPermissionState(Context context, File targetPath) {
        if (targetPath != null && isAppSpecificPath(context, targetPath)) {
            return State.APP_SPECIFIC_ONLY;
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (Environment.isExternalStorageManager()) {
                return State.GRANTED_MANAGE_EXTERNAL_STORAGE;
            }
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (hasLegacyPermissions(context)) {
                return State.GRANTED_LEGACY;
            }
        } else {
            // API < 23 granted at install time
            return State.GRANTED_LEGACY;
        }

        return State.DENIED;
    }

    /**
     * Checks if the app has full external storage access across the filesystem.
     *
     * @param context Android context
     * @return true if full access is granted
     */
    public static boolean hasFullStorageAccess(Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            return Environment.isExternalStorageManager();
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            return hasLegacyPermissions(context);
        }
        return true;
    }

    /**
     * Checks if a given path is within the app's private external storage directory.
     * Private app-specific directories require no runtime permissions.
     */
    public static boolean isAppSpecificPath(Context context, @NonNull File path) {
        try {
            String canonical = path.getCanonicalPath();
            File appExt = context.getExternalFilesDir(null);
            if (appExt != null && canonical.startsWith(appExt.getCanonicalPath())) {
                return true;
            }
            File appCache = context.getExternalCacheDir();
            if (appCache != null && canonical.startsWith(appCache.getCanonicalPath())) {
                return true;
            }
            File internalFiles = context.getFilesDir();
            if (internalFiles != null && canonical.startsWith(internalFiles.getCanonicalPath())) {
                return true;
            }
        } catch (Exception ignored) {}
        return false;
    }

    /**
     * Checks whether READ and WRITE external storage permissions are granted.
     */
    public static boolean hasLegacyPermissions(Context context) {
        int readPerm = ContextCompat.checkSelfPermission(context, Manifest.permission.READ_EXTERNAL_STORAGE);
        int writePerm = ContextCompat.checkSelfPermission(context, Manifest.permission.WRITE_EXTERNAL_STORAGE);
        return readPerm == PackageManager.PERMISSION_GRANTED && writePerm == PackageManager.PERMISSION_GRANTED;
    }

    /**
     * Dispatches the appropriate permission request depending on Android version.
     * On Android 11+ (API 30+), opens system settings for All Files Access.
     * On Android 6.0-10 (API 23-29), requests READ/WRITE runtime permissions.
     */
    public static void requestStoragePermission(Activity activity) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            requestManageStoragePermission(activity);
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            ActivityCompat.requestPermissions(
                activity,
                new String[]{Manifest.permission.READ_EXTERNAL_STORAGE, Manifest.permission.WRITE_EXTERNAL_STORAGE},
                REQUEST_CODE_LEGACY_STORAGE
            );
        }
    }

    /**
     * Requests MANAGE_EXTERNAL_STORAGE ("All Files Access") on Android 11+ (API 30+).
     */
    public static void requestManageStoragePermission(Activity activity) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            try {
                Intent intent = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION);
                intent.setData(Uri.parse("package:" + activity.getPackageName()));
                activity.startActivityForResult(intent, REQUEST_CODE_MANAGE_STORAGE);
            } catch (Exception e) {
                Intent intent = new Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION);
                activity.startActivityForResult(intent, REQUEST_CODE_MANAGE_STORAGE);
            }
        }
    }
}
