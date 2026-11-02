package git.artdeell.mojo.prefs;

import android.content.Context;
import android.util.AttributeSet;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.preference.Preference;

import com.kdt.mcgui.ProgressLayout;

import java.io.File;
import java.io.IOException;
import java.util.concurrent.Future;

import git.artdeell.mojo.MojoApplication;
import git.artdeell.mojo.R;
import git.artdeell.mojo.Tools;

public class ClearPartfileCachePreference extends Preference {
    private static final double ONE_MEGABYTE = (1024d * 1024d);
    private final Future<?> mSizeCalcFuture;

    public ClearPartfileCachePreference(@NonNull Context context) {
        this(context, null);
    }

    public ClearPartfileCachePreference(@NonNull Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);
        setSummary(R.string.pref_clean_partfiles_subtitle_wait);
        mSizeCalcFuture = MojoApplication.sExecutorService.submit(this::calculateSizeBackground);
    }

    private File getPartFilesDir() {
        return new File(Tools.DIR_GAME_HOME, "partfiles");
    }

    private void clearCacheBackground() {
        ProgressLayout.setProgress(ProgressLayout.DATA_MIGRATION, 0, R.string.clean_partfiles_wait);
        try {
            File[] files = getPartFilesDir().listFiles();
            if(files != null) {
                for(File f : files) {
                    if(f.isDirectory()) continue;
                    if(!f.delete()) throw new IOException("Failed to remove " + f.getName());
                }
            }
            calculateSizeBackground();
        } catch (IOException e) {
            Tools.showErrorRemote(e);
        }
        ProgressLayout.clearProgress(ProgressLayout.DATA_MIGRATION);
    }

    private void calculateSizeBackground() {
        File[] files = getPartFilesDir().listFiles();
        double size = 0;
        if(files != null && files.length > 0) {
            long usedSpace = 0;
            for(File f : files) {
                if(Thread.interrupted()) return;
                long fileLen = f.length();
                if(fileLen != -1) usedSpace += fileLen;
            }
            size = usedSpace / ONE_MEGABYTE;
        }
        final double finalSize = size;
        Tools.runOnUiThread(() ->
                setSummary(getContext().getString(R.string.pref_clean_partfiles_subtitle, finalSize))
        );
    }

    @Override
    public void onDetached() {
        super.onDetached();
        mSizeCalcFuture.cancel(true);
    }

    @Override
    protected void onClick() {
        if(!ProgressLayout.ensureNoOngoingTasks(getContext())) return;
        MojoApplication.sExecutorService.execute(this::clearCacheBackground);
    }
}
