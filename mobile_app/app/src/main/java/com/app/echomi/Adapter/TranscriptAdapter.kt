package com.app.echomi.Adapter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.app.echomi.R
import com.app.echomi.data.TranscriptMessage
import java.text.SimpleDateFormat
import java.util.*
import kotlin.text.isLowerCase
import kotlin.text.lowercase
import kotlin.text.replaceFirstChar
import kotlin.text.substring
import kotlin.text.titlecase

class TranscriptAdapter : RecyclerView.Adapter<TranscriptAdapter.TranscriptViewHolder>() {

    private var transcript: List<TranscriptMessage> = emptyList()

    companion object {
        private const val VIEW_TYPE_CALLER = 1
        private const val VIEW_TYPE_AI = 2
    }

    class TranscriptViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val speakerText: TextView = view.findViewById(R.id.speakerTextView)
        val messageText: TextView = view.findViewById(R.id.messageTextView)
        val timestampText: TextView = view.findViewById(R.id.timestampTextView)
    }

    override fun getItemViewType(position: Int): Int {
        return when (transcript[position].speaker.lowercase()) {
            "caller" -> VIEW_TYPE_CALLER
            "ai" -> VIEW_TYPE_AI
            else -> VIEW_TYPE_CALLER // Default to caller layout
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): TranscriptViewHolder {
        val layoutRes = when (viewType) {
            VIEW_TYPE_CALLER -> R.layout.item_transcript_message_left
            VIEW_TYPE_AI -> R.layout.item_transcript_message_right
            else -> R.layout.item_transcript_message_left
        }

        val view = LayoutInflater.from(parent.context)
            .inflate(layoutRes, parent, false)
        return TranscriptViewHolder(view)
    }

    override fun onBindViewHolder(holder: TranscriptViewHolder, position: Int) {
        val message = transcript[position]

        // Set speaker name with appropriate styling
        when (message.speaker.lowercase()) {
            "caller" -> {
                holder.speakerText.text = "Caller"
                holder.speakerText.setTextColor(holder.itemView.context.getColor(R.color.caller_color))
            }
            "ai" -> {
                holder.speakerText.text = "AI Assistant"
                holder.speakerText.setTextColor(holder.itemView.context.getColor(R.color.ai_color))
            }
            else -> {
                holder.speakerText.text = message.speaker.replaceFirstChar {
                    if (it.isLowerCase()) it.titlecase(Locale.getDefault()) else it.toString()
                }
                holder.speakerText.setTextColor(holder.itemView.context.getColor(R.color.default_speaker_color))
            }
        }

        holder.messageText.text = message.text

        // Format timestamp
        val formattedTime = try {
            val date = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.getDefault()).parse(message.timestamp)
            SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(date ?: Date())
        } catch (e: Exception) {
            message.timestamp.substring(11, 19) // fallback to extract time part
        }
        holder.timestampText.text = formattedTime
    }

    override fun getItemCount() = transcript.size

    fun updateTranscript(newTranscript: List<TranscriptMessage>) {
        transcript = newTranscript
        notifyDataSetChanged()
    }
}