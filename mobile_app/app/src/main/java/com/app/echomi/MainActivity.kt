package com.app.echomi

import android.content.Context
import android.content.SharedPreferences
import android.content.res.ColorStateList
import android.graphics.Color
import android.os.Bundle
import android.util.Log
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.setupWithNavController
import com.app.echomi.Network.RetrofitInstance
import com.echomi.app.network.FcmTokenRequest
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

class MainActivity : AppCompatActivity() {
    private lateinit var sharedPreferences: SharedPreferences
    private lateinit var googleSignInClient: GoogleSignInClient
    private lateinit var auth: FirebaseAuth

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)// Remove ripple effect
        val bottomNav = findViewById<BottomNavigationView>(R.id.bottom_navigation)
        bottomNav.itemRippleColor = ColorStateList.valueOf(Color.TRANSPARENT)
        bottomNav.itemRippleColor = ColorStateList.valueOf(ContextCompat.getColor(this, R.color.ripple))

        auth = FirebaseAuth.getInstance()

        val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestIdToken(getString(R.string.default_web_client_id)) // Make sure you have this in strings.xml
            .requestEmail()
            .build()
        googleSignInClient = GoogleSignIn.getClient(this, gso)

        // Initialize shared preferences
        sharedPreferences = getSharedPreferences("auth", Context.MODE_PRIVATE)

        val navHostFragment = supportFragmentManager.findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        val navController = navHostFragment.navController
        val bottomNavigationView = findViewById<BottomNavigationView>(R.id.bottom_navigation)
        bottomNavigationView.setupWithNavController(navController)

        getAndSendFcmToken()
    }

    private fun getAndSendFcmToken() {
        lifecycleScope.launch {
            try {
                // 1. Get FCM token from Firebase
                val fcmToken = FirebaseMessaging.getInstance().token.await()
                Log.d("MainActivity", "FCM Token: $fcmToken")

                // 2. Get Google ID token for authentication
                val idToken = getGoogleIdToken()
                if (idToken.isEmpty()) {
                    Log.e("MainActivity", "No Google ID token found - user might not be logged in")
                    return@launch
                }

                // 3. Prepare the authorization header with Google ID token
                val authHeader = "Bearer $idToken"

                // 4. Send token to backend
                val request = FcmTokenRequest(fcmToken = fcmToken)
                val response = RetrofitInstance.api.updateFcmToken(request, authHeader)

                if (response.isSuccessful) {
                    Log.d("MainActivity", "✅ FCM token sent to backend successfully")
                } else {
                    Log.e("MainActivity", "❌ Failed to send FCM token: ${response.code()} - ${response.message()}")
                }
            } catch (e: Exception) {
                Log.e("MainActivity", "Error getting/sending FCM token", e)
            }
        }
    }

    private suspend fun getGoogleIdToken(): String {
        return try {
            // Get current user
            val user = auth.currentUser
            if (user != null) {
                // Get the ID token
                val tokenResult = user.getIdToken(false).await()
                tokenResult.token ?: ""
            } else {
                // Try to get from Google Sign In account
                val account = GoogleSignIn.getLastSignedInAccount(this)
                account?.idToken ?: ""
            }
        } catch (e: Exception) {
            Log.e("MainActivity", "Error getting Google ID token", e)
            ""
        }
    }
}