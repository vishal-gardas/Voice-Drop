package com.app.echomi.data

data class SmsStoreRequest(
    val userId: String,
    val callSid: String,
    val smsMessages: List<SmsMessage>,
    val storageType: String = "regular" // "regular" or "emergency"
)