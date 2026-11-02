package git.artdeell.mojo.fragments;

import static git.artdeell.mojo.Tools.openPath;
import static git.artdeell.mojo.Tools.shareLog;

import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;

import git.artdeell.mojo.CustomControlsActivity;
import git.artdeell.mojo.R;
import git.artdeell.mojo.Tools;
import git.artdeell.mojo.extra.ExtraConstants;
import git.artdeell.mojo.extra.ExtraCore;
import git.artdeell.mojo.instances.Instance;
import git.artdeell.mojo.instances.Instances;
import git.artdeell.mojo.launch.GamePathValidator;
import git.artdeell.mojo.launch.PathValidationResult;
import git.artdeell.mojo.mods.ModManagerFragment;
import git.artdeell.mojo.prefs.LauncherPreferences;
import git.artdeell.mojo.ui.GameFolderSelectorFragment;
import git.artdeell.mojo.utils.FileUtils;

import java.io.File;

public class MainMenuFragment extends Fragment {
    public static final String TAG = "MainMenuFragment";

    private TextView mTextGameFolderPath;
    private TextView mTextGameFolderStatus;
    private ImageView mImageValidationBadge;
    private Button mButtonChangeFolder;

    public MainMenuFragment(){
        super(R.layout.fragment_launcher);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        Button mNewsButton = view.findViewById(R.id.news_button);
        Button mDiscordButton = view.findViewById(R.id.social_media_button);
        Button mCustomControlButton = view.findViewById(R.id.custom_control_button);
        Button mShareLogsButton = view.findViewById(R.id.share_logs_button);
        Button mOpenDirectoryButton = view.findViewById(R.id.open_files_button);
        Button mModsButton = view.findViewById(R.id.mods_button);
        Button mPlayButton = view.findViewById(R.id.play_button);

        mTextGameFolderPath = view.findViewById(R.id.text_game_folder_path);
        mTextGameFolderStatus = view.findViewById(R.id.text_game_folder_status);
        mImageValidationBadge = view.findViewById(R.id.image_validation_badge);
        mButtonChangeFolder = view.findViewById(R.id.button_change_game_folder);

        if (mButtonChangeFolder != null) {
            mButtonChangeFolder.setOnClickListener(v ->
                    Tools.swapFragment(requireActivity(), GameFolderSelectorFragment.class, GameFolderSelectorFragment.TAG, null)
            );
        }

        mNewsButton.setOnClickListener(v -> Tools.openURL(requireActivity(), Tools.URL_HOME));
        mDiscordButton.setOnClickListener(v -> Tools.openURL(requireActivity(), getString(R.string.social_media_invite)));
        if (mCustomControlButton != null) {
            mCustomControlButton.setVisibility(View.GONE);
        }

        mPlayButton.setOnClickListener(v -> {
            String gameDir = LauncherPreferences.getGameDirectory();
            PathValidationResult result = GamePathValidator.validatePath(gameDir);
            if (!result.isValid) {
                new AlertDialog.Builder(requireContext())
                        .setTitle(R.string.global_error)
                        .setMessage(result.errorMessage != null ? result.errorMessage : getString(R.string.no_game_dir_selected))
                        .setPositiveButton(R.string.btn_select_game_folder, (d, w) ->
                                Tools.swapFragment(requireActivity(), GameFolderSelectorFragment.class, GameFolderSelectorFragment.TAG, null)
                        )
                        .setNegativeButton(android.R.string.cancel, null)
                        .show();
                return;
            }
            ExtraCore.setValue(ExtraConstants.LAUNCH_GAME, true);
        });

        mShareLogsButton.setOnClickListener((v) -> shareLog(requireContext()));
        mOpenDirectoryButton.setOnClickListener((v) -> openGameDirectory(v.getContext()));
        if (mModsButton != null) {
            mModsButton.setOnClickListener(v ->
                    Tools.swapFragment(requireActivity(), ModManagerFragment.class, ModManagerFragment.TAG, null)
            );
        }

        mNewsButton.setOnLongClickListener((v) -> {
            Tools.swapFragment(requireActivity(), GamepadMapperFragment.class, GamepadMapperFragment.TAG, null);
            return true;
        });

        updateGameFolderCard();
    }

    @Override
    public void onResume() {
        super.onResume();
        updateGameFolderCard();
    }

    private void updateGameFolderCard() {
        if (mTextGameFolderPath == null) return;
        String gameDir = LauncherPreferences.getGameDirectory();
        if (gameDir != null && !gameDir.trim().isEmpty()) {
            mTextGameFolderPath.setText(gameDir);
            PathValidationResult result = GamePathValidator.validatePath(gameDir);
            if (result.isValid) {
                mTextGameFolderStatus.setText(R.string.game_folder_valid);
                mTextGameFolderStatus.setTextColor(0xFF4CAF50);
                if (mImageValidationBadge != null) {
                    mImageValidationBadge.setImageResource(R.drawable.ic_px_check);
                }
            } else {
                mTextGameFolderStatus.setText(result.errorMessage != null ? result.errorMessage : getString(R.string.game_folder_invalid));
                mTextGameFolderStatus.setTextColor(0xFFE57373);
                if (mImageValidationBadge != null) {
                    mImageValidationBadge.setImageResource(R.drawable.ic_px_warn);
                }
            }
        } else {
            mTextGameFolderPath.setText(R.string.game_folder_invalid);
            mTextGameFolderStatus.setText(R.string.no_game_dir_selected);
            mTextGameFolderStatus.setTextColor(0xFFE57373);
            if (mImageValidationBadge != null) {
                mImageValidationBadge.setImageResource(R.drawable.ic_px_warn);
            }
        }
    }

    private void openGameDirectory(Context context) {
        String gameDir = LauncherPreferences.getGameDirectory();
        if (gameDir != null && !gameDir.trim().isEmpty()) {
            File dir = new File(gameDir);
            if (dir.exists()) {
                openPath(context, dir, false);
                return;
            }
        }

        Instance instance = Instances.loadSelectedInstance();
        if (instance != null) {
            File gameDirectory = instance.getGameDirectory();
            if (FileUtils.ensureDirectorySilently(gameDirectory)) {
                openPath(context, gameDirectory, false);
                return;
            }
        }

        Toast.makeText(context, R.string.gamedir_open_failed, Toast.LENGTH_LONG).show();
    }
}
