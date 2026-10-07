package com.app.echomi.Fragments

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.airbnb.lottie.LottieAnimationView
import com.app.echomi.Adapter.CallLogsAdapter
import com.app.echomi.CallDetailScreen
import com.app.echomi.Network.RetrofitInstance
import com.app.echomi.R
import kotlinx.coroutines.launch

class CallLogsFragment : Fragment() {
    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: CallLogsAdapter
    private lateinit var loadingAnimationView: LottieAnimationView
    private lateinit var emptyStateTextView: TextView
    private lateinit var searchEditText: EditText

    companion object {
        private const val CONTACTS_PERMISSION_REQUEST_CODE = 100
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_call_logs, container, false)

        recyclerView = view.findViewById(R.id.callLogsRecyclerView)
        loadingAnimationView = view.findViewById(R.id.loadingAnimationView)
        emptyStateTextView = view.findViewById(R.id.emptyStateTextView)
        searchEditText = view.findViewById(R.id.searchEditText)

        setupRecyclerView()
        setupSearch()

        // Check and request contacts permission
        checkContactsPermission()

        return view
    }

    private fun setupRecyclerView() {
        adapter = CallLogsAdapter(mutableListOf(), { clickedLog ->
            val intent = Intent(activity, CallDetailScreen::class.java)
            intent.putExtra("CALL_ID", clickedLog._id)
            startActivity(intent)
        }, requireContext()) // Pass context to adapter

        recyclerView.adapter = adapter
        recyclerView.layoutManager = LinearLayoutManager(context)
    }

    private fun setupSearch() {
        searchEditText.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}

            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                adapter.filter.filter(s)
            }

            override fun afterTextChanged(s: Editable?) {}
        })
    }

    private fun checkContactsPermission() {
        when {
            ContextCompat.checkSelfPermission(
                requireContext(),
                android.Manifest.permission.READ_CONTACTS
            ) == PackageManager.PERMISSION_GRANTED -> {
                // Permission already granted, fetch call logs
                fetchCallLogs()
            }
            ActivityCompat.shouldShowRequestPermissionRationale(
                requireActivity(),
                android.Manifest.permission.READ_CONTACTS
            ) -> {
                // Explain why permission is needed
                Toast.makeText(
                    context,
                    "Contact permission is needed to display contact names",
                    Toast.LENGTH_LONG
                ).show()
                requestContactsPermission()
            }
            else -> {
                // Request the permission
                requestContactsPermission()
            }
        }
    }

    private fun requestContactsPermission() {
        requestPermissions(
            arrayOf(android.Manifest.permission.READ_CONTACTS),
            CONTACTS_PERMISSION_REQUEST_CODE
        )
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        when (requestCode) {
            CONTACTS_PERMISSION_REQUEST_CODE -> {
                if ((grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED)) {
                    // Permission granted, fetch call logs
                    fetchCallLogs()
                } else {
                    // Permission denied, fetch logs anyway (will show numbers instead of names)
                    Toast.makeText(
                        context,
                        "Contact names won't be displayed due to missing permission",
                        Toast.LENGTH_LONG
                    ).show()
                    fetchCallLogs()
                }
            }
            else -> {
                super.onRequestPermissionsResult(requestCode, permissions, grantResults)
            }
        }
    }

    private fun fetchCallLogs() {
        loadingAnimationView.visibility = View.VISIBLE
        emptyStateTextView.visibility = View.GONE
        recyclerView.visibility = View.GONE

        lifecycleScope.launch {
            try {
                val response = RetrofitInstance.api.getCallLogs()
                if (response.isSuccessful) {
                    val logs = response.body()
                    if (logs.isNullOrEmpty()) {
                        emptyStateTextView.visibility = View.VISIBLE
                    } else {
                        adapter.updateLogs(logs)
                        recyclerView.visibility = View.VISIBLE
                    }
                } else {
                    Toast.makeText(context, "Failed to load logs", Toast.LENGTH_SHORT).show()
                    emptyStateTextView.visibility = View.VISIBLE
                }
            } catch (e: Exception) {
                Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
                emptyStateTextView.visibility = View.VISIBLE
            } finally {
                loadingAnimationView.visibility = View.GONE
            }
        }
    }

    // Rest of your existing methods (onPause, onResume, onDestroyView) remain the same
    override fun onPause() {
        super.onPause()
        if (::loadingAnimationView.isInitialized) {
            loadingAnimationView.pauseAnimation()
        }
    }

    override fun onResume() {
        super.onResume()
        if (::loadingAnimationView.isInitialized) {
            try {
                loadingAnimationView.playAnimation()
            } catch (e: Exception) {
                Toast.makeText(context, "Failed to resume animation: ${e.message}", Toast.LENGTH_LONG).show()
                loadingAnimationView.visibility = View.GONE
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        if (::loadingAnimationView.isInitialized) {
            loadingAnimationView.cancelAnimation()
        }
    }
}