# 📞 VoiceDrop — AI Delivery Call Assistant

> **A real-time AI phone agent** that picks up calls on your behalf — guides delivery drivers with turn-by-turn directions, fetches & reads OTPs from your SMS (with owner approval), and screens unknown callers by collecting their name, purpose, and callback number.

---

## 📌 Problem Statement

In everyday life, people miss important phone calls from delivery agents and unknown callers — especially when busy. Delivery agents often struggle to find the address, need OTPs, and have no way to reach the resident in time. There is no smart, automated solution that:
- Guides delivery personnel to the correct address
- Provides OTPs for deliveries without human intervention
- Screens unknown callers and captures messages for the owner

**VoiceDrop** solves this with an AI backend that handles calls autonomously.

---

## 💡 Solution Overview

VoiceDrop is a four-tier system:

1. **Twilio** receives the real phone call and streams audio to the Node.js backend.
2. **Node.js Telephony Backend** (`/backend`) streams caller audio to the Python Speech Subsystem, receives transcripts, forwards text to the Flask AI engine, and converts the AI response back to telephony audio for the caller.
3. **VoiceDrop Flask API** (`/app`) is the AI brain and self-hosted SLP speech server — it handles Speech-to-Text (Whisper), Text-to-Speech (Neural/Local TTS), identifies caller type, handles delivery/OTP flows, and returns intelligent responses.
4. **Android Mobile App** (`/mobile_app`) runs on the owner's phone in the background. When the AI needs an OTP during a live call, the server sends a silent Firebase push notification to the app, which reads the owner's SMS messages, extracts the OTP, and sends it back to the server — all within seconds.

```
Phone Call → Twilio → Node.js Backend → VoiceDrop Flask API (Whisper STT + Gemini + Neural TTS) → Spoken back to Caller
                                ↕
                    Android App (OTP SMS fetching via FCM)
```

---

## 🏗️ System Architecture

```mermaid
graph TD
    Caller["📞 Caller Phone"] -->|"1. Voice Call"| Twilio["☁️ Twilio Telephony"]

    subgraph NodeBackend["🖥️ Node.js Telephony Bridge port 3000"]
        TwilioWebhook["🔌 Twilio Webhook /api/twilio/incoming"]
        STT["🎙️ Local Whisper STT Adapter"]
        TTS["🔊 Local Neural TTS Adapter"]
        TwilioWebhook --> STT
    end

    Twilio -->|"2. Webhook Audio Stream"| TwilioWebhook

    subgraph PythonAI["🧠 Python Flask AI Engine port 5000"]
        ConvHandler["💬 Conversation Handler &amp; Role Identifier"]
        DeliveryFlow["📦 Delivery &amp; Directions Flow"]
        UnknownFlow["👤 Unknown Caller Flow"]
        OtpFlow["🔑 OTP &amp; SMS Verification Flow"]

        ConvHandler --> DeliveryFlow
        ConvHandler --> UnknownFlow
        ConvHandler --> OtpFlow
    end

    STT -->|"3. POST /generate User Transcript"| ConvHandler

    DeliveryFlow -->|"Turn-by-Turn Routes"| Mapbox["🗺️ Mapbox Navigation API"]
    UnknownFlow -->|"Smart Q&amp;A"| Gemini["✨ Google Gemini AI"]
    OtpFlow -->|"FCM Silent Push"| Firebase["🔥 Firebase Cloud Messaging"]

    subgraph MobileApp["📱 Android Mobile App"]
        FCMSvc["📥 FCM Push Receiver"]
        SMSReader["📝 Foreground SMS Reader Last 20 SMS"]
        FCMSvc --> SMSReader
    end

    Firebase -->|"4. Request OTP Check"| FCMSvc
    SMSReader -->|"5. Extracted OTP POST /api/sms/call/store"| TwilioWebhook

    ConvHandler -->|"6. AI Text Response"| TTS
    TTS -->|"7. Audio Stream"| Twilio
    Twilio -->|"8. Speaks to Caller"| Caller

    TwilioWebhook --- MongoDB["🍃 MongoDB Atlas Database"]

    style Caller fill:#2e7d32,stroke:#1b5e20,color:#fff
    style Twilio fill:#c2185b,stroke:#880e4f,color:#fff
    style TwilioWebhook fill:#1565c0,stroke:#0d47a1,color:#fff
    style STT fill:#1565c0,stroke:#0d47a1,color:#fff
    style TTS fill:#1565c0,stroke:#0d47a1,color:#fff
    style ConvHandler fill:#e65100,stroke:#bf360c,color:#fff
    style DeliveryFlow fill:#e65100,stroke:#bf360c,color:#fff
    style UnknownFlow fill:#e65100,stroke:#bf360c,color:#fff
    style OtpFlow fill:#e65100,stroke:#bf360c,color:#fff
    style FCMSvc fill:#6a1b9a,stroke:#4a148c,color:#fff
    style SMSReader fill:#6a1b9a,stroke:#4a148c,color:#fff
    style Mapbox fill:#00897b,stroke:#00695c,color:#fff
    style Gemini fill:#00897b,stroke:#00695c,color:#fff
    style Firebase fill:#00897b,stroke:#00695c,color:#fff
    style MongoDB fill:#37474f,stroke:#263238,color:#fff
```

---

## ✨ Features

### 📦 Delivery Personnel Flow
| Step | What Happens |
|------|-------------|
| 1    | AI identifies the caller as a delivery agent (keyword + fuzzy matching) |
| 2    | Asks if they need directions or are already at the location |
| 3    | Takes their current landmark and provides **turn-by-turn walking directions** via Mapbox |
| 4    | Upon arrival, asks if they need an **OTP** |
| 5    | Sends a silent FCM push to the owner's phone → reads the latest 20 SMS messages → extracts the OTP → reads it out to the delivery driver |

### 👤 Unknown Caller Flow
| Step | What Happens |
|------|-------------|
| 1    | Collects caller's **name** |
| 2    | Asks the **reason for calling** |
| 3    | Gemini AI determines if intelligent **follow-up questions** are needed |
| 4    | Collects **callback number** |
| 5    | Sends a **notification** to the owner with all details |

### 📱 OTP Approval System
- When a delivery driver requests an OTP, the Android app shows an **approval notification** to the owner
- The backend sends a **silent (data-only) FCM push** to bypass default system notifications, allowing the Android app to construct a rich notification with actionable Approve/Deny buttons.
- The owner can **approve or deny** OTP sharing directly from the notification
- Prevents unauthorized OTP sharing without the owner's consent

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------| 
| **Telephony** | Twilio Voice | Receives real phone calls, handles call events |
| **Backend Framework** | Python + Flask | REST API server (AI brain) |
| **Telephony Bridge** | Node.js + Express + WebSocket | Connects Twilio to the Flask API via WebSocket |
| **Speech-to-Text** | Local Whisper (LoRA fine-tuned) | Converts caller's voice to text in real time locally |
| **Text-to-Speech** | Local Neural TTS + HiFi-GAN | Converts AI response text to audio locally |
| **AI Engine** | Google Gemini AI | Conversation intelligence, intent detection, info extraction |
| **Maps & Navigation** | Mapbox API | Geocoding, routing, turn-by-turn directions |
| **Database** | MongoDB Atlas + Mongoose | Stores call logs, users, SMS data, prompts, contacts, settings |
| **Authentication** | Firebase Auth + Admin SDK | Google Sign-In on mobile, JWT verification on backend |
| **Push Notifications** | Firebase Cloud Messaging (FCM) | Silent push (data-only) to wake the mobile app for SMS reading and OTP approvals |
| **OTP SMS Reading** | Android `SmsFetchService` | Foreground service that reads SMS from device |
| **Tunneling** | ngrok (static domain) | Exposes local server to the internet for Twilio & mobile app |
| **Config** | python-dotenv | Environment variable management |
| **Validation** | Pydantic | Data schema validation |
| **CORS** | flask-cors / cors | Cross-origin API access (both Python & Node.js) |

---

## 🗂️ Project Structure

```
VoiceDrop/
├── main.py                          # Flask app entry point
├── requirements.txt                 # Python dependencies
├── .env                             # Flask environment variables 🔒
├── .gitignore                       # Root gitignore — protects all secrets
│
├── app/                             # Flask AI brain (port 5000)
│   ├── config/
│   │   └── config.py                # Application configuration class
│   │
│   ├── routes/
│   │   ├── conversation.py          # Main /generate endpoint + OTP & order routes
│   │   ├── admin.py                 # Admin management endpoints (/api/admin/*)
│   │   ├── call_summary.py          # Call summary generation endpoint
│   │   └── health.py                # Health check & status endpoints
│   │
│   ├── services/
│   │   ├── conversation_handler.py  # Core AI conversation logic
│   │   ├── gemini_service.py        # Google Gemini AI integration
│   │   ├── mapbox_service.py        # Mapbox maps & routing integration
│   │   ├── delivery_guidance_service.py  # Delivery direction logic
│   │   ├── real_otp_service.py      # OTP fetching service
│   │   ├── sms_service.py           # SMS reading & management
│   │   ├── notification_service.py  # Owner notification system
│   │   ├── call_summary_service.py  # AI-powered call summarization
│   │   └── service_factory.py       # Dependency injection / service creation
│   │
│   ├── models/
│   │   └── schemas.py               # Pydantic data models & schemas
│   │
│   ├── graphs/                      # Placeholder for future LangGraph implementation
│   │   ├── conversation_manager.py
│   │   └── nodes.py
│   │
│   └── utils/
│       ├── text_processing.py       # Intent detection, info extraction, fuzzy matching
│       ├── language_utils.py        # Multilingual response templates
│       └── sms_parser.py            # OTP extraction from raw SMS text
│
├── backend/                         # Node.js Telephony Bridge (port 3000)
│   ├── server.js                    # Express + WebSocket server entry point
│   ├── .env                         # Node.js environment variables 🔒
│   ├── .gitignore
│   ├── package.json
│   ├── config/
│   │   ├── db.js                    # MongoDB connection
│   │   └── firebase-service-account.json  # Firebase Admin SDK key 🔒
│   ├── controllers/
│   │   ├── twilioController.js      # Twilio webhook handler (STT → Flask → TTS)
│   │   ├── authController.js        # User registration/login
│   │   ├── callLogController.js     # Call log retrieval
│   │   ├── contactController.js     # Contact sync from mobile app
│   │   ├── promptController.js      # Custom AI prompt management
│   │   ├── smsController.js         # SMS store, fetch & trigger logic
│   │   ├── summaryController.js     # Call summary generation & retrieval
│   │   └── userSettingsController.js # FCM token & battery status management
│   ├── middleware/
│   │   └── authMiddleware.js        # Firebase Admin token verification
│   ├── models/
│   │   ├── User.js                  # User schema (email, firebaseUid, twilioNumber)
│   │   ├── Sms.js                   # SMS data schema
│   │   ├── CallLog.js               # Call log schema (transcript, duration, summary)
│   │   ├── Prompt.js                # Custom AI prompts per user
│   │   ├── Contact.js               # Synced contacts
│   │   └── UserSettings.js          # FCM token, preferences
│   ├── routes/
│   │   ├── twilioRoutes.js          # /api/twilio/* endpoints
│   │   ├── twilioStatusRoute.js     # /api/twilio/status callback handler
│   │   ├── authRoutes.js            # /api/auth/* endpoints
│   │   ├── smsRoutes.js             # /api/sms/* endpoints
│   │   ├── callLogRoutes.js         # /api/logs/* endpoints
│   │   ├── promptRoutes.js          # /api/prompts/* endpoints
│   │   ├── contactRoutes.js         # /api/contacts/* endpoints
│   │   ├── otpRoutes.js             # /api/otp/* endpoints (approval system)
│   │   ├── summaryRoutes.js         # /api/summary/* endpoints
│   │   └── userSettingsRoutes.js    # /api/settings/* endpoints
│   └── services/
│       ├── sttService.js            # Local Speech-to-Text Integration
│       ├── ttsService.js            # Local Text-to-Speech Integration
│       ├── fcmService.js            # Firebase Cloud Messaging push delivery
│       ├── smsFcmService.js         # SMS-specific FCM trigger logic
│       ├── smsService.js            # SMS storage & retrieval
│       ├── smsVerificationService.js # OTP lookup, approval & verification system
│       ├── conversationResumeService.js # Resume call after OTP approval
│       ├── conversationManager.js   # Active WebSocket conversation tracking
│       └── summaryService.js        # AI call summary generation
│
└── mobile_app/                      # Android App (Kotlin, Native)
    ├── app/
    │   ├── google-services.json     # Firebase config 🔒
    │   ├── build.gradle.kts         # App-level Gradle config + dependencies
    │   └── src/main/
    │       ├── AndroidManifest.xml   # Permissions: SMS, FCM, Internet, Phone
    │       └── java/com/app/echomi/
    │           ├── SplashScreen.kt           # App startup + backend health check
    │           ├── LoginScreen.kt            # Firebase Google Sign-In
    │           ├── SetupScreen.kt            # Twilio number setup UI
    │           ├── MainActivity.kt           # Dashboard with bottom navigation
    │           ├── CallDetailScreen.kt       # Call transcript viewer
    │           ├── ContactSelectionScreen.kt # Contact sync screen
    │           ├── ApprovalActivity.kt       # OTP sharing approval dialog
    │           ├── Adapter/
    │           │   ├── CallLogsAdapter.kt    # Call log list adapter
    │           │   ├── ContactsAdapter.kt   # Contact list adapter
    │           │   ├── PromptsAdapter.kt    # Prompt list adapter
    │           │   └── TranscriptAdapter.kt # Transcript message adapter
    │           ├── Fragments/
    │           │   ├── AssistantFragment.kt  # AI assistant tab
    │           │   ├── CallLogsFragment.kt  # Call history tab
    │           │   └── ProfileFragment.kt   # Profile & settings tab
    │           ├── Network/
    │           │   ├── ApiService.kt         # Retrofit API interface
    │           │   ├── RetrofitInstance.kt    # Base URL config (ngrok domain)
    │           │   └── AuthInterceptor.kt    # Firebase token + tunnel bypass headers
    │           ├── Services/
    │           │   ├── MyFirebaseMessagingService.kt  # FCM handler (routes push types)
    │           │   ├── SmsFetchService.kt    # Reads SMS from device, POSTs to backend
    │           │   ├── SmsReceiver.kt        # Broadcast receiver for incoming SMS
    │           │   ├── ApprovalService.kt    # OTP approval notification handler
    │           │   ├── ApprovalReceiver.kt   # Broadcast receiver for approval actions
    │           │   └── ContactHelper.kt      # Device contact reader utility
    │           └── data/                     # Kotlin data classes
    │               ├── CallLog.kt            # Call log model
    │               ├── Contact.kt            # Contact model
    │               ├── Prompt.kt             # Prompt model
    │               ├── SmsMessage.kt         # SMS message model
    │               ├── TranscriptEntry.kt    # Transcript entry model
    │               ├── ApprovalRequest.kt    # OTP approval request model
    │               ├── OtpRequest.kt / OtpResponse.kt
    │               ├── FirebaseLoginRequest.kt / UserResponse.kt
    │               ├── SmsStoreRequest.kt / SmsStoreResponse.kt
    │               └── ...                   # Other request/response data classes
    ├── build.gradle.kts              # Root Gradle config
    └── .gitignore
```

---

## 🚀 Setup & Running

### Prerequisites
- Python 3.9+
- Node.js 18+
- Android Studio (for installing the mobile app)
- A **Twilio account** with a phone number
- A **Google Gemini API Key**
- A **Mapbox API Key**
- A **MongoDB URI** (Atlas free tier works)
- A **Firebase project** (for Auth + FCM push notifications)
- An **ngrok account** (free tier — provides a permanent static domain)

### Step 1 — Configure Environment Variables

**Flask API** (`VoiceDrop/.env`):
```env
GEMINI_API_KEY=your_gemini_key
MAPBOX_API_KEY=your_mapbox_key
NODEJS_BACKEND_URL=http://localhost:3000
INTERNAL_API_KEY=dev-internal-key-123
OWNER_PHONE_NUMBER=+91XXXXXXXXXX
BASE_URL=http://localhost:5000
APP_SECRET_KEY=your-secret-key
USER_LAT=12.974072
USER_LNG=79.163959
MOCK_MODE=False
LOG_LEVEL=INFO
```

**Node.js Backend** (`VoiceDrop/backend/.env`):
```env
PORT=3000
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/voicedrop
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
AI_ENDPOINT_URL=http://localhost:5000/generate
AI_MODEL_URL=http://localhost:5000
SMS_ENDPOINT_URL=http://localhost:3000
```

**Firebase Config Files** (not committed to Git):
- `backend/config/firebase-service-account.json` — Download from Firebase Console → Project Settings → Service Accounts → Generate New Private Key
- `mobile_app/app/google-services.json` — Download from Firebase Console → Project Settings → General → Your Apps → Download `google-services.json`

### Step 2 — Install Dependencies

```bash
# Flask API (Python)
cd VoiceDrop
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Node.js Backend
cd backend
npm install
```

### Step 3 — Install the Android App (One-Time)

1. Open **Android Studio** → Open the `VoiceDrop/mobile_app` folder
2. Update `RetrofitInstance.kt` with your ngrok static domain:
   ```kotlin
   private const val BASE_URL = "https://your-static-domain.ngrok-free.dev/"
   ```
3. Connect your Android phone via USB (with USB debugging enabled)
4. Click **Run ⏵** to install the app
5. Grant **SMS** and **Notification** permissions when prompted
6. Sign in with **Google** on the login screen
7. **Unplug USB** — the app stays installed and runs in the background permanently

### Step 4 — Run All Three Services

Open **three separate terminals** every time you want to use VoiceDrop:

**Terminal 1 — Flask AI Brain:**
```bash
cd VoiceDrop
venv\Scripts\activate
python main.py
```
*(Starts on port 5000)*

**Terminal 2 — Node.js Telephony Backend:**
```bash
cd VoiceDrop\backend
npm start
```
*(Starts on port 3000)*

**Terminal 3 — ngrok Tunnel (permanent URL):**
```bash
ngrok http 3000 --domain=your-static-domain.ngrok-free.dev
```
*(Same URL every time — no code changes needed between restarts)*

### Step 5 — Connect Twilio (One-Time)

1. Go to your **Twilio Console** → **Phone Numbers** → **Active Numbers**
2. Click your number → scroll to **Voice Configuration** → **"A call comes in"**
3. Set the webhook URL to: `https://your-static-domain.ngrok-free.dev/api/twilio/incoming`
4. Click **Save**

**Call your Twilio number from any phone — the AI will answer!**

---

## 📞 How to Test

### Delivery Person Scenario
Call your Twilio number and say:
> *"Hi, I have a delivery from Amazon"*

The AI will:
1. Ask if you need directions
2. Provide turn-by-turn walking directions (via Mapbox)
3. Ask if you need the OTP
4. Silently fetch the OTP from the owner's phone via FCM push
5. Read the OTP out loud

### Unknown Caller Scenario
Call your Twilio number and say:
> *"Hi, I'm calling from SBI bank"*

The AI will:
1. Ask your name
2. Ask the reason for your call
3. Ask follow-up questions if needed
4. Collect a callback number
5. Notify the owner with all details

---

## 🌐 API Endpoints

### Flask API (port 5000)

| Method | Endpoint | Description |
|--------|---------|-------------|
| `GET`  | `/`     | API info, version, and available endpoints |
| `GET`  | `/health` | Health check — confirms all services are configured |
| `GET`  | `/status` | Detailed system status (Python version, platform, services) |
| `GET`  | `/api/status` | Service status with API key validation |
| `POST` | `/generate` | **Main endpoint** — processes one turn of a phone conversation |
| `POST` | `/api/get-otp` | Direct OTP lookup by company + order |
| `POST` | `/api/conversation-summary` | Generate a summary from conversation history |
| `POST` | `/add-order` | Pre-register an order + OTP in the system |
| `GET`  | `/list-orders` | View all current orders in the wallet |
| `POST` | `/generate-summary` | Generate an AI summary from a call transcript |
| `POST` | `/api/admin/configure-backend` | Configure backend connection for AI model |
| `POST` | `/api/admin/test-backend` | Test backend SMS connectivity and parsing |
| `POST` | `/api/admin/test-sms-parsing` | Test SMS OTP parsing with sample messages |
| `GET`  | `/api/admin/backend-status` | Get current backend configuration status |
| `POST` | `/api/admin/update-config` | Update AI model configuration at runtime |

### Node.js Backend (port 3000)

| Method | Endpoint | Description |
|--------|---------|-------------|
| `GET`  | `/` | Health check |
| `POST` | `/api/twilio/incoming` | Twilio voice webhook (receives calls) |
| `POST` | `/api/twilio/voice` | Twilio voice webhook (alias) |
| `POST` | `/api/twilio/status` | Twilio call status callback (duration, end time) |
| `POST` | `/api/twilio/send-notification` | Send notification via Twilio route |
| `GET`  | `/api/twilio/test` | Twilio route health check |
| `POST` | `/api/auth/firebase` | Firebase login/registration |
| `GET`  | `/api/logs` | Get all call logs for authenticated user |
| `GET`  | `/api/logs/:id` | Get a specific call log by ID |
| `GET`  | `/api/prompts` | Get user's custom AI prompts |
| `PUT`  | `/api/prompts/:promptType` | Update a specific prompt |
| `POST` | `/api/sms/call/store` | Store SMS messages from mobile app |
| `POST` | `/api/sms/call/latest` | Fetch latest SMS for a call (AI model use) |
| `POST` | `/api/sms/call/trigger-fetch` | Trigger SMS fetch from mobile app via FCM |
| `POST` | `/api/otp/approve` | Approve or deny OTP sharing |
| `GET`  | `/api/otp/status/:approvalId` | Check OTP approval request status |
| `POST` | `/api/otp/request` | Request user approval for OTP sharing via FCM |
| `POST` | `/api/contacts` | Sync contacts from mobile app |
| `GET`  | `/api/summary/call/:callSid` | Get call summary for a specific call |
| `POST` | `/api/summary/generate/:callSid` | Manually generate summary for a call |
| `GET`  | `/api/summary/user/:userId` | Get all call summaries for a user |
| `POST` | `/api/summary/generate-missing` | Bulk generate summaries for calls without one |
| `PUT`  | `/api/settings/fcm-token` | Update user's FCM token |
| `GET`  | `/api/settings/fcm-token` | Get user's FCM token |
| `PUT`  | `/api/settings/battery-status` | Update device battery status |
| `POST` | `/api/send-notification` | Receive notifications from AI model |

---

## 📱 Sample API Usage

### Delivery Conversation Turn
```json
POST /generate
{
  "new_message": "I have a delivery from Amazon",
  "caller_role": "delivery",
  "conversation_stage": "start",
  "response_language": "en",
  "call_sid": "call-001",
  "delivery_location": {
    "latitude": 12.974072,
    "longitude": 79.163959
  },
  "collected_info": {}
}
```

**Response:**
```json
{
  "response_text": "Hi! I see you have a delivery from Amazon. Do you need help getting here, or are you already here?",
  "conversation_stage": "asking_location_help",
  "requires_sms": false,
  "collected_info": { "company": "Amazon" }
}
```

---

### OTP Request
```json
POST /generate
{
  "new_message": "I need the OTP",
  "caller_role": "delivery",
  "conversation_stage": "asking_if_otp_needed",
  "collected_info": { "company": "Amazon" }
}
```

**Response:**
```json
{
  "response_text": "I'll check your recent messages for the Amazon OTP. Please give me a moment.",
  "requires_sms": true,
  "conversation_stage": "checking_sms",
  "company_requested": "Amazon"
}
```

---

## 🔄 Conversation State Machine

```
start
  ├── [delivery keyword detected]  → asking_location_help
  │       ├── [needs directions]   → getting_current_location → traveling_to_location
  │       └── [already here]       → asking_if_otp_needed
  │                                       ├── [yes] → checking_sms → otp_provided → end_of_call
  │                                       └── [no]  → end_of_call
  │
  └── [unknown caller]             → asking_name → asking_purpose → collecting_contact → end_of_call
```

---

## 🔐 OTP Fetching Flow (Detailed)

```
 1. Delivery driver says "I need the OTP" on the call
 2. Node.js backend detects OTP request
 3. Backend sends silent FCM push notification to owner's Android app
 4. MyFirebaseMessagingService receives the push
 5. SmsFetchService starts as a Foreground Service
 6. Reads the latest 20 SMS messages from the device
 7. POSTs them to Node.js backend at /api/sms/call/store
 8. Backend scans SMS for OTP matching the delivery company
 9. Android app receives silent push and creates custom approval notification — owner approves or denies sharing
10. If approved, AI reads the OTP aloud to the delivery driver
11. Call log and transcript are saved to MongoDB
```

---

## 🔑 Environment Variables

### Flask API (`VoiceDrop/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini AI API key | ✅ Yes |
| `MAPBOX_API_KEY` | Mapbox API key for maps/routing | ✅ Yes |
| `NODEJS_BACKEND_URL` | URL of the Node.js backend | ✅ Yes |
| `INTERNAL_API_KEY` | Secret key for internal service calls | ✅ Yes |
| `OWNER_PHONE_NUMBER` | Phone number to send notifications to | ✅ Yes |
| `USER_LAT` / `USER_LNG` | Owner's home/delivery location coordinates | ✅ Yes |
| `BASE_URL` | Flask server base URL | Optional |
| `APP_SECRET_KEY` | Secret for the `/add-order` endpoint | Optional |
| `MOCK_MODE` | Set to `True` to use mock services | Optional |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, etc.) | Optional |

### Node.js Backend (`backend/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `MONGO_URI` | MongoDB Atlas connection string | ✅ Yes |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | ✅ Yes |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | ✅ Yes |
| `TWILIO_PHONE_NUMBER` | Your Twilio virtual phone number | ✅ Yes |
| `AI_ENDPOINT_URL` | URL of Flask `/generate` endpoint | ✅ Yes |
| `AI_MODEL_URL` | Base URL of Flask server | ✅ Yes |
| `SMS_ENDPOINT_URL` | Base URL for SMS endpoints | Optional |
| `PORT` | Port for the Node.js server (default: 3000) | Optional |

---

## 🔒 Security — Files Protected from GitHub

The following sensitive files are **gitignored** and will NOT be pushed to GitHub:

| File | Contains |
|------|----------|
| `.env` (root) | Gemini API key, Mapbox key, owner phone number |
| `backend/.env` | Twilio credentials, MongoDB URI, Deepgram key |
| `backend/config/firebase-service-account.json` | Firebase Admin private key |
| `mobile_app/app/google-services.json` | Firebase client config |
| `venv/` | Python virtual environment |
| `backend/node_modules/` | Node.js dependencies |

---

## 🎯 Key Design Decisions

1. **Stateless Flask API** — All conversation state (`stage`, `collected_info`, `history`) is passed in each request and returned in the response. The Node.js backend maintains state per active call via WebSocket.
2. **Role-Based Routing** — Callers are automatically identified as `delivery` or `unknown` and routed to separate logic pipelines.
3. **SMS Integration Pattern** — When an OTP is needed, the Flask API returns `"requires_sms": true`, signaling the Node.js backend to trigger an FCM push to the mobile app. The mobile app reads SMS and sends them back to the backend. This keeps the AI backend decoupled from direct phone access.
4. **OTP Approval System** — The owner must explicitly approve OTP sharing via a notification on their phone, preventing unauthorized access. The call is paused and automatically resumed after approval. The backend uses data-only FCM payloads so the Android app can render custom rich notifications with action buttons.
5. **Fuzzy Company Matching** — Handles speech-to-text errors where company names may be misheard (e.g., "Amazone" → "Amazon").
6. **Self-Hosted SLP Pipeline** — Replaced commercial cloud APIs with a fully local Speech and Language Processing pipeline. Utilizes OpenAI Whisper (fine-tuned with LoRA) for STT and a local Neural Vocoder for TTS, ensuring data privacy and handling accented telephony speech.
7. **Firebase Auth End-to-End** — The mobile app authenticates via Google Sign-In (Firebase Auth). Every API request includes a Firebase ID token, verified by Firebase Admin SDK on the backend.
8. **ngrok Static Domain** — Uses a free ngrok static domain so the tunnel URL never changes between restarts. No need to update code or Twilio config after initial setup.
9. **Conversation Resume** — When an OTP approval is pending, the `conversationResumeService` holds the WebSocket connection state so the call can seamlessly continue once the owner responds.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](file:///c:/Users/hp/Desktop/PROJECTS/VoiceDrop/LICENSE) file for details.
