package com.app.echomi

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.os.Bundle
import android.telecom.TelecomManager
import android.widget.TextView
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton

class SetupScreen : AppCompatActivity() {
    private val twilioNumber = "+1 626-427-0085"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_setup_screen)

        val twilioNumberTextView: TextView = findViewById(R.id.twilioNumberTextView)
        val copyNumberButton: MaterialButton = findViewById(R.id.copyNumberButton)
        val openSettingsButton: MaterialButton = findViewById(R.id.openSettingsButton)
        val continueButton: MaterialButton = findViewById(R.id.continueButton)

        // Set the Twilio number in the UI
        twilioNumberTextView.text = twilioNumber

        // Handle the "Copy" button click
        copyNumberButton.setOnClickListener {
            copyToClipboard(twilioNumber)
            Toast.makeText(this, "Number copied!", Toast.LENGTH_SHORT).show()
        }

        // Handle the "Open Settings" button click
        openSettingsButton.setOnClickListener {
            openCallForwardingSettings()
        }

        // Handle the "Continue" button click
        continueButton.setOnClickListener {
            Toast.makeText(this, "Setup completed!", Toast.LENGTH_SHORT).show()
            // Navigate to MainActivity instead of ContactSelectionScreen
            val intent = Intent(this, MainActivity::class.java)
            startActivity(intent)
            finish()
        }
    }

    private fun copyToClipboard(text: String) {
        val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
        val clip = ClipData.newPlainText("Twilio Number", text)
        clipboard.setPrimaryClip(clip)
    }

    private fun openCallForwardingSettings() {
        try {
            val intent = Intent(TelecomManager.ACTION_SHOW_CALL_SETTINGS)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
            startActivity(intent)
        } catch (e: Exception) {
            try {
                val fallbackIntent = Intent("com.android.phone.CallFeaturesSetting")
                startActivity(fallbackIntent)
            } catch (fallbackException: Exception) {
                Toast.makeText(this, "Could not open settings directly. Opening dialer.", Toast.LENGTH_LONG).show()
                try {
                    val finalFallback = Intent(Intent.ACTION_DIAL)
                    startActivity(finalFallback)
                } catch (finalException: Exception) {
                    Toast.makeText(this, "Could not open any phone settings.", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
}