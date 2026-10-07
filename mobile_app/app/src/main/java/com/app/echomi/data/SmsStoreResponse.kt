package com.app.echomi.data

data class SmsStoreResponse(
    val success: Boolean,
    val message: String,
    val count: Int,
    val callSid: String,
    val storageType: String,
    val alreadyExists: Boolean = false
)