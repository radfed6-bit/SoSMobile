package git.artdeell.mojo;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import git.artdeell.mojo.launch.StoragePermissions;
import git.artdeell.mojo.prefs.LauncherPreferences;
import git.artdeell.mojo.tasks.AsyncAssetManager;

public class TestStorageActivity extends Activity {
    private AlertDialog mPermissionRequestDialog;
    private boolean mPermsRequired = false;
    private boolean mPermsDialogShown = false;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        mPermsDialogShown = false;
        if (!StoragePermissions.hasFullStorageAccess(this)) {
            mPermsRequired = true;
        } else {
            exit();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (!mPermsRequired) return;
        if (StoragePermissions.hasFullStorageAccess(this)) {
            mPermsRequired = false;
            exit();
            return;
        }
        if (!mPermsDialogShown) {
            requestStoragePermission();
        } else {
            showRerequestDialog();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (mPermissionRequestDialog != null) mPermissionRequestDialog.dismiss();
    }

    private void showRerequestDialog() {
        if (mPermissionRequestDialog != null) mPermissionRequestDialog.dismiss();
        mPermissionRequestDialog = new AlertDialog.Builder(this)
                .setTitle(R.string.global_error)
                .setMessage(R.string.toast_permission_denied)
                .setPositiveButton(android.R.string.ok, (d, i) -> requestStoragePermission())
                .setNegativeButton(android.R.string.cancel, (d, i) -> {
                    mPermsRequired = false;
                    exit();
                })
                .show();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == StoragePermissions.REQUEST_CODE_LEGACY_STORAGE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                mPermsRequired = false;
                exit();
            } else {
                mPermsDialogShown = true;
                showRerequestDialog();
            }
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == StoragePermissions.REQUEST_CODE_MANAGE_STORAGE) {
            if (StoragePermissions.hasFullStorageAccess(this)) {
                mPermsRequired = false;
                exit();
            } else {
                mPermsDialogShown = true;
                showRerequestDialog();
            }
        }
    }

    public static boolean isStorageAllowed(Context context) {
        return StoragePermissions.hasFullStorageAccess(context);
    }

    private void requestStoragePermission() {
        mPermsDialogShown = true;
        StoragePermissions.requestStoragePermission(this);
    }

    private void exit() {
        if (!Tools.checkStorageRoot(this)) {
            startActivity(new Intent(this, MissingStorageActivity.class));
            return;
        }
        // Initialize constants (implicitly) and preferences after we confirm that we have storage.
        LauncherPreferences.loadPreferences(this);
        AsyncAssetManager.unpackComponents(this);
        AsyncAssetManager.unpackSingleFiles(this);

        Intent intent = new Intent(this, LauncherActivity.class);
        startActivity(intent);
        finish();
    }
}
