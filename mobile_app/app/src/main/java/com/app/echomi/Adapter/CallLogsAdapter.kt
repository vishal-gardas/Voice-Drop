package com.app.echomi.Adapter

import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Filter
import android.widget.Filterable
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.app.echomi.data.CallLog
import com.app.echomi.R
import com.app.echomi.Services.ContactHelper
import java.util.*
import kotlin.text.contains
import kotlin.text.isNullOrEmpty
import kotlin.text.lowercase
import kotlin.text.substring
import kotlin.text.trim

class CallLogsAdapter(
    private var logs: MutableList<CallLog>,
    private val onItemClick: (CallLog) -> Unit,
    private val context: Context // Add context parameter
) : RecyclerView.Adapter<CallLogsAdapter.LogViewHolder>(), Filterable {

    private var fullLogsList: List<CallLog> = ArrayList(logs)

    class LogViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val callerNumber: TextView = view.findViewById(R.id.callerNumberTextView)
        val summary: TextView = view.findViewById(R.id.summaryTextView)
        val date: TextView = view.findViewById(R.id.dateTextView)
        val icon: ImageView = view.findViewById(R.id.callerTypeIcon)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): LogViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_call_log, parent, false)
        return LogViewHolder(view)
    }

    override fun onBindViewHolder(holder: LogViewHolder, position: Int) {
        val log = logs[position]

        // Get contact name if available, otherwise use number
        val displayName = getContactDisplayName(log.callerNumber)
        holder.callerNumber.text = displayName

        holder.summary.text = log.summary ?: "No summary available."
        holder.date.text = log.startTime.substring(0, 10)

        // Set the click listener on the item view
        holder.itemView.setOnClickListener {
            onItemClick(log)
        }
    }

    override fun getItemCount() = logs.size

    fun updateLogs(newLogs: List<CallLog>) {
        logs.clear()
        logs.addAll(newLogs)
        fullLogsList = ArrayList(newLogs)
        notifyDataSetChanged()
    }

    override fun getFilter(): Filter {
        return callLogFilter
    }

    private val callLogFilter = object : Filter() {
        override fun performFiltering(constraint: CharSequence?): FilterResults {
            val filteredList = mutableListOf<CallLog>()
            if (constraint.isNullOrEmpty()) {
                filteredList.addAll(fullLogsList)
            } else {
                val filterPattern = constraint.toString().lowercase(Locale.getDefault()).trim()
                for (item in fullLogsList) {
                    // Search in both displayed name and original number
                    val displayName = getContactDisplayName(item.callerNumber).lowercase(Locale.getDefault())
                    val originalNumber = item.callerNumber.lowercase(Locale.getDefault())

                    if (displayName.contains(filterPattern) ||
                        originalNumber.contains(filterPattern) ||
                        item.summary?.lowercase(Locale.getDefault())?.contains(filterPattern) == true) {
                        filteredList.add(item)
                    }
                }
            }
            val results = FilterResults()
            results.values = filteredList
            return results
        }

        override fun publishResults(constraint: CharSequence?, results: FilterResults?) {
            logs.clear()
            if (results?.values is List<*>) {
                logs.addAll(results.values as List<CallLog>)
            }
            notifyDataSetChanged()
        }
    }

    private fun getContactDisplayName(phoneNumber: String): String {
        return ContactHelper.getContactName(context, phoneNumber) ?: phoneNumber
    }
}