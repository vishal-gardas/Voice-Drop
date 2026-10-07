package com.app.echomi.data

import com.google.gson.annotations.SerializedName

data class ApprovalRequest(
    @SerializedName("approvalId") val approvalId: String,
    @SerializedName("company") val company: String,
    @SerializedName("callerNumber") val callerNumber: String,
    @SerializedName("callSid") val callSid: String,
    @SerializedName("timestamp") val timestamp: Long
)

data class ApprovalResponse(
    @SerializedName("approvalId") val approvalId: String,
    @SerializedName("approved") val approved: Boolean,
    @SerializedName("userId") val userId: String? = null
)

data class ApprovalStatus(
    @SerializedName("success") val success: Boolean,
    @SerializedName("message") val message: String? = null,
    @SerializedName("action") val action: String? = null
)