package git.artdeell.mojo.prefs;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.WindowManager;
import android.view.WindowMetrics;

import git.artdeell.mojo.Architecture;
import git.artdeell.mojo.Logger;
import git.artdeell.mojo.Tools;
import git.artdeell.mojo.utils.GpuUtils;

public final class DeviceAutoConfig {
    public static final String TAG = "DeviceAutoConfig";
    public static final String PREF_KEY_AUTO_CONFIG_VERSION = "auto_config_version";
    public static final int CURRENT_AUTO_CONFIG_VERSION = 1;

    private DeviceAutoConfig() {}

    /**
     * Checks if auto-configuration has already been performed.
     *
     * @param prefs SharedPreferences instance to check
     * @return true if auto_config_version >= CURRENT_AUTO_CONFIG_VERSION
     */
    public static boolean isConfigured(SharedPreferences prefs) {
        return prefs != null && prefs.getInt(PREF_KEY_AUTO_CONFIG_VERSION, 0) >= CURRENT_AUTO_CONFIG_VERSION;
    }

    /**
     * Executes hardware probing and persists optimal settings if not already configured.
     * Guarded by auto_config_version flag to ensure subsequent launches do not overwrite
     * user customizations.
     *
     * @param context Application context
     */
    public static void runAutoConfigIfNeeded(Context context) {
        if (context == null) return;
        if (LauncherPreferences.DEFAULT_PREF == null) {
            LauncherPreferences.DEFAULT_PREF = androidx.preference.PreferenceManager.getDefaultSharedPreferences(context);
        }
        SharedPreferences prefs = LauncherPreferences.DEFAULT_PREF;
        if (isConfigured(prefs)) {
            return;
        }
        runAutoConfig(context, prefs);
    }

    /**
     * Forces execution of hardware probing and persists settings to SharedPreferences.
     *
     * @param context Application context
     * @param prefs Target SharedPreferences instance
     */
    public static void runAutoConfig(Context context, SharedPreferences prefs) {
        if (prefs == null) {
            if (context != null) {
                if (LauncherPreferences.DEFAULT_PREF == null) {
                    LauncherPreferences.DEFAULT_PREF = androidx.preference.PreferenceManager.getDefaultSharedPreferences(context);
                }
                prefs = LauncherPreferences.DEFAULT_PREF;
            }
            if (prefs == null) return;
        }

        Log.i(TAG, "Executing First-Launch Device Auto-Configuration for Songs of Syx...");

        // 1. Hardware Probing
        int totalRamMb = 4096;
        if (context != null) {
            try {
                totalRamMb = Tools.getTotalDeviceMemory(context);
            } catch (Throwable t) {
                Log.w(TAG, "Failed to query device memory, falling back to 4096MB", t);
            }
        }

        boolean is32Bit = Architecture.is32BitsDevice();

        GpuUtils.GLInfo glInfo = null;
        try {
            glInfo = GpuUtils.getGlInfo();
        } catch (Throwable t) {
            Log.w(TAG, "Failed to query GL info", t);
        }

        int screenWidth = 1080;
        int screenHeight = 1920;
        if (context != null) {
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    WindowManager wm = context.getSystemService(WindowManager.class);
                    if (wm != null) {
                        WindowMetrics wmMetrics = wm.getCurrentWindowMetrics();
                        screenWidth = wmMetrics.getBounds().width();
                        screenHeight = wmMetrics.getBounds().height();
                    } else {
                        DisplayMetrics dm = context.getResources().getDisplayMetrics();
                        screenWidth = dm.widthPixels;
                        screenHeight = dm.heightPixels;
                    }
                } else {
                    DisplayMetrics dm = context.getResources().getDisplayMetrics();
                    screenWidth = dm.widthPixels;
                    screenHeight = dm.heightPixels;
                }
            } catch (Throwable t) {
                Log.w(TAG, "Failed to query display metrics, falling back to 1080x1920", t);
            }
        }
        int minSide = Math.min(screenWidth, screenHeight);
        if (minSide <= 0) minSide = 1080;

        // 2. Heuristic Calculations
        int recommendedRam = computeOptimalRam(totalRamMb, is32Bit);
        int recommendedResolutionRatio = computeOptimalResolutionRatio(minSide, totalRamMb, glInfo);
        String recommendedRenderer = "opengles2"; // GL4ES is universal stable default
        boolean alternateSurface = true;
        boolean sustainedPerf = false;
        boolean forceVsync = true;
        boolean zinkPreferSystemDriver = glInfo == null || !glInfo.isAdreno();

        // 3. Persist to SharedPreferences
        prefs.edit()
            .putInt("allocation", recommendedRam)
            .putInt("resolutionRatio", recommendedResolutionRatio)
            .putString("renderer", recommendedRenderer)
            .putBoolean("alternate_surface", alternateSurface)
            .putBoolean("sustainedPerformance", sustainedPerf)
            .putBoolean("force_vsync", forceVsync)
            .putBoolean("zinkPreferSystemDriver", zinkPreferSystemDriver)
            .putInt(PREF_KEY_AUTO_CONFIG_VERSION, CURRENT_AUTO_CONFIG_VERSION)
            .apply();

        // 4. Diagnostic Logging
        String logMsg = String.format(
            "Auto-Config Applied: RAM=%dMB (Device=%dMB, 32bit=%b), Resolution=%d%% (MinSide=%dpx), " +
            "Renderer=%s, GPU=%s %s",
            recommendedRam, totalRamMb, is32Bit, recommendedResolutionRatio, minSide,
            recommendedRenderer,
            glInfo != null ? glInfo.vendor : "unknown",
            glInfo != null ? glInfo.renderer : "unknown"
        );
        Log.i(TAG, logMsg);
        try {
            Logger.appendToLog(logMsg);
        } catch (Throwable ignored) {}
    }

    /**
     * Resets settings to recommended auto-configured values and refreshes in-memory preferences.
     * Callable from UI settings.
     *
     * @param context Application context
     */
    public static void resetToRecommended(Context context) {
        if (context == null) return;
        if (LauncherPreferences.DEFAULT_PREF == null) {
            LauncherPreferences.DEFAULT_PREF = androidx.preference.PreferenceManager.getDefaultSharedPreferences(context);
        }
        runAutoConfig(context, LauncherPreferences.DEFAULT_PREF);
        LauncherPreferences.loadPreferences(context);
    }

    /**
     * Computes the optimal JVM RAM allocation (in MB) according to device RAM and architecture.
     *
     * @param totalRamMb Physical device memory in MB
     * @return Tuned RAM allocation in MB, aligned to 8 MB seekbar increment and >= 512 MB
     */
    public static int computeOptimalRam(int totalRamMb) {
        return computeOptimalRam(totalRamMb, Architecture.is32BitsDevice());
    }

    /**
     * Computes the optimal JVM RAM allocation (in MB) according to device RAM and 32-bit status.
     *
     * 7-tier scale:
     * - Tier 1 (< 2048 MB): 768 MB (safe above 512 MB MIN_RAM, prevents OOM killer)
     * - Tier 2 (2048 - 3500 MB): 1536 MB
     * - Tier 3 (3501 - 5000 MB): 2048 MB
     * - Tier 4 (5001 - 7000 MB): 3072 MB
     * - Tier 5 (7001 - 9500 MB): 4608 MB
     * - Tier 6 (9501 - 13000 MB): 6144 MB
     * - Tier 7 (> 13000 MB): 8192 MB
     *
     * @param totalRamMb Physical device memory in MB
     * @param is32Bit Whether running on a 32-bit ABI / device
     * @return Tuned RAM allocation in MB, aligned to 8 MB seekbar increment and >= 512 MB
     */
    public static int computeOptimalRam(int totalRamMb, boolean is32Bit) {
        int val;
        if (is32Bit) {
            val = Math.min(800, Math.max(512, totalRamMb - 512));
        } else if (totalRamMb < 1024) {
            val = 512;
        } else if (totalRamMb <= 2048) {
            val = 768;
        } else if (totalRamMb <= 3500) {
            val = 1536;
        } else if (totalRamMb <= 5000) {
            val = 2048;
        } else if (totalRamMb <= 7000) {
            val = 3072;
        } else if (totalRamMb <= 9500) {
            val = 4608;
        } else if (totalRamMb <= 13000) {
            val = 6144;
        } else {
            val = 8192;
        }
        val = (val / 8) * 8;
        return Math.max(512, val);
    }

    /**
     * Computes the optimal resolution scaling percentage (50..100) to balance visual sharpness
     * with mobile GPU thermal throttling.
     *
     * @param minSide Shortest display dimension in pixels
     * @param totalRamMb Physical device memory in MB
     * @param isAdreno True if Qualcomm Adreno GPU
     * @return Resolution ratio percentage (25..100), aligned to 5% seekbar increment
     */
    public static int computeOptimalResolutionRatio(int minSide, int totalRamMb, boolean isAdreno) {
        int ratio;
        if (minSide <= 720) {
            ratio = 100;
        } else if (minSide <= 1080) {
            if (totalRamMb <= 4096 || !isAdreno) {
                ratio = 85;
            } else {
                ratio = 100;
            }
        } else {
            float target = 1080.0f;
            float rawRatio = (target / (float) minSide) * 100.0f;
            int increment = 5;
            ratio = Math.round(rawRatio / (float) increment) * increment;
        }
        return Math.max(25, Math.min(100, ratio));
    }

    /**
     * Overload for computeOptimalResolutionRatio taking GLInfo.
     */
    public static int computeOptimalResolutionRatio(int minSide, int totalRamMb, GpuUtils.GLInfo glInfo) {
        boolean isAdreno = glInfo != null && glInfo.isAdreno();
        return computeOptimalResolutionRatio(minSide, totalRamMb, isAdreno);
    }

    /**
     * Overload for computeOptimalResolutionRatio probing context.
     */
    public static int computeOptimalResolutionRatio(Context context) {
        if (context == null) return 100;
        int screenWidth = 1080;
        int screenHeight = 1920;
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                WindowManager wm = context.getSystemService(WindowManager.class);
                if (wm != null) {
                    WindowMetrics wmMetrics = wm.getCurrentWindowMetrics();
                    screenWidth = wmMetrics.getBounds().width();
                    screenHeight = wmMetrics.getBounds().height();
                } else {
                    DisplayMetrics dm = context.getResources().getDisplayMetrics();
                    screenWidth = dm.widthPixels;
                    screenHeight = dm.heightPixels;
                }
            } else {
                DisplayMetrics dm = context.getResources().getDisplayMetrics();
                screenWidth = dm.widthPixels;
                screenHeight = dm.heightPixels;
            }
        } catch (Throwable t) {
            Log.w(TAG, "Failed to query display metrics", t);
        }
        int minSide = Math.min(screenWidth, screenHeight);
        if (minSide <= 0) minSide = 1080;

        int totalRamMb = 4096;
        try {
            totalRamMb = Tools.getTotalDeviceMemory(context);
        } catch (Throwable t) {
            Log.w(TAG, "Failed to query device memory", t);
        }

        GpuUtils.GLInfo glInfo = null;
        try {
            glInfo = GpuUtils.getGlInfo();
        } catch (Throwable t) {
            Log.w(TAG, "Failed to query GL info", t);
        }

        return computeOptimalResolutionRatio(minSide, totalRamMb, glInfo);
    }
}
