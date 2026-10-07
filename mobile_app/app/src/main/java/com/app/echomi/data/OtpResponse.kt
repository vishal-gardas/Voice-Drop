package com.app.echomi.data

data class OtpResponse(
    val status: String,
    val otpId: String? = null,
    val otp: String? = null,
    val sender: String? = null,
    val orderId: String? = null,
    val error: String? = null
)
