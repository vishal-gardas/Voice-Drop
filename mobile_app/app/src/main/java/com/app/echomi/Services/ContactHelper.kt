package com.app.echomi.Services

import android.content.ContentResolver
import android.content.Context
import android.provider.ContactsContract

object ContactHelper {

    fun getContactName(context: Context, phoneNumber: String): String? {
        if (!hasContactPermission(context)) {
            return null
        }

        val contentResolver: ContentResolver = context.contentResolver
        var contactName: String? = null

        try {
            val uri = ContactsContract.PhoneLookup.CONTENT_FILTER_URI
                .buildUpon()
                .appendPath(phoneNumber)
                .build()

            val projection = arrayOf(
                ContactsContract.PhoneLookup.DISPLAY_NAME
            )

            contentResolver.query(uri, projection, null, null, null)?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val nameIndex = cursor.getColumnIndex(ContactsContract.PhoneLookup.DISPLAY_NAME)
                    if (nameIndex != -1) {
                        contactName = cursor.getString(nameIndex)
                    }
                }
            }
        } catch (e: SecurityException) {
            // Permission might be revoked during runtime
            return null
        } catch (e: Exception) {
            e.printStackTrace()
        }

        return contactName
    }

    private fun hasContactPermission(context: Context): Boolean {
        return context.checkSelfPermission(android.Manifest.permission.READ_CONTACTS) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED
    }

    // Helper function to normalize phone numbers for comparison
    fun normalizePhoneNumber(phoneNumber: String): String {
        return phoneNumber.replace("[^0-9]".toRegex(), "")
    }
}