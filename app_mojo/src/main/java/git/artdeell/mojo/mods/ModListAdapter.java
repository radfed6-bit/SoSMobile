package git.artdeell.mojo.mods;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.appcompat.widget.SwitchCompat;
import androidx.recyclerview.widget.RecyclerView;

import git.artdeell.mojo.R;

import java.util.List;

/**
 * RecyclerView Adapter for presenting installed Songs of Syx mods.
 * Complies with Feature 14 Mod Manager UI presentation requirements.
 */
public class ModListAdapter extends RecyclerView.Adapter<ModListAdapter.ModViewHolder> {

    public interface OnModToggleListener {
        void onToggle(ModItem item, boolean isActive);
    }

    public interface OnModDeleteListener {
        void onDelete(ModItem item);
    }

    private final List<ModItem> mItems;
    private final OnModToggleListener mToggleListener;
    private final OnModDeleteListener mDeleteListener;

    public ModListAdapter(List<ModItem> items, OnModToggleListener toggleListener, OnModDeleteListener deleteListener) {
        this.mItems = items;
        this.mToggleListener = toggleListener;
        this.mDeleteListener = deleteListener;
    }

    @NonNull
    @Override
    public ModViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_mod_entry, parent, false);
        return new ModViewHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull ModViewHolder holder, int position) {
        ModItem item = mItems.get(position);
        holder.bind(item, mToggleListener, mDeleteListener);
    }

    @Override
    public int getItemCount() {
        return mItems.size();
    }

    public static class ModViewHolder extends RecyclerView.ViewHolder {
        private final TextView textName;
        private final TextView textVersion;
        private final TextView textAuthor;
        private final TextView textDesc;
        private final TextView textVersions;
        private final TextView textLocation;
        private final SwitchCompat switchActive;
        private final ImageButton btnDelete;
        private final ImageView imgWarning;
        private final View layoutDetails;

        public ModViewHolder(@NonNull View itemView) {
            super(itemView);
            textName = itemView.findViewById(R.id.text_mod_name);
            textVersion = itemView.findViewById(R.id.text_mod_version);
            textAuthor = itemView.findViewById(R.id.text_mod_author);
            textDesc = itemView.findViewById(R.id.text_mod_desc);
            textVersions = itemView.findViewById(R.id.text_mod_target_versions);
            textLocation = itemView.findViewById(R.id.text_mod_location);
            switchActive = itemView.findViewById(R.id.switch_mod_active);
            btnDelete = itemView.findViewById(R.id.button_delete_mod);
            imgWarning = itemView.findViewById(R.id.image_mod_warning);
            layoutDetails = itemView.findViewById(R.id.layout_mod_details);
        }

        public void bind(ModItem item, OnModToggleListener toggleListener, OnModDeleteListener deleteListener) {
            ModInfo info = item.info;
            textName.setText(info.getName());
            textVersion.setText(info.getVersion() != null && !info.getVersion().isEmpty() ? "v" + info.getVersion() : "");
            textAuthor.setText(info.getAuthor() != null && !info.getAuthor().isEmpty() ? "By: " + info.getAuthor() : "");
            textDesc.setText(info.getDescription() != null ? info.getDescription() : "");

            if (info.getTargetVersions() != null && !info.getTargetVersions().isEmpty()) {
                textVersions.setText(String.join(", ", info.getTargetVersions()));
                textVersions.setVisibility(View.VISIBLE);
            } else {
                textVersions.setVisibility(View.GONE);
            }

            textLocation.setText(info.isUserMod() ? R.string.mod_loc_user : R.string.mod_loc_game);

            imgWarning.setVisibility(info.isValid() ? View.GONE : View.VISIBLE);
            if (!info.isValid() && info.getErrorMessage() != null) {
                textDesc.setText("[Warning: " + info.getErrorMessage() + "]\n" + textDesc.getText());
            }

            // Bind switch without firing listener
            switchActive.setOnCheckedChangeListener(null);
            switchActive.setChecked(item.isActive);
            switchActive.setOnCheckedChangeListener((btn, isChecked) -> {
                if (toggleListener != null) toggleListener.onToggle(item, isChecked);
            });

            // Delete button: enabled for user mods only
            if (info.isUserMod()) {
                btnDelete.setVisibility(View.VISIBLE);
                btnDelete.setOnClickListener(v -> {
                    if (deleteListener != null) deleteListener.onDelete(item);
                });
            } else {
                btnDelete.setVisibility(View.GONE);
            }

            // Card expand/collapse on tap
            itemView.setOnClickListener(v -> {
                int vis = layoutDetails.getVisibility() == View.VISIBLE ? View.GONE : View.VISIBLE;
                layoutDetails.setVisibility(vis);
            });
        }
    }
}
