package com.app.echomi.Services

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.app.echomi.ApprovalActivity
import com.app.echomi.R
import com.app.echomi.data.ApprovalRequest
import com.app.echomi.data.ApprovalResponse
import com.app.echomi.Network.RetrofitInstance
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ApprovalService(private val context: Context) {

    companion object {
        private const val TAG = "ApprovalService" // Moved TAG inside companion object
        private const val CHANNEL_ID = "otp_approval_channel"
        private const val NOTIFICATION_ID = 2001
        private const val ACTION_APPROVE = "ACTION_APPROVE"
        private const val ACTION_DENY = "ACTION_DENY"
        private const val EXTRA_APPROVAL_ID = "extra_approval_id"
        private const val EXTRA_COMPANY = "extra_company"
        private const val EXTRA_CALLER_NUMBER = "extra_caller_number"
    }

    init {
        createNotificationChannel()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "OTP Approval Requests",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifications for OTP sharing approval requests"
                enableVibration(true)
                setShowBadge(true)
            }

            val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    fun showApprovalNotification(approvalRequest: ApprovalRequest) {
        // Check notification permission first
        if (!hasNotificationPermission()) {
            Log.w(TAG, "Cannot show approval notification: POST_NOTIFICATIONS permission denied")
            return
        }

        // Create intent for ApprovalActivity
        val intent = Intent(context, ApprovalActivity::class.java).apply {
            putExtra("approvalId", approvalRequest.approvalId)
            putExtra("company", approvalRequest.company)
            putExtra("callerNumber", approvalRequest.callerNumber)
            putExtra("callSid", approvalRequest.callSid)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }

        val pendingIntent = PendingIntent.getActivity(
            context,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // Create approve action
        val approveIntent = Intent(context, ApprovalReceiver::class.java).apply {
            action = ACTION_APPROVE
            putExtra(EXTRA_APPROVAL_ID, approvalRequest.approvalId)
            putExtra(EXTRA_COMPANY, approvalRequest.company)
        }

        val approvePendingIntent = PendingIntent.getBroadcast(
            context,
            approvalRequest.approvalId.hashCode(),
            approveIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // Create deny action
        val denyIntent = Intent(context, ApprovalReceiver::class.java).apply {
            action = ACTION_DENY
            putExtra(EXTRA_APPROVAL_ID, approvalRequest.approvalId)
            putExtra(EXTRA_COMPANY, approvalRequest.company)
        }

        val denyPendingIntent = PendingIntent.getBroadcast(
            context,
            approvalRequest.approvalId.hashCode() + 1,
            denyIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        try {
            // Build notification
            val notification = NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_shield)
                .setContentTitle("OTP Sharing Request")
                .setContentText("${approvalRequest.company} delivery needs OTP access")
                .setStyle(NotificationCompat.BigTextStyle()
                    .bigText("A delivery person from ${approvalRequest.company} is requesting OTP verification. Caller: ${approvalRequest.callerNumber}"))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setContentIntent(pendingIntent)
                .addAction(
                    R.drawable.ic_check,
                    "Approve",
                    approvePendingIntent
                )
                .addAction(
                    R.drawable.ic_close,
                    "Deny",
                    denyPendingIntent
                )
                .setAutoCancel(true)
                .setTimeoutAfter(60000) // Auto-cancel after 1 minute
                .build()

            val notificationManager = ContextCompat.getSystemService(context, NotificationManager::class.java)
            notificationManager?.notify(NOTIFICATION_ID, notification)
            Log.d(TAG, "Approval notification shown for ${approvalRequest.company}")

        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException when showing approval notification", e)
        } catch (e: Exception) {
            Log.e(TAG, "Error showing approval notification", e)
        }
    }

    private fun hasNotificationPermission(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
        } else {
            // Permission is granted by default on older Android versions
            true
        }
    }

    suspend fun sendApprovalResponse(approvalId: String, approved: Boolean): Boolean {
        return try {
            val response = RetrofitInstance.api.approveOtpSharing(
                ApprovalResponse(approvalId, approved)
            )
            response.isSuccessful && response.body()?.success == true
        } catch (e: Exception) {
            false
        }
    }

    fun sendApprovalResponseAsync(approvalId: String, approved: Boolean) {
        CoroutineScope(Dispatchers.IO).launch {
            val success = sendApprovalResponse(approvalId, approved)
            withContext(Dispatchers.Main) {
                if (success) {
                    Log.d(TAG, "Approval response sent successfully")
                } else {
                    Log.e(TAG, "Failed to send approval response")
                }
            }
        }
    }
}