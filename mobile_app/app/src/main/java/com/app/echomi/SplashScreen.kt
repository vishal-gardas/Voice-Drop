package com.app.echomi

import android.Manifest
import android.app.NotificationManager
import android.content.ContentValues.TAG
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.TextView
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.airbnb.lottie.LottieAnimationView
import com.app.echomi.Network.RetrofitInstance
import com.app.echomi.Services.MyFirebaseMessagingService
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.ktx.auth
import com.google.firebase.ktx.Firebase
import kotlinx.coroutines.launch

class SplashScreen : AppCompatActivity() {
    private lateinit var loadingAnimationView: LottieAnimationView
    private lateinit var statusTextView: TextView
    private lateinit var retryButton: Button
    private lateinit var auth: FirebaseAuth

    private val REQUEST_CODE_NOTIFICATIONS = 1001

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Initialize Firebase Auth
        auth = Firebase.auth

        // Check if user is already logged in
        checkUserAuthentication()
    }

    private fun checkUserAuthentication() {
        val currentUser = auth.currentUser

        if (currentUser != null) {
            // User is already logged in, proceed to MainActivity
            Log.d(TAG, "User already authenticated: ${currentUser.email}")
            navigateToMainActivity()
        } else {
            // User is not logged in, show splash screen and check backend
            setContentView(R.layout.activity_splash_screen)
            initializeViews()
            requestPermissions()
            checkBackendStatus()
        }
    }

    private fun initializeViews() {
        loadingAnimationView = findViewById(R.id.loadingAnimationView)
        statusTextView = findViewById(R.id.statusTextView)
        retryButton = findViewById(R.id.retryButton)

        retryButton.setOnClickListener {
            checkBackendStatus()
        }

        // Configure Lottie animation with error handling
        try {
            loadingAnimationView.speed = 1.0f
            loadingAnimationView.playAnimation() // Ensure animation plays (redundant with autoPlay=true)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to load animation: ${e.message}")
            loadingAnimationView.visibility = View.GONE // Hide animation on failure
        }

        // Add failure listener for Lottie animation
        loadingAnimationView.addLottieOnCompositionLoadedListener { composition ->
            if (composition == null) {
                Log.e(TAG, "Failed to load Lottie animation")
                loadingAnimationView.visibility = View.GONE // Hide animation on failure
            }
        }

        MyFirebaseMessagingService.stopEmergencyAlarm()
    }

    private fun requestPermissions() {
        requestNotificationPermission()
        requestDoNotDisturbPermission()
        requestSmsPermissions()
    }

    private fun requestDoNotDisturbPermission() {
        val notificationManager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M &&
            !notificationManager.isNotificationPolicyAccessGranted) {
            val intent = Intent(Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS)
            startActivity(intent)
        }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    REQUEST_CODE_NOTIFICATIONS
                )
            }
        }
    }

    private fun requestSmsPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val permissions = arrayOf(
                Manifest.permission.RECEIVE_SMS,
                Manifest.permission.READ_SMS,
                Manifest.permission.POST_NOTIFICATIONS
            )
            if (permissions.any { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }) {
                ActivityCompat.requestPermissions(this, permissions, 101)
            }
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CODE_NOTIFICATIONS) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Log.d(TAG, "✅ Notification permission granted")
            } else {
                Log.w(TAG, "❌ Notification permission denied")
            }
        }
    }

    private fun checkBackendStatus() {
        loadingAnimationView.visibility = View.VISIBLE
        statusTextView.text = "Connecting to service..."
        retryButton.visibility = View.GONE

        lifecycleScope.launch {
            try {
                val response = RetrofitInstance.api.healthCheck()
                if (response.isSuccessful) {
                    // Backend is reachable, proceed to Login
                    startActivity(Intent(this@SplashScreen, LoginScreen::class.java))
                    Log.d(TAG, "Backend Connected ✅ - Navigating to Login")
                    finish()
                } else {
                    showError()
                }
            } catch (e: Exception) {
                Log.d(TAG, "Backend Not Connected ❌")
                showError()
            }
        }
    }

    private fun navigateToMainActivity() {
        // Directly navigate to MainActivity without checking backend
        val intent = Intent(this, MainActivity::class.java)
        startActivity(intent)
        finish()
    }

    private fun showError() {
        loadingAnimationView.visibility = View.GONE
        statusTextView.text = "Connection failed. Please try again."
        retryButton.visibility = View.VISIBLE
    }

    override fun onPause() {
        super.onPause()
        // Pause animation when activity is paused
        if (::loadingAnimationView.isInitialized) {
            loadingAnimationView.pauseAnimation()
        }
    }

    override fun onResume() {
        super.onResume()
        // Resume animation when activity is resumed
        if (::loadingAnimationView.isInitialized) {
            try {
                loadingAnimationView.playAnimation()
            } catch (e: Exception) {
                Log.e(TAG, "Failed to resume animation: ${e.message}")
                loadingAnimationView.visibility = View.GONE
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        // Cancel animation when activity is destroyed
        if (::loadingAnimationView.isInitialized) {
            loadingAnimationView.cancelAnimation()
        }
    }
}