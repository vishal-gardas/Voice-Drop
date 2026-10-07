package com.app.echomi.data

data class CallLog(
    val _id: String,
    val userId: String,
    val callerNumber: String,
    val callSid: String,
    val startTime: String,
    val duration: Int = 0,
    val summary: String? = null,
    val recordingUrl: String? = null,
    val transcript: List<TranscriptMessage> = emptyList()
)