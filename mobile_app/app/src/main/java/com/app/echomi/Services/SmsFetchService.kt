package com.app.echomi.Services

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.IBinder
import android.provider.Telephony
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.app.echomi.Network.RetrofitInstance
import com.app.echomi.R
import com.app.echomi.data.SmsMessage
import com.app.echomi.data.SmsStoreRequest
import com.google.firebase.auth.FirebaseAuth
import kotlinx.coroutines.*
import kotlinx.coroutines.tasks.await
import java.util.Date

class SmsFetchService : Service() {

    companion object {
        private const val TAG = "SmsFetchService"
        private const val NOTIFICATION_CHANNEL_ID = "sms_fetch_service_channel"
        private const val NOTIFICATION_ID = 1003 // Use a unique ID

        // Intent Extras
        const val EXTRA_CALL_SID = "EXTRA_CALL_SID"
        const val EXTRA_USER_ID = "EXTRA_USER_ID"
        const val EXTRA_STORAGE_TYPE = "EXTRA_STORAGE_TYPE"
        const val EXTRA_LIMIT = "EXTRA_LIMIT"
    }

    private val job = SupervisorJob()
    private val scope = CoroutineScope(Dispatchers.IO + job)

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val callSid = intent?.getStringExtra(EXTRA_CALL_SID) ?: ""
        val userId = intent?.getStringExtra(EXTRA_USER_ID) ?: ""
        val storageType = intent?.getStringExtra(EXTRA_STORAGE_TYPE) ?: "regular"
        val limit = intent?.getIntExtra(EXTRA_LIMIT, 20) ?: 20

        if (callSid.isEmpty() || userId.isEmpty()) {
            Log.e(TAG, "❌ Missing required intent data. Stopping service.")
            stopSelf()
            return START_NOT_STICKY
        }

        // Start the service in the foreground
        startForeground(NOTIFICATION_ID, createNotification(storageType))

        // Launch a coroutine to do the background work
        scope.launch {
            try {
                Log.d(TAG, "🚀 Starting SMS fetch work for callSid: $callSid")
                fetchAndSendSms(callSid, userId, storageType, limit)
            } finally {
                Log.d(TAG, "✅ Work finished. Stopping service.")
                stopSelf() // Stop the service when the work is done
            }
        }

        return START_NOT_STICKY
    }

    private suspend fun fetchAndSendSms(callSid: String, userId: String, storageType: String, limit: Int) {
        try {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_SMS) != PackageManager.PERMISSION_GRANTED) {
                Log.e(TAG, "❌ SMS read permission not granted.")
                return
            }

            val smsMessages = fetchLatestSms(limit)

            if (smsMessages.isNotEmpty()) {
                val idToken = getGoogleIdToken()
                if (idToken.isEmpty()) {
                    Log.e(TAG, "❌ Cannot send SMS data: User is not authenticated.")
                    return
                }
                val authHeader = "Bearer $idToken"

                val request = SmsStoreRequest(
                    userId = userId,
                    callSid = callSid,
                    smsMessages = smsMessages,
                    storageType = storageType
                )

                val response = RetrofitInstance.api.storeSmsMessages(authHeader, request)

                if (response.isSuccessful) {
                    val responseBody = response.body()
                    Log.d(TAG, "✅ Backend response: ${responseBody?.message}")

                    // ✅ Handle duplicate case
                    if (responseBody?.alreadyExists == true) {
                        Log.d(TAG, "📱 SMS already stored for this call. No new messages added.")
                    } else {
                        Log.d(TAG, "✅ Successfully stored ${smsMessages.size} SMS for call $callSid")
                    }
                } else {
                    Log.e(TAG, "❌ Failed to store SMS: ${response.code()} - ${response.errorBody()?.string()}")
                }
            } else {
                Log.w(TAG, "No SMS messages found to send.")
            }
        } catch (e: Exception) {
            if (e is CancellationException) {
                Log.w(TAG, "Coroutine was cancelled.")
            } else {
                Log.e(TAG, "Error during fetch/send SMS process", e)
            }
        }
    }

    private fun fetchLatestSms(limit: Int): List<SmsMessage> {
        // This function is identical to the one in your MyFirebaseMessagingService
        // You can move it here.
        return try {
            val smsList = mutableListOf<SmsMessage>()
            val uri = Telephony.Sms.CONTENT_URI
            val projection = arrayOf(Telephony.Sms.ADDRESS, Telephony.Sms.BODY, Telephony.Sms.DATE, Telephony.Sms.TYPE)
            val sortOrder = "${Telephony.Sms.DATE} DESC LIMIT $limit"

            contentResolver.query(uri, projection, null, null, sortOrder)?.use { cursor ->
                while (cursor.moveToNext() && smsList.size < limit) {
                    val address = cursor.getString(cursor.getColumnIndexOrThrow(Telephony.Sms.ADDRESS)) ?: ""
                    val body = cursor.getString(cursor.getColumnIndexOrThrow(Telephony.Sms.BODY)) ?: ""
                    val date = cursor.getLong(cursor.getColumnIndexOrThrow(Telephony.Sms.DATE))
                    val type = cursor.getInt(cursor.getColumnIndexOrThrow(Telephony.Sms.TYPE))
                    val smsType = if (type == Telephony.Sms.MESSAGE_TYPE_INBOX) "inbox" else "sent"

                    smsList.add(SmsMessage(address, body, address, Date(date), smsType))
                }
            }
            Log.d(TAG, "Fetched ${smsList.size} SMS messages")
            smsList
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching SMS from provider", e)
            emptyList()
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

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                NOTIFICATION_CHANNEL_ID,
                "SMS Fetching Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Handles fetching SMS in the background for your AI assistant."
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun createNotification(storageType: String): Notification {
        val title = if (storageType == "emergency") "Fetching Emergency SMS" else "Fetching Recent SMS"
        val text = "Processing messages for your AI assistant..."

        return NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(text)
            .setSmallIcon(R.drawable.message)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        job.cancel() // Cancel all coroutines when the service is destroyed
    }
}