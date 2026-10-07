package com.app.echomi

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.app.echomi.Services.ApprovalService
import com.app.echomi.databinding.ActivityApprovalBinding

class ApprovalActivity : AppCompatActivity() {

    private lateinit var binding: ActivityApprovalBinding
    private lateinit var approvalService: ApprovalService

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityApprovalBinding.inflate(layoutInflater)
        setContentView(binding.root)

        approvalService = ApprovalService(this)

        val approvalId = intent.getStringExtra("approvalId") ?: ""
        val company = intent.getStringExtra("company") ?: "Unknown Company"
        val callerNumber = intent.getStringExtra("callerNumber") ?: "Unknown Number"
        val callSid = intent.getStringExtra("callSid") ?: ""

        // Update UI
        binding.companyName.text = company
        binding.callerNumber.text = "Caller: $callerNumber"
        binding.description.text = "A delivery person from $company is requesting OTP verification for your delivery."

        binding.approveButton.setOnClickListener {
            approvalService.sendApprovalResponseAsync(approvalId, true)
            finish()
        }

        binding.denyButton.setOnClickListener {
            approvalService.sendApprovalResponseAsync(approvalId, false)
            finish()
        }

        binding.closeButton.setOnClickListener {
            finish()
        }
    }
}