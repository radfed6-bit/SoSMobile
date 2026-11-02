package git.artdeell.mojo.input;

import android.animation.Animator;
import android.animation.AnimatorListenerAdapter;
import android.annotation.SuppressLint;
import android.content.Context;
import android.util.AttributeSet;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.ViewGroup;
import android.view.animation.AccelerateInterpolator;
import android.view.animation.DecelerateInterpolator;
import android.widget.ImageButton;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import git.artdeell.mojo.CallbackBridge;
import git.artdeell.mojo.LwjglGlfwKeycode;
import git.artdeell.mojo.R;
import git.artdeell.mojo.game.GameActivity;
import git.artdeell.mojo.input.keyboard.TouchCharInput;

/**
 * Floating game HUD overlay for Songs of Syx.
 * Provides quick access to essential game controls:
 * - Pause / Play (Space)
 * - Game Speed Cycle (1x, 2x, 3x, 4x)
 * - Rotate Structure (R)
 * - Menu / Cancel (ESC)
 * - Software Keyboard Toggle (TouchCharInput)
 * - Vertical drag handle for repositioning along screen edge
 * - Collapsible pill bar
 */
public class FloatingHUDView extends LinearLayout {

    // Android KeyCodes matching E2E test FloatingHUDOracle
    public static final int KEYCODE_SPACE  = KeyEvent.KEYCODE_SPACE;  // 62
    public static final int KEYCODE_1      = KeyEvent.KEYCODE_1;      // 8
    public static final int KEYCODE_2      = KeyEvent.KEYCODE_2;      // 9
    public static final int KEYCODE_3      = KeyEvent.KEYCODE_3;      // 10
    public static final int KEYCODE_4      = KeyEvent.KEYCODE_4;      // 11
    public static final int KEYCODE_R      = KeyEvent.KEYCODE_R;      // 46
    public static final int KEYCODE_ESCAPE = KeyEvent.KEYCODE_ESCAPE; // 111

    // GLFW KeyCodes matching LwjglGlfwKeycode
    public static final int GLFW_KEY_SPACE  = LwjglGlfwKeycode.GLFW_KEY_SPACE;   // 32
    public static final int GLFW_KEY_1      = LwjglGlfwKeycode.GLFW_KEY_1;       // 49
    public static final int GLFW_KEY_2      = LwjglGlfwKeycode.GLFW_KEY_2;       // 50
    public static final int GLFW_KEY_3      = LwjglGlfwKeycode.GLFW_KEY_3;       // 51
    public static final int GLFW_KEY_4      = LwjglGlfwKeycode.GLFW_KEY_4;       // 52
    public static final int GLFW_KEY_R      = LwjglGlfwKeycode.GLFW_KEY_R;       // 82
    public static final int GLFW_KEY_ESCAPE = LwjglGlfwKeycode.GLFW_KEY_ESCAPE;  // 256

    public static final int[] SPEED_KEYCODES = {
        KEYCODE_1, KEYCODE_2, KEYCODE_3, KEYCODE_4
    };
    public static final String[] SPEED_LABELS = {
        "1x", "2x", "3x", "4x"
    };

    private LinearLayout mRootContainer;
    private LinearLayout mActionsContainer;
    private View mDragHandle;
    private ImageButton mBtnPause;
    private TextView mBtnSpeed;
    private ImageButton mBtnRotate;
    private TextView mBtnEscape;
    private ImageButton mBtnKeyboard;
    private ImageButton mBtnCollapse;

    private int mCurrentSpeedIndex = 0;
    private boolean mIsPaused = false;
    private boolean mIsCollapsed = false;
    private boolean mIsKeyboardVisible = false;

    // Drag-to-reposition state
    private float mInitialTouchY;
    private float mInitialTranslationY;
    private boolean mIsDragging = false;
    private int mTouchSlop;

    private TouchCharInput mBoundCharInput;

    public FloatingHUDView(@NonNull Context context) {
        this(context, null);
    }

    public FloatingHUDView(@NonNull Context context, @Nullable AttributeSet attrs) {
        this(context, attrs, 0);
    }

    public FloatingHUDView(@NonNull Context context, @Nullable AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
        init(context);
    }

    private void init(Context context) {
        mTouchSlop = ViewConfiguration.get(context).getScaledTouchSlop();
        setOrientation(HORIZONTAL);
        setClipChildren(false);
        setClipToPadding(false);
    }

    @Override
    protected void onFinishInflate() {
        super.onFinishInflate();
        mRootContainer = findViewById(R.id.hud_root_container);
        mActionsContainer = findViewById(R.id.hud_actions_container);
        mDragHandle = findViewById(R.id.hud_drag_handle);
        mBtnPause = findViewById(R.id.btn_hud_pause);
        mBtnSpeed = findViewById(R.id.btn_hud_speed);
        mBtnRotate = findViewById(R.id.btn_hud_rotate);
        mBtnEscape = findViewById(R.id.btn_hud_escape);
        mBtnKeyboard = findViewById(R.id.btn_hud_keyboard);
        mBtnCollapse = findViewById(R.id.btn_hud_collapse);

        setupListeners();
    }

    @SuppressLint("ClickableViewAccessibility")
    private void setupListeners() {
        if (mBtnPause != null) {
            mBtnPause.setOnClickListener(v -> pressPause());
        }
        if (mBtnSpeed != null) {
            mBtnSpeed.setOnClickListener(v -> cycleSpeed());
        }
        if (mBtnRotate != null) {
            mBtnRotate.setOnClickListener(v -> pressRotate());
        }
        if (mBtnEscape != null) {
            mBtnEscape.setOnClickListener(v -> pressEscape());
        }
        if (mBtnKeyboard != null) {
            mBtnKeyboard.setOnClickListener(v -> toggleKeyboard());
        }
        if (mBtnCollapse != null) {
            mBtnCollapse.setOnClickListener(v -> toggleCollapse());
        }

        // Drag handle touch listener for vertical repositioning
        if (mDragHandle != null) {
            mDragHandle.setOnTouchListener((v, event) -> {
                switch (event.getActionMasked()) {
                    case MotionEvent.ACTION_DOWN:
                        mInitialTouchY = event.getRawY();
                        mInitialTranslationY = getTranslationY();
                        mIsDragging = false;
                        return true;

                    case MotionEvent.ACTION_MOVE:
                        float deltaY = event.getRawY() - mInitialTouchY;
                        if (!mIsDragging && Math.abs(deltaY) > mTouchSlop) {
                            mIsDragging = true;
                        }
                        if (mIsDragging) {
                            float newY = mInitialTranslationY + deltaY;
                            ViewGroup parent = (ViewGroup) getParent();
                            if (parent != null) {
                                float maxY = parent.getHeight() - getHeight();
                                newY = Math.max(0, Math.min(newY, maxY));
                            }
                            setTranslationY(newY);
                        }
                        return true;

                    case MotionEvent.ACTION_UP:
                    case MotionEvent.ACTION_CANCEL:
                        if (!mIsDragging) {
                            toggleCollapse();
                        }
                        mIsDragging = false;
                        return true;
                }
                return false;
            });
        }
    }

    public void bindTouchCharInput(@Nullable TouchCharInput input) {
        this.mBoundCharInput = input;
    }

    // --- Action Methods matching Oracle contract ---

    public boolean pressPause() {
        mIsPaused = !mIsPaused;
        if (mBtnPause != null) {
            mBtnPause.setImageResource(mIsPaused ? R.drawable.ic_hud_play : R.drawable.ic_hud_pause);
            mBtnPause.setSelected(mIsPaused);
        }
        CallbackBridge.sendKeyPress(KEYCODE_SPACE);
        return mIsPaused;
    }

    public int cycleSpeed() {
        mCurrentSpeedIndex = (mCurrentSpeedIndex + 1) % SPEED_KEYCODES.length;
        int keycode = SPEED_KEYCODES[mCurrentSpeedIndex];
        if (mBtnSpeed != null) {
            mBtnSpeed.setText(SPEED_LABELS[mCurrentSpeedIndex]);
        }
        CallbackBridge.sendKeyPress(keycode);
        return keycode;
    }

    public void pressRotate() {
        CallbackBridge.sendKeyPress(KEYCODE_R);
    }

    public void pressEscape() {
        CallbackBridge.sendKeyPress(KEYCODE_ESCAPE);
    }

    public boolean toggleKeyboard() {
        mIsKeyboardVisible = !mIsKeyboardVisible;
        if (mBtnKeyboard != null) {
            mBtnKeyboard.setSelected(mIsKeyboardVisible);
        }
        if (mBoundCharInput != null) {
            mBoundCharInput.switchKeyboardState();
        } else {
            GameActivity.switchKeyboardState(false);
        }
        return mIsKeyboardVisible;
    }

    public boolean toggleCollapse() {
        mIsCollapsed = !mIsCollapsed;
        if (mActionsContainer == null) return mIsCollapsed;

        if (mIsCollapsed) {
            // Animate collapse: slide actions out, then hide
            mActionsContainer.animate()
                .alpha(0f)
                .translationX(mActionsContainer.getWidth())
                .setDuration(180)
                .setInterpolator(new AccelerateInterpolator())
                .setListener(new AnimatorListenerAdapter() {
                    @Override
                    public void onAnimationEnd(Animator animation) {
                        mActionsContainer.setVisibility(View.GONE);
                    }
                })
                .start();
            if (mBtnCollapse != null) {
                mBtnCollapse.setImageResource(R.drawable.ic_hud_chevron_expand);
            }
        } else {
            // Animate expand: show, then slide in
            mActionsContainer.setVisibility(View.VISIBLE);
            mActionsContainer.setAlpha(0f);
            mActionsContainer.setTranslationX(mActionsContainer.getWidth());
            mActionsContainer.animate()
                .alpha(1f)
                .translationX(0f)
                .setDuration(220)
                .setInterpolator(new DecelerateInterpolator())
                .setListener(null)
                .start();
            if (mBtnCollapse != null) {
                mBtnCollapse.setImageResource(R.drawable.ic_hud_chevron_collapse);
            }
        }
        return mIsCollapsed;
    }

    // --- State Getters ---

    public boolean isCollapsed() {
        return mIsCollapsed;
    }

    public boolean isPaused() {
        return mIsPaused;
    }

    public int getCurrentSpeedIndex() {
        return mCurrentSpeedIndex;
    }

    public boolean isKeyboardVisible() {
        return mIsKeyboardVisible;
    }

    public void setKeyboardVisible(boolean visible) {
        this.mIsKeyboardVisible = visible;
        if (mBtnKeyboard != null) {
            mBtnKeyboard.setSelected(visible);
        }
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        // Essential: consume touch events on HUD so they do NOT leak to underlying GameView
        return true;
    }
}
