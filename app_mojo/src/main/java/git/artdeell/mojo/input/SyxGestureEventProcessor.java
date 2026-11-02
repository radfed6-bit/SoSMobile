package git.artdeell.mojo.input;

import android.os.Handler;
import android.os.Looper;
import android.view.MotionEvent;

import git.artdeell.mojo.CallbackBridge;
import git.artdeell.mojo.game.GameView;
import git.artdeell.mojo.game.TouchEventProcessor;

/**
 * Native touch gesture event processor for Songs of Syx.
 * Replaces Minecraft virtual button layouts with intuitive multi-touch gestures:
 * - Single-finger tap: Left Mouse Button click (button 0)
 * - Single-finger drag: Left Mouse Button hold (box selection, placement)
 * - Long-press (> 350ms): Right Mouse Button click (button 1, cancel / deselect)
 * - Two-finger tap: Right Mouse Button click (button 1)
 * - Two-finger drag: Middle Mouse Button hold (button 2, camera panning)
 * - Two-finger pinch: Mouse scroll wheel (zoom in / zoom out)
 */
public class SyxGestureEventProcessor extends TouchEventProcessor {

    public static final float TOUCH_SLOP_PX = 10.0f;
    public static final long TAP_MAX_DURATION_MS = 250L;
    public static final long LONG_PRESS_TIMEOUT_MS = 350L;
    public static final float PINCH_MIN_SCALE_DELTA = 0.05f;
    public static final float PINCH_MIN_DISTANCE_PX = 20.0f;

    public enum GestureState {
        IDLE,
        PENDING_TAP,
        DRAGGING_LEFT,
        PENDING_TWO_FINGER,
        PANNING_TWO_FINGER,
        PINCHING_ZOOM,
        MULTI_TOUCH_IGNORE
    }

    private GestureState mState = GestureState.IDLE;
    private final Handler mHandler = new Handler(Looper.getMainLooper());

    // Single touch tracking
    private int mPointer0Id = -1;
    private float mStartX, mStartY;
    private float mCurrentX, mCurrentY;
    private long mDownTime;
    private boolean mLongPressFired = false;

    // Two-finger touch tracking
    private int mPointer1Id = -1;
    private float mInitialPinchDist = -1f;
    private float mInitialMidX, mInitialMidY;
    private long mTwoFingerDownTime;
    private boolean mTwoFingerTapFired = false;

    // Active gesture flags
    private boolean mIsDraggingLeft = false;
    private boolean mIsTwoFingerPanning = false;

    private final Runnable mLongPressRunnable = new Runnable() {
        @Override
        public void run() {
            if (mState == GestureState.PENDING_TAP && !mIsDraggingLeft) {
                float dist = (float) Math.hypot(mCurrentX - mStartX, mCurrentY - mStartY);
                if (dist <= TOUCH_SLOP_PX) {
                    mLongPressFired = true;
                    // Trigger Right Click (cancel / context menu)
                    sendTouchCoordinates(mCurrentX, mCurrentY);
                    CallbackBridge.sendMouseButton(MotionEvent.BUTTON_SECONDARY, true);
                    CallbackBridge.sendMouseButton(MotionEvent.BUTTON_SECONDARY, false);
                }
            }
        }
    };

    public SyxGestureEventProcessor(GameView hostView) {
        super(hostView);
    }

    @Override
    public boolean processTouchEvent(MotionEvent event) {
        if (event == null) return false;
        int action = event.getActionMasked();

        switch (action) {
            case MotionEvent.ACTION_DOWN:
                handleActionDown(event);
                break;

            case MotionEvent.ACTION_POINTER_DOWN:
                handleActionPointerDown(event);
                break;

            case MotionEvent.ACTION_MOVE:
                handleActionMove(event);
                break;

            case MotionEvent.ACTION_POINTER_UP:
                handleActionPointerUp(event);
                break;

            case MotionEvent.ACTION_UP:
                handleActionUp(event);
                break;

            case MotionEvent.ACTION_CANCEL:
                handleActionCancel(event);
                break;
        }
        return true;
    }

    private void handleActionDown(MotionEvent event) {
        cancelLongPressTimer();
        mPointer0Id = event.getPointerId(0);
        mStartX = event.getX(0);
        mStartY = event.getY(0);
        mCurrentX = mStartX;
        mCurrentY = mStartY;
        mDownTime = event.getEventTime();
        mLongPressFired = false;
        mIsDraggingLeft = false;

        sendTouchCoordinates(mStartX, mStartY);
        mState = GestureState.PENDING_TAP;
        mHandler.postDelayed(mLongPressRunnable, LONG_PRESS_TIMEOUT_MS);
    }

    private void handleActionPointerDown(MotionEvent event) {
        cancelLongPressTimer();

        if (mIsDraggingLeft) {
            CallbackBridge.sendMouseButton(MotionEvent.BUTTON_PRIMARY, false);
            mIsDraggingLeft = false;
        }

        int pointerCount = event.getPointerCount();
        if (pointerCount == 2) {
            mPointer0Id = event.getPointerId(0);
            mPointer1Id = event.getPointerId(1);
            int idx0 = event.findPointerIndex(mPointer0Id);
            int idx1 = event.findPointerIndex(mPointer1Id);

            if (idx0 != -1 && idx1 != -1) {
                float x0 = event.getX(idx0);
                float y0 = event.getY(idx0);
                float x1 = event.getX(idx1);
                float y1 = event.getY(idx1);

                mInitialPinchDist = (float) Math.hypot(x0 - x1, y0 - y1);
                mInitialMidX = (x0 + x1) / 2.0f;
                mInitialMidY = (y0 + y1) / 2.0f;
                mTwoFingerDownTime = event.getEventTime();
                mTwoFingerTapFired = false;
                mState = GestureState.PENDING_TWO_FINGER;
            }
        } else if (pointerCount >= 3) {
            if (mIsTwoFingerPanning) {
                CallbackBridge.sendMouseButton(MotionEvent.BUTTON_TERTIARY, false);
                mIsTwoFingerPanning = false;
            }
            mState = GestureState.MULTI_TOUCH_IGNORE;
        }
    }

    private void handleActionMove(MotionEvent event) {
        int pointerCount = event.getPointerCount();

        if (mState == GestureState.MULTI_TOUCH_IGNORE) {
            return;
        }

        if (pointerCount == 1 && (mState == GestureState.PENDING_TAP || mState == GestureState.DRAGGING_LEFT)) {
            int idx = event.findPointerIndex(mPointer0Id);
            if (idx == -1) idx = 0;
            mCurrentX = event.getX(idx);
            mCurrentY = event.getY(idx);

            float dist = (float) Math.hypot(mCurrentX - mStartX, mCurrentY - mStartY);

            if (!mIsDraggingLeft) {
                if (dist > TOUCH_SLOP_PX) {
                    cancelLongPressTimer();
                    mIsDraggingLeft = true;
                    mState = GestureState.DRAGGING_LEFT;
                    sendTouchCoordinates(mCurrentX, mCurrentY);
                    CallbackBridge.sendMouseButton(MotionEvent.BUTTON_PRIMARY, true);
                }
            } else {
                sendTouchCoordinates(mCurrentX, mCurrentY);
            }
        } else if (pointerCount == 2) {
            int idx0 = event.findPointerIndex(mPointer0Id);
            int idx1 = event.findPointerIndex(mPointer1Id);
            if (idx0 == -1 || idx1 == -1) return;

            float x0 = event.getX(idx0);
            float y0 = event.getY(idx0);
            float x1 = event.getX(idx1);
            float y1 = event.getY(idx1);

            float currDist = (float) Math.hypot(x0 - x1, y0 - y1);
            float midX = (x0 + x1) / 2.0f;
            float midY = (y0 + y1) / 2.0f;

            if (mInitialPinchDist > PINCH_MIN_DISTANCE_PX && currDist > PINCH_MIN_DISTANCE_PX) {
                float scale = currDist / mInitialPinchDist;

                if (scale > (1.0f + PINCH_MIN_SCALE_DELTA)) {
                    // Pinch Spread -> Zoom In
                    if (mIsTwoFingerPanning) {
                        CallbackBridge.sendMouseButton(MotionEvent.BUTTON_TERTIARY, false);
                        mIsTwoFingerPanning = false;
                    }
                    mState = GestureState.PINCHING_ZOOM;
                    CallbackBridge.sendScroll(0.0, 1.0);
                    mInitialPinchDist = currDist;
                    return;
                } else if (scale < (1.0f - PINCH_MIN_SCALE_DELTA)) {
                    // Pinch Contract -> Zoom Out
                    if (mIsTwoFingerPanning) {
                        CallbackBridge.sendMouseButton(MotionEvent.BUTTON_TERTIARY, false);
                        mIsTwoFingerPanning = false;
                    }
                    mState = GestureState.PINCHING_ZOOM;
                    CallbackBridge.sendScroll(0.0, -1.0);
                    mInitialPinchDist = currDist;
                    return;
                }
            }

            // If not actively pinching, handle camera panning
            if (mState != GestureState.PINCHING_ZOOM) {
                float midDist = (float) Math.hypot(midX - mInitialMidX, midY - mInitialMidY);
                if (midDist > TOUCH_SLOP_PX || mIsTwoFingerPanning) {
                    if (!mIsTwoFingerPanning) {
                        mIsTwoFingerPanning = true;
                        mState = GestureState.PANNING_TWO_FINGER;
                        sendTouchCoordinates(midX, midY);
                        CallbackBridge.sendMouseButton(MotionEvent.BUTTON_TERTIARY, true);
                    } else {
                        sendTouchCoordinates(midX, midY);
                    }
                }
            }
        }
    }

    private void handleActionPointerUp(MotionEvent event) {
        int pointerCount = event.getPointerCount();

        if (pointerCount == 2 && mState == GestureState.PENDING_TWO_FINGER && !mTwoFingerTapFired) {
            long duration = event.getEventTime() - mTwoFingerDownTime;
            if (duration <= TAP_MAX_DURATION_MS) {
                // Two-finger tap -> Right Click
                sendTouchCoordinates(mInitialMidX, mInitialMidY);
                CallbackBridge.sendMouseButton(MotionEvent.BUTTON_SECONDARY, true);
                CallbackBridge.sendMouseButton(MotionEvent.BUTTON_SECONDARY, false);
                mTwoFingerTapFired = true;
            }
        }

        if (mIsTwoFingerPanning) {
            CallbackBridge.sendMouseButton(MotionEvent.BUTTON_TERTIARY, false);
            mIsTwoFingerPanning = false;
        }

        mInitialPinchDist = -1f;
    }

    private void handleActionUp(MotionEvent event) {
        cancelLongPressTimer();

        if (mIsDraggingLeft) {
            int idx = event.findPointerIndex(mPointer0Id);
            if (idx == -1) idx = 0;
            sendTouchCoordinates(event.getX(idx), event.getY(idx));
            CallbackBridge.sendMouseButton(MotionEvent.BUTTON_PRIMARY, false);
            mIsDraggingLeft = false;
        } else if (mState == GestureState.PENDING_TWO_FINGER && !mTwoFingerTapFired) {
            // Handle synthesized 2-finger UP events where ACTION_POINTER_UP wasn't received
            long duration = event.getEventTime() - mTwoFingerDownTime;
            if (duration <= TAP_MAX_DURATION_MS) {
                sendTouchCoordinates(mInitialMidX, mInitialMidY);
                CallbackBridge.sendMouseButton(MotionEvent.BUTTON_SECONDARY, true);
                CallbackBridge.sendMouseButton(MotionEvent.BUTTON_SECONDARY, false);
                mTwoFingerTapFired = true;
            }
        } else if (mState == GestureState.PENDING_TAP && !mLongPressFired) {
            int idx = event.findPointerIndex(mPointer0Id);
            if (idx == -1) idx = 0;
            float endX = event.getX(idx);
            float endY = event.getY(idx);
            float dist = (float) Math.hypot(endX - mStartX, endY - mStartY);
            long duration = event.getEventTime() - mDownTime;

            if (dist <= TOUCH_SLOP_PX) {
                if (duration >= LONG_PRESS_TIMEOUT_MS) {
                    // Long press -> Right Click
                    sendTouchCoordinates(endX, endY);
                    CallbackBridge.sendMouseButton(MotionEvent.BUTTON_SECONDARY, true);
                    CallbackBridge.sendMouseButton(MotionEvent.BUTTON_SECONDARY, false);
                } else if (duration <= TAP_MAX_DURATION_MS) {
                    // Single tap -> Left Click
                    sendTouchCoordinates(endX, endY);
                    CallbackBridge.sendMouseButton(MotionEvent.BUTTON_PRIMARY, true);
                    CallbackBridge.sendMouseButton(MotionEvent.BUTTON_PRIMARY, false);
                }
            }
        }

        if (mIsTwoFingerPanning) {
            CallbackBridge.sendMouseButton(MotionEvent.BUTTON_TERTIARY, false);
            mIsTwoFingerPanning = false;
        }

        resetState();
    }

    private void handleActionCancel(MotionEvent event) {
        cancelLongPressTimer();

        if (mIsDraggingLeft) {
            CallbackBridge.sendMouseButton(MotionEvent.BUTTON_PRIMARY, false);
            mIsDraggingLeft = false;
        }
        if (mIsTwoFingerPanning) {
            CallbackBridge.sendMouseButton(MotionEvent.BUTTON_TERTIARY, false);
            mIsTwoFingerPanning = false;
        }

        resetState();
    }

    private void cancelLongPressTimer() {
        mHandler.removeCallbacks(mLongPressRunnable);
    }

    private void resetState() {
        cancelLongPressTimer();
        mState = GestureState.IDLE;
        mPointer0Id = -1;
        mPointer1Id = -1;
        mInitialPinchDist = -1f;
        mLongPressFired = false;
        mTwoFingerTapFired = false;
        mIsDraggingLeft = false;
        mIsTwoFingerPanning = false;
    }

    @Override
    public void prepareForSwitching() {
        super.prepareForSwitching();
        handleActionCancel(null);
    }

    public GestureState getState() {
        return mState;
    }

    public boolean isDraggingLeft() {
        return mIsDraggingLeft;
    }

    public boolean isTwoFingerPanning() {
        return mIsTwoFingerPanning;
    }
}
