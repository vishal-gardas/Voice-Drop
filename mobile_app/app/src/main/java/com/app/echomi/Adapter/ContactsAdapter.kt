package com.app.echomi.Adapter

import android.content.res.ColorStateList
import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.CheckBox
import android.widget.Filter
import android.widget.Filterable
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.app.echomi.R
import com.app.echomi.data.Contact
import java.util.Locale
import kotlin.apply
import kotlin.collections.filter
import kotlin.collections.find
import kotlin.text.contains
import kotlin.text.isNullOrEmpty
import kotlin.text.lowercase
import kotlin.text.trim

class ContactsAdapter(
    private var displayedContacts: MutableList<Contact>,
    private val fullContactList: List<Contact>, // Complete list
    private val onRoleChanged: () -> Unit // Callback to re-sort/filter
) : RecyclerView.Adapter<ContactsAdapter.ContactViewHolder>(), Filterable {

    class ContactViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val nameTextView: TextView = view.findViewById(R.id.contactNameTextView)
        val numberTextView: TextView = view.findViewById(R.id.contactNumberTextView)
        val familyCheckBox: CheckBox = view.findViewById(R.id.familyCheckBox)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ContactViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_contact, parent, false)
        return ContactViewHolder(view)
    }

    override fun onBindViewHolder(holder: ContactViewHolder, position: Int) {
        val contact = displayedContacts[position]

        holder.nameTextView.text = contact.name
        holder.numberTextView.text = contact.phoneNumber

        // Avoid checkbox recycling issue
        holder.familyCheckBox.setOnCheckedChangeListener(null)

        // Pre-check family contacts
        holder.familyCheckBox.isChecked = contact.role == "family"

        // Green tick for checked contacts
        holder.familyCheckBox.buttonTintList = if (holder.familyCheckBox.isChecked) {
            ColorStateList.valueOf(Color.GREEN)
        } else {
            ColorStateList.valueOf(Color.WHITE)
        }

        holder.familyCheckBox.setOnCheckedChangeListener { _, isChecked ->
            val originalContact = fullContactList.find { it.id == contact.id }
            originalContact?.role = if (isChecked) "family" else "default"

            // Update tick color dynamically
            holder.familyCheckBox.buttonTintList = if (isChecked) {
                ColorStateList.valueOf(Color.GREEN)
            } else {
                ColorStateList.valueOf(Color.WHITE)
            }
            onRoleChanged()
        }
    }

    override fun getItemCount() = displayedContacts.size

    // Returns only selected family contacts
    fun getCategorizedContacts(): List<Contact> {
        return fullContactList.filter { it.role == "family" }
    }

    override fun getFilter(): Filter = contactFilter

    private val contactFilter = object : Filter() {
        override fun performFiltering(constraint: CharSequence?): FilterResults {
            val filteredList = mutableListOf<Contact>()
            val sourceList = ArrayList(fullContactList)

            if (constraint.isNullOrEmpty()) {
                filteredList.addAll(sourceList)
            } else {
                val filterPattern = constraint.toString().lowercase(Locale.getDefault()).trim()
                for (item in sourceList) {
                    if (item.name.lowercase(Locale.getDefault()).contains(filterPattern)) {
                        filteredList.add(item)
                    }
                }
            }

            return FilterResults().apply { values = filteredList }
        }

        override fun publishResults(constraint: CharSequence?, results: FilterResults?) {
            displayedContacts.clear()
            if (results?.values is List<*>) {
                @Suppress("UNCHECKED_CAST")
                displayedContacts.addAll(results.values as List<Contact>)
            }
            notifyDataSetChanged()
        }
    }
}
