package com.app.echomi.Adapter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.app.echomi.R
import com.app.echomi.data.Prompt

class PromptsAdapter(
    private var prompts: List<Prompt>,
    private val onItemClick: (Prompt) -> Unit
) : RecyclerView.Adapter<PromptsAdapter.PromptViewHolder>() {

    class PromptViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val title: TextView = view.findViewById(R.id.promptTitleTextView)
        val instructions: TextView = view.findViewById(R.id.promptInstructionsTextView)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): PromptViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_prompt, parent, false)
        return PromptViewHolder(view)
    }

    override fun onBindViewHolder(holder: PromptViewHolder, position: Int) {
        val prompt = prompts[position]

        // Set a title with an icon based on the prompt type
        holder.title.text = when (prompt.promptType) {
            "delivery" -> "🚚 Delivery Partners"
            "family" -> "❤️ Family & Friends"
            "unknown" -> "❓ Unknown Callers"
            else -> "👤 Default"
        }
        holder.instructions.text = prompt.instructions

        holder.itemView.setOnClickListener {
            onItemClick(prompt)
        }
    }

    override fun getItemCount() = prompts.size

    fun updatePrompts(newPrompts: List<Prompt>) {
        prompts = newPrompts
        notifyDataSetChanged()
    }
}
