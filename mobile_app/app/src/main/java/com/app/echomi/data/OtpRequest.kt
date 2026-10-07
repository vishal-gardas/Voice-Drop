package com.app.echomi.data

data class OtpRequest(
    val firebaseUid: String,
    val sender: String,
    val otp: String,
    val orderId: String? = null
)
