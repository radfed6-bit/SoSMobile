package git.artdeell.mojo.ui;

import android.app.AlertDialog;
import android.content.Context;
import android.os.Bundle;
import android.os.Environment;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;

import git.artdeell.mojo.R;
import git.artdeell.mojo.Tools;
import git.artdeell.mojo.launch.GamePathValidator;
import git.artdeell.mojo.launch.PathValidationResult;
import git.artdeell.mojo.launch.StoragePermissions;
import git.artdeell.mojo.prefs.LauncherPreferences;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;

public class GameFolderSelectorFragment extends Fragment {
    public static final String TAG = "GameFolderSelectorFragment";

    private File currentDirectory;
    private TextView textCurrentPath;
    private TextView textPreviewStatus;
    private ImageView imagePreviewBadge;
    private ListView listDirectories;
    private Button buttonConfirmSelection;
    private ArrayAdapter<String> adapter;
    private final List<String> displayedItems = new ArrayList<>();
    private final List<File> currentFiles = new ArrayList<>();

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        return inflater.inflate(R.layout.fragment_game_folder_selector, container, false);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);

        textCurrentPath = view.findViewById(R.id.text_current_path);
        textPreviewStatus = view.findViewById(R.id.text_preview_status);
        imagePreviewBadge = view.findViewById(R.id.image_preview_badge);
        listDirectories = view.findViewById(R.id.list_directories);
        buttonConfirmSelection = view.findViewById(R.id.button_confirm_selection);

        view.findViewById(R.id.button_back).setOnClickListener(v -> Tools.removeCurrentFragment(requireActivity()));
        view.findViewById(R.id.button_cancel_selection).setOnClickListener(v -> Tools.removeCurrentFragment(requireActivity()));

        // Quick Jumps
        view.findViewById(R.id.chip_jump_storage).setOnClickListener(v -> navigateTo(Environment.getExternalStorageDirectory()));
        view.findViewById(R.id.chip_jump_downloads).setOnClickListener(v -> {
            File downloads = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
            navigateTo(downloads != null && downloads.exists() ? downloads : new File(Environment.getExternalStorageDirectory(), "Download"));
        });
        view.findViewById(R.id.chip_jump_app_specific).setOnClickListener(v -> {
            File appFiles = requireContext().getExternalFilesDir(null);
            if (appFiles != null) navigateTo(appFiles);
        });
        view.findViewById(R.id.chip_jump_root).setOnClickListener(v -> navigateTo(new File("/")));

        // Edit path manually
        view.findViewById(R.id.button_edit_path_manually).setOnClickListener(v -> showManualPathDialog());

        // Setup ListView adapter
        adapter = new ArrayAdapter<>(requireContext(), android.R.layout.simple_list_item_1, displayedItems);
        listDirectories.setAdapter(adapter);

        listDirectories.setOnItemClickListener((parent, itemView, position, id) -> {
            if (position < currentFiles.size()) {
                File target = currentFiles.get(position);
                if (target != null && target.isDirectory()) {
                    navigateTo(target);
                }
            }
        });

        buttonConfirmSelection.setOnClickListener(v -> confirmSelection());

        // Initial directory: current saved game directory or default external storage
        String savedDir = LauncherPreferences.getGameDirectory();
        if (savedDir != null && !savedDir.trim().isEmpty() && new File(savedDir).exists()) {
            navigateTo(new File(savedDir));
        } else {
            navigateTo(Environment.getExternalStorageDirectory());
        }
    }

    private void navigateTo(File dir) {
        if (dir == null) return;
        try {
            currentDirectory = dir.getCanonicalFile();
        } catch (IOException e) {
            currentDirectory = dir.getAbsoluteFile();
        }

        textCurrentPath.setText(currentDirectory.getAbsolutePath());

        // Refresh list
        displayedItems.clear();
        currentFiles.clear();

        File parent = currentDirectory.getParentFile();
        if (parent != null && parent.canRead()) {
            displayedItems.add(".. (Parent Directory)");
            currentFiles.add(parent);
        }

        File[] subdirs = currentDirectory.listFiles(File::isDirectory);
        if (subdirs != null) {
            Arrays.sort(subdirs, Comparator.comparing(File::getName, String.CASE_INSENSITIVE_ORDER));
            for (File sub : subdirs) {
                displayedItems.add(sub.getName() + "/");
                currentFiles.add(sub);
            }
        } else if (!StoragePermissions.hasFullStorageAccess(requireContext())
                && !StoragePermissions.isAppSpecificPath(requireContext(), currentDirectory)) {
            // Cannot list files due to permissions
            displayedItems.add("[Access Denied: Grant All Files Access to browse this directory]");
            currentFiles.add(null);
        }

        adapter.notifyDataSetChanged();
        updateValidationPreview();
    }

    private void updateValidationPreview() {
        if (currentDirectory == null) return;
        PathValidationResult result = GamePathValidator.validatePath(currentDirectory.getAbsolutePath());
        if (result.isValid) {
            textPreviewStatus.setText(R.string.game_folder_valid);
            textPreviewStatus.setTextColor(0xFF4CAF50); // Green
            imagePreviewBadge.setImageResource(R.drawable.ic_px_check);
            buttonConfirmSelection.setEnabled(true);
        } else {
            textPreviewStatus.setText(result.errorMessage != null ? result.errorMessage : getString(R.string.game_folder_invalid));
            textPreviewStatus.setTextColor(0xFFE57373); // Soft red
            imagePreviewBadge.setImageResource(R.drawable.ic_px_warn);
        }
    }

    private void showManualPathDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(requireContext());
        builder.setTitle(R.string.manual_path_dialog_title);

        final EditText input = new EditText(requireContext());
        input.setText(currentDirectory != null ? currentDirectory.getAbsolutePath() : "");
        builder.setView(input);

        builder.setPositiveButton(android.R.string.ok, (dialog, which) -> {
            String path = input.getText().toString().trim();
            if (!path.isEmpty()) {
                File file = new File(path);
                if (file.exists() && file.isDirectory()) {
                    navigateTo(file);
                } else {
                    Toast.makeText(requireContext(), "Directory does not exist: " + path, Toast.LENGTH_SHORT).show();
                }
            }
        });
        builder.setNegativeButton(android.R.string.cancel, (dialog, which) -> dialog.cancel());
        builder.show();
    }

    private void confirmSelection() {
        if (currentDirectory == null) return;
        PathValidationResult result = GamePathValidator.validatePath(currentDirectory.getAbsolutePath());
        if (!result.isValid) {
            new AlertDialog.Builder(requireContext())
                    .setTitle(R.string.global_error)
                    .setMessage(result.errorMessage)
                    .setPositiveButton(android.R.string.ok, null)
                    .show();
            return;
        }

        LauncherPreferences.setGameDirectory(requireContext(), currentDirectory.getAbsolutePath());
        Toast.makeText(requireContext(), R.string.game_folder_valid, Toast.LENGTH_SHORT).show();
        Tools.removeCurrentFragment(requireActivity());
    }
}
