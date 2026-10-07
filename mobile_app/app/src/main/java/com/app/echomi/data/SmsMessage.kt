package com.app.echomi.data

import java.util.Date

data class SmsMessage(
    val phoneNumber: String,
    val message: String,
    val sender: String,
    val timestamp: Date,
    val smsType: String // "inbox" or "sent"
)