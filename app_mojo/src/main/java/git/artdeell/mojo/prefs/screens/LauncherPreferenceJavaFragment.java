package git.artdeell.mojo.prefs.screens;

import static git.artdeell.mojo.Architecture.is32BitsDevice;
import static git.artdeell.mojo.Tools.getTotalDeviceMemory;

import android.os.Bundle;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.preference.EditTextPreference;
import androidx.preference.Preference;

import git.artdeell.mojo.R;
import git.artdeell.mojo.Tools;
import git.artdeell.mojo.contracts.OpenDocumentWithExtension;
import git.artdeell.mojo.multirt.MultiRTConfigDialog;
import git.artdeell.mojo.prefs.CustomSeekBarPreference;
import git.artdeell.mojo.prefs.DeviceAutoConfig;
import git.artdeell.mojo.prefs.LauncherPreferences;

public class LauncherPreferenceJavaFragment extends LauncherPreferenceFragment {
    private MultiRTConfigDialog mDialogScreen;
    private final ActivityResultLauncher<Object> mVmInstallLauncher =
            registerForActivityResult(new OpenDocumentWithExtension("xz"), (data)->{
                if(data != null) Tools.installRuntimeFromUri(getContext(), data);
            });

    @Override
    public void onCreatePreferences(Bundle b, String str) {
        int ramAllocation = LauncherPreferences.PREF_RAM_ALLOCATION;
        // Triggers a write for some reason
        addPreferencesFromResource(R.xml.pref_java);

        CustomSeekBarPreference memorySeekbar = requirePreference("allocation",
                CustomSeekBarPreference.class);

        int maxRAM;
        int deviceRam = getTotalDeviceMemory(memorySeekbar.getContext());

        if(is32BitsDevice() || deviceRam < 2048) maxRAM = Math.min(1024, deviceRam);
        else maxRAM = deviceRam - (deviceRam < 3064 ? 800 : 1024); //To have a minimum for the device to breathe

        memorySeekbar.setMaxKeepIncrement(maxRAM);
        memorySeekbar.setValue(ramAllocation);
        memorySeekbar.setSuffix(" MB");

        EditTextPreference editJVMArgs = findPreference("javaArgs");
        if (editJVMArgs != null) {
            editJVMArgs.setOnBindEditTextListener(TextView::setSingleLine);
        }

        requirePreference("install_jre").setOnPreferenceClickListener(preference->{
            openMultiRTDialog();
            return true;
        });

        Preference resetPref = findPreference("reset_recommended_settings");
        if (resetPref == null) {
            resetPref = new Preference(requireContext());
            resetPref.setKey("reset_recommended_settings");
            resetPref.setTitle("Reset to Recommended Settings");
            resetPref.setSummary("Re-detect device hardware and restore recommended RAM and graphics configuration");
            resetPref.setIcon(R.drawable.ic_px_sliders);
            getPreferenceScreen().addPreference(resetPref);
        }
        resetPref.setOnPreferenceClickListener(preference -> {
            DeviceAutoConfig.resetToRecommended(requireContext());
            memorySeekbar.setValue(LauncherPreferences.PREF_RAM_ALLOCATION);
            Toast.makeText(requireContext(), "Recommended settings restored", Toast.LENGTH_SHORT).show();
            return true;
        });
    }

    private void openMultiRTDialog() {
        if (mDialogScreen == null) {
            mDialogScreen = new MultiRTConfigDialog();
            mDialogScreen.prepare(getContext(), mVmInstallLauncher);
        }
        mDialogScreen.show();
    }
}
