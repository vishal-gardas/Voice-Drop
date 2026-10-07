package com.app.echomi.Services

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import android.util.Log
import com.google.firebase.auth.FirebaseAuth

class SmsReceiver : BroadcastReceiver() {
    companion object {
        private const val TAG = "SmsReceiver"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Telephony.Sms.Intents.SMS_RECEIVED_ACTION) {
            val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
            if (messages.isNullOrEmpty()) return

            // Just log the SMS receipt - no OTP processing
            val smsBody = StringBuilder()
            var originatingAddress = ""
            for (message in messages) {
                smsBody.append(message.messageBody)
                if (originatingAddress.isEmpty()) {
                    originatingAddress = message.originatingAddress ?: ""
                }
            }

            val fullBody = smsBody.toString()
            Log.d(TAG, "📩 New SMS received from $originatingAddress: ${fullBody.take(50)}...")

            // No longer sending to backend automatically
            // Backend will request SMS when needed via FCM
        }
    }
}