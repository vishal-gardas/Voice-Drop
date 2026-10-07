package com.app.echomi.data

// This represents one turn in a conversation
data class TranscriptEntry(
    val role: String,
    val parts: List<String>
)