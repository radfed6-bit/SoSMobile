package git.artdeell.mojo.mods;

import android.app.AlertDialog;
import android.net.Uri;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageButton;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.kdt.mcgui.MineButton;

import git.artdeell.mojo.MojoApplication;
import git.artdeell.mojo.R;
import git.artdeell.mojo.Tools;
import git.artdeell.mojo.contracts.OpenDocumentWithExtension;
import git.artdeell.mojo.prefs.LauncherPreferences;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Mod Manager Screen for listing, toggling, installing ZIP archives,
 * and deleting installed user mods.
 * Complies with Feature 14 and Feature 15 specifications.
 */
public class ModManagerFragment extends Fragment {
    public static final String TAG = "ModManagerFragment";

    private RecyclerView mRecyclerView;
    private ModListAdapter mAdapter;
    private View mEmptyLayout;
    private ProgressBar mProgressBar;
    private TextView mTextSummary;
    private ActivityResultLauncher<Object> mZipPickerLauncher;

    private final List<ModItem> mModItems = new ArrayList<>();

    @Override
    public void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        mZipPickerLauncher = registerForActivityResult(
                new OpenDocumentWithExtension("zip"),
                this::handleZipUriSelected
        );
    }

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        return inflater.inflate(R.layout.fragment_mod_manager, container, false);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);

        ImageButton btnBack = view.findViewById(R.id.button_back);
        ImageButton btnRefresh = view.findViewById(R.id.button_refresh_mods);
        MineButton btnInstallZip = view.findViewById(R.id.button_install_mod_zip);

        mRecyclerView = view.findViewById(R.id.recycler_mods);
        mEmptyLayout = view.findViewById(R.id.layout_empty_mods);
        mProgressBar = view.findViewById(R.id.progress_loading);
        mTextSummary = view.findViewById(R.id.text_mods_summary);

        btnBack.setOnClickListener(v -> Tools.removeCurrentFragment(requireActivity()));
        btnRefresh.setOnClickListener(v -> reloadModsAsync());
        btnInstallZip.setOnClickListener(v -> mZipPickerLauncher.launch(null));

        mAdapter = new ModListAdapter(
                mModItems,
                this::onModToggled,
                this::confirmModDelete
        );

        mRecyclerView.setLayoutManager(new LinearLayoutManager(requireContext()));
        mRecyclerView.setAdapter(mAdapter);

        reloadModsAsync();
    }

    private void reloadModsAsync() {
        if (mProgressBar != null) {
            mProgressBar.setVisibility(View.VISIBLE);
        }
        MojoApplication.sExecutorService.execute(() -> {
            File userHome = (Tools.DIR_GAME_HOME != null && !Tools.DIR_GAME_HOME.isEmpty())
                    ? new File(Tools.DIR_GAME_HOME)
                    : new File(System.getProperty("user.home", "."));
            String savedGameDir = LauncherPreferences.getGameDirectory();
            File gameDir = (savedGameDir != null && !savedGameDir.trim().isEmpty())
                    ? new File(savedGameDir)
                    : new File("/SoSMobile");

            List<ModInfo> discovered = SyxModManager.discoverMods(gameDir, userHome);
            List<String> activeMods = SyxModManager.loadActiveMods(userHome);

            List<ModItem> items = new ArrayList<>();
            for (ModInfo info : discovered) {
                boolean isActive = activeMods.contains(info.getFolderName());
                items.add(new ModItem(info, isActive));
            }
            Collections.sort(items, (a, b) -> a.info.getName().compareToIgnoreCase(b.info.getName()));

            Tools.runOnUiThread(() -> {
                if (!isAdded()) return;
                if (mProgressBar != null) {
                    mProgressBar.setVisibility(View.GONE);
                }
                mModItems.clear();
                mModItems.addAll(items);
                mAdapter.notifyDataSetChanged();

                int activeCount = 0;
                for (ModItem item : mModItems) {
                    if (item.isActive) activeCount++;
                }
                if (mTextSummary != null) {
                    mTextSummary.setText(getString(R.string.mod_summary_format, mModItems.size(), activeCount));
                }

                if (mEmptyLayout != null) {
                    mEmptyLayout.setVisibility(mModItems.isEmpty() ? View.VISIBLE : View.GONE);
                }
                if (mRecyclerView != null) {
                    mRecyclerView.setVisibility(mModItems.isEmpty() ? View.GONE : View.VISIBLE);
                }
            });
        });
    }

    private void onModToggled(ModItem item, boolean isActive) {
        item.isActive = isActive;
        MojoApplication.sExecutorService.execute(() -> {
            File userHome = (Tools.DIR_GAME_HOME != null && !Tools.DIR_GAME_HOME.isEmpty())
                    ? new File(Tools.DIR_GAME_HOME)
                    : new File(System.getProperty("user.home", "."));
            SyxModManager.toggleMod(userHome, item.info.getFolderName(), isActive);
            reloadModsAsync();
        });
    }

    private void confirmModDelete(ModItem item) {
        if (!item.info.isUserMod()) {
            Toast.makeText(requireContext(), R.string.mod_cannot_delete_game_mod, Toast.LENGTH_SHORT).show();
            return;
        }

        new AlertDialog.Builder(requireContext())
                .setTitle(R.string.mod_delete_confirm_title)
                .setMessage(getString(R.string.mod_delete_confirm_message, item.info.getName()))
                .setPositiveButton(R.string.global_delete, (d, w) -> deleteModAsync(item))
                .setNegativeButton(android.R.string.cancel, null)
                .show();
    }

    private void deleteModAsync(ModItem item) {
        if (mProgressBar != null) {
            mProgressBar.setVisibility(View.VISIBLE);
        }
        MojoApplication.sExecutorService.execute(() -> {
            File userHome = (Tools.DIR_GAME_HOME != null && !Tools.DIR_GAME_HOME.isEmpty())
                    ? new File(Tools.DIR_GAME_HOME)
                    : new File(System.getProperty("user.home", "."));
            File userModsDir = SyxModManager.getUserModsDir(userHome);
            UninstallResult result = SyxModManager.uninstallMod(item.info.getFolderName(), userModsDir, userHome);

            Tools.runOnUiThread(() -> {
                if (!isAdded()) return;
                if (mProgressBar != null) {
                    mProgressBar.setVisibility(View.GONE);
                }
                if (result.success) {
                    Toast.makeText(requireContext(), getString(R.string.mod_uninstall_success, item.info.getName()), Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(requireContext(), getString(R.string.mod_uninstall_failed, result.message), Toast.LENGTH_LONG).show();
                }
                reloadModsAsync();
            });
        });
    }

    private void handleZipUriSelected(@Nullable Uri uri) {
        if (uri == null) return;
        if (mProgressBar != null) {
            mProgressBar.setVisibility(View.VISIBLE);
        }
        MojoApplication.sExecutorService.execute(() -> {
            try {
                File cacheDir = (Tools.DIR_CACHE != null) ? Tools.DIR_CACHE : requireContext().getCacheDir();
                File tempZip = new File(cacheDir, "import_" + System.currentTimeMillis() + ".zip");
                try (InputStream in = requireContext().getContentResolver().openInputStream(uri);
                     OutputStream out = new FileOutputStream(tempZip)) {
                    if (in != null) {
                        byte[] buffer = new byte[8192];
                        int len;
                        while ((len = in.read(buffer)) > 0) {
                            out.write(buffer, 0, len);
                        }
                    }
                }

                File userHome = (Tools.DIR_GAME_HOME != null && !Tools.DIR_GAME_HOME.isEmpty())
                        ? new File(Tools.DIR_GAME_HOME)
                        : new File(System.getProperty("user.home", "."));
                File userModsDir = SyxModManager.getUserModsDir(userHome);
                InstallResult result = SyxModManager.installModZip(tempZip, userModsDir);
                if (tempZip.exists()) {
                    tempZip.delete();
                }

                Tools.runOnUiThread(() -> {
                    if (!isAdded()) return;
                    if (mProgressBar != null) {
                        mProgressBar.setVisibility(View.GONE);
                    }
                    if (result.success) {
                        Toast.makeText(requireContext(), getString(R.string.mod_install_success, result.modName), Toast.LENGTH_SHORT).show();
                    } else {
                        new AlertDialog.Builder(requireContext())
                                .setTitle(R.string.global_error)
                                .setMessage(getString(R.string.mod_install_failed, result.errorMessage != null ? result.errorMessage : "Unknown error"))
                                .setPositiveButton(android.R.string.ok, null)
                                .show();
                    }
                    reloadModsAsync();
                });
            } catch (Exception e) {
                Tools.runOnUiThread(() -> {
                    if (!isAdded()) return;
                    if (mProgressBar != null) {
                        mProgressBar.setVisibility(View.GONE);
                    }
                    Toast.makeText(requireContext(), e.getMessage(), Toast.LENGTH_LONG).show();
                });
            }
        });
    }
}
