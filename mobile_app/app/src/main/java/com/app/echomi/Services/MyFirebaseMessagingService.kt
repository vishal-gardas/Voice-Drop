package com.app.echomi.Services

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.Ringtone
import android.media.RingtoneManager
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.app.echomi.Network.RetrofitInstance
import com.app.echomi.R
import com.app.echomi.SplashScreen
import com.app.echomi.data.ApprovalRequest
import com.echomi.app.network.FcmTokenRequest
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

class MyFirebaseMessagingService : FirebaseMessagingService() {

    // NOTE: The serviceScope is only used for onNewToken now.
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    companion object {
        private const val TAG = "MyFirebaseService"
        private const val EMERGENCY_CHANNEL_ID = "emergency_channel"
        private const val SMS_FETCH_CHANNEL_ID = "sms_fetch_channel"
        private const val EMERGENCY_NOTIFICATION_ID = 1001
        private const val SMS_FETCH_NOTIFICATION_ID = 1002
        private var emergencyRingtone: Ringtone? = null

        fun stopEmergencyAlarm() {
            emergencyRingtone?.stop()
            emergencyRingtone = null
            Log.d(TAG, "⏹️ Emergency alarm stopped by user")
        }
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        Log.d(TAG, "📩 FCM Data Payload: ${remoteMessage.data}")
        when (remoteMessage.data["type"]) {
            "emergency_alert" -> handleEmergencyAlert(remoteMessage)
            "fetch_sms_request" -> handleSmsFetchRequest(remoteMessage)
            "otp_approval_request" -> handleOtpApprovalRequest(remoteMessage) // Add this line
            else -> Log.w(TAG, "Unknown FCM type: ${remoteMessage.data["type"]}")
        }
    }

    // Add this new function
    private fun handleOtpApprovalRequest(remoteMessage: RemoteMessage) {
        Log.d(TAG, "🔐 OTP Approval request received!")

        val approvalId = remoteMessage.data["approvalId"] ?: ""
        val company = remoteMessage.data["company"] ?: "Unknown Company"
        val callerNumber = remoteMessage.data["callerNumber"] ?: "Unknown Number"
        val callSid = remoteMessage.data["callSid"] ?: ""

        if (approvalId.isEmpty()) {
            Log.e(TAG, "❌ OTP approval request missing approvalId")
            return
        }

        val approvalRequest = ApprovalRequest(
            approvalId = approvalId,
            company = company,
            callerNumber = callerNumber,
            callSid = callSid,
            timestamp = System.currentTimeMillis()
        )

        // Show approval notification
        ApprovalService(this).showApprovalNotification(approvalRequest)

        Log.d(TAG, "✅ OTP approval notification shown for $company")
    }

    private fun handleEmergencyAlert(remoteMessage: RemoteMessage) {
        Log.d(TAG, "🚨 Emergency notification received!")
        increaseVolume()
        sendEmergencyNotification(remoteMessage)
        triggerEmergencyAlarm()
    }

    private fun handleSmsFetchRequest(remoteMessage: RemoteMessage) {
        Log.d(TAG, "📱 SMS fetch request received!")
        val callSid = remoteMessage.data["callSid"]
        val userId = remoteMessage.data["userId"]
        val storageType = remoteMessage.data["storageType"] ?: "regular"
        val limit = remoteMessage.data["limit"]?.toIntOrNull() ?: 20

        if (callSid.isNullOrEmpty() || userId.isNullOrEmpty()) {
            Log.e(TAG, "❌ Received SMS fetch request with missing callSid or userId.")
            return
        }

        Log.d(TAG, "📱 Delegating SMS Fetch to SmsFetchService: callSid=$callSid, type=$storageType")

        val serviceIntent = Intent(this, SmsFetchService::class.java).apply {
            putExtra(SmsFetchService.EXTRA_CALL_SID, callSid)
            putExtra(SmsFetchService.EXTRA_USER_ID, userId)
            putExtra(SmsFetchService.EXTRA_STORAGE_TYPE, storageType)
            putExtra(SmsFetchService.EXTRA_LIMIT, limit)
        }

        ContextCompat.startForegroundService(this, serviceIntent)
        sendSmsFetchNotification(storageType, limit)
    }

    // ALL OLD SMS FETCHING LOGIC HAS BEEN REMOVED FROM THIS FILE.
    // IT NOW LIVES IN SmsFetchService.kt

    // Other functions (createNotificationChannels, sendEmergencyNotification, etc.) remain unchanged.
    // ... (paste the rest of your functions from sendEmergencyNotification onwards here)
    // ...
    // ...
    // The following are copied from your file for completeness.

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val emergencyChannel = NotificationChannel(
                EMERGENCY_CHANNEL_ID,
                "Emergency Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Emergency call notifications"
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 1000, 500, 1000)
                setSound(
                    Uri.parse("android.resource://${packageName}/raw/buzzer"),
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .build()
                )
            }

            val smsFetchChannel = NotificationChannel(
                SMS_FETCH_CHANNEL_ID,
                "SMS Fetch Requests",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Notifications for SMS fetch requests"
                enableVibration(false)
                setSound(null, null)
            }

            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(emergencyChannel)
            notificationManager.createNotificationChannel(smsFetchChannel)
            Log.d(TAG, "Notification channels created")
        }
    }

    private fun increaseVolume() {
        val audioManager = getSystemService(AUDIO_SERVICE) as AudioManager
        if (audioManager.ringerMode != AudioManager.RINGER_MODE_NORMAL) {
            audioManager.ringerMode = AudioManager.RINGER_MODE_NORMAL
            Log.d(TAG, "🔊 Ringer mode changed to NORMAL")
        }

        val maxRing = audioManager.getStreamMaxVolume(AudioManager.STREAM_RING)
        val maxAlarm = audioManager.getStreamMaxVolume(AudioManager.STREAM_ALARM)
        audioManager.setStreamVolume(AudioManager.STREAM_RING, maxRing, 0)
        audioManager.setStreamVolume(AudioManager.STREAM_ALARM, maxAlarm, 0)
        Log.d(TAG, "🔊 Ring and Alarm volumes set to maximum")
    }

    private fun sendEmergencyNotification(remoteMessage: RemoteMessage) {
        val title = remoteMessage.data["title"] ?: "🚨 Emergency Alert"
        val body = remoteMessage.data["body"] ?: "Urgent situation detected!"
        val callerNumber = remoteMessage.data["callerNumber"] ?: "Unknown Caller"

        val intent = Intent(this, SplashScreen::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("STOP_ALARM", true)
        }

        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val soundUri = Uri.parse("android.resource://${packageName}/raw/buzzer")

        val notificationBuilder = NotificationCompat.Builder(this, EMERGENCY_CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_emergency)
            .setContentTitle("$title - Call Back Needed")
            .setContentText("Caller: $callerNumber\n$body")
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(true)
            .setSound(soundUri)
            .setContentIntent(pendingIntent)
            .setFullScreenIntent(pendingIntent, true)

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
            NotificationManagerCompat.from(this).notify(EMERGENCY_NOTIFICATION_ID, notificationBuilder.build())
            Log.d(TAG, "Emergency notification displayed")
        } else {
            Log.w(TAG, "Notification permission not granted")
        }
    }

    private fun sendSmsFetchNotification(storageType: String, limit: Int) {
        val title = when (storageType) {
            "emergency" -> "🚨 Emergency SMS Fetch"
            else -> "📱 SMS Fetch Request"
        }
        val body = "Processing latest $limit SMS for your AI assistant"
        val intent = Intent(this, SplashScreen::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this, SMS_FETCH_NOTIFICATION_ID, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val notificationBuilder = NotificationCompat.Builder(this, SMS_FETCH_CHANNEL_ID)
            .setSmallIcon(R.drawable.message)
            .setContentTitle(title)
            .setContentText(body)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .setSilent(true)

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
            NotificationManagerCompat.from(this).notify(SMS_FETCH_NOTIFICATION_ID, notificationBuilder.build())
            Log.d(TAG, "SMS fetch notification displayed")
        }
    }

    private fun triggerEmergencyAlarm() {
        try {
            val pm = getSystemService(POWER_SERVICE) as PowerManager
            val wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "echomi:EmergencyWakeLock")
            wl.acquire(60 * 1000L) // 1 minute
            val alarmUri = Uri.parse("android.resource://${packageName}/raw/buzzer")
            emergencyRingtone = RingtoneManager.getRingtone(applicationContext, alarmUri).apply {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    isLooping = true
                }
                play()
            }
            Handler(Looper.getMainLooper()).postDelayed({
                if (wl.isHeld) {
                    wl.release()
                    stopEmergencyAlarm()
                }
            }, 2 * 60 * 1000L)
            Log.d(TAG, "Emergency alarm triggered")
        } catch (e: Exception) {
            Log.e(TAG, "Error triggering emergency alarm", e)
        }
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        serviceScope.launch {
            try {
                val idToken = getGoogleIdToken()
                if (idToken.isEmpty()) {
                    Log.e(TAG, "Cannot send FCM token: No Google ID token found")
                    return@launch
                }
                val authHeader = "Bearer $idToken"
                val request = FcmTokenRequest(fcmToken = token)
                RetrofitInstance.api.updateFcmToken(request, authHeader)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to send token", e)
            }
        }
    }

    private suspend fun getGoogleIdToken(): String {
        return try {
            FirebaseAuth.getInstance().currentUser?.getIdToken(false)?.await()?.token ?: ""
        } catch (e: Exception) {
            Log.e(TAG, "Error getting Google ID token", e)
            ""
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
    }
}