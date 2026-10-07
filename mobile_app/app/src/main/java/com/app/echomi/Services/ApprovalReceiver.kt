package com.app.echomi.Services

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.util.Log
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.app.echomi.R

class ApprovalReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "ApprovalReceiver"
    }

    override fun onReceive(context: Context, intent: Intent) {
        val approvalId = intent.getStringExtra("extra_approval_id")
        val company = intent.getStringExtra("extra_company")

        if (approvalId == null || company == null) {
            Log.e(TAG, "Missing approval ID or company")
            return
        }

        when (intent.action) {
            "ACTION_APPROVE" -> {
                Log.d(TAG, "User approved OTP sharing for $company")
                // Send approval to backend
                ApprovalService(context).sendApprovalResponseAsync(approvalId, true)

                // Show confirmation
                showConfirmationNotification(context, "OTP Sharing Approved", "OTP will be shared with $company delivery")
            }

            "ACTION_DENY" -> {
                Log.d(TAG, "User denied OTP sharing for $company")
                // Send denial to backend
                ApprovalService(context).sendApprovalResponseAsync(approvalId, false)

                // Show confirmation
                showConfirmationNotification(context, "OTP Sharing Denied", "OTP will not be shared with $company")
            }
        }

        // Dismiss the original notification - with permission check
        dismissOriginalNotification(context)
    }

    private fun showConfirmationNotification(context: Context, title: String, message: String) {
        // Check if we have notification permission
        if (!hasNotificationPermission(context)) {
            Log.w(TAG, "Cannot show confirmation notification: Permission denied")
            return
        }

        try {
            val notification = NotificationCompat.Builder(context, "otp_approval_channel")
                .setSmallIcon(R.drawable.ic_check)
                .setContentTitle(title)
                .setContentText(message)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true)
                .build()

            NotificationManagerCompat.from(context).notify(2002, notification)
            Log.d(TAG, "Confirmation notification shown: $title")
        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException when showing confirmation notification", e)
        } catch (e: Exception) {
            Log.e(TAG, "Error showing confirmation notification", e)
        }
    }

    private fun dismissOriginalNotification(context: Context) {
        // Check if we have notification permission
        if (!hasNotificationPermission(context)) {
            Log.w(TAG, "Cannot dismiss original notification: Permission denied")
            return
        }

        try {
            NotificationManagerCompat.from(context).cancel(2001)
            Log.d(TAG, "Original notification dismissed")
        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException when dismissing notification", e)
        } catch (e: Exception) {
            Log.e(TAG, "Error dismissing notification", e)
        }
    }

    private fun hasNotificationPermission(context: Context): Boolean {
        return if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
        } else {
            // Permission is granted by default on older Android versions
            true
        }
    }
}