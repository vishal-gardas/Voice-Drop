package com.app.echomi.data

data class TranscriptMessage(
    val speaker: String, // "caller" or "ai"
    val text: String,
    val timestamp: String
)