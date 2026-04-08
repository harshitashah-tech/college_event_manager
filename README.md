# 🎓 EventSphere — College Event Management System

A full-stack, modular academic project built with **Python + Streamlit + MongoDB Atlas**.

---

## 📁 Project Structure

```
college_event_manager/
│
├── app.py                        ← Main entry point
├── config.py                     ← Central configuration & constants
├── requirements.txt
├── .env.example                  ← Copy to .env with your credentials
│
├── auth/
│   ├── login.py                  ← Login flow (MongoDB + bcrypt)
│   ├── register.py               ← Registration flow
│   └── roles.py                  ← Role constants & permission helpers
│
├── database/
│   └── mongo_client.py           ← Singleton MongoDB Atlas client
│
├── modules/
│   ├── events.py                 ← Event CRUD + registrations
│   ├── clubs.py                  ← Club CRUD + membership
│   ├── notifications.py          ← Notification system
│   ├── certificates.py           ← Certificate issuance + PDF generation
│   ├── payments.py               ← Simulated payment sandbox
│   └── recommendations.py        ← MongoDB-based recommendation engine
│
├── dashboards/
│   ├── student_dashboard.py
│   ├── coordinator_dashboard.py
│   └── admin_dashboard.py
│
└── utils/
    ├── helpers.py                ← Date formatting, badges, currency
    ├── validators.py             ← Input validation helpers
    └── styling.py                ← CSS injection + UI component wrappers
```

---

## 🚀 Deployment (Streamlit Community Cloud)

1. **Push to GitHub**: Upload this project to a public repository on GitHub.
2. **Connect to Streamlit**: Go to [share.streamlit.io](https://share.streamlit.io) and select your repository.
3. **Configure Secrets**:
   - In Streamlit Cloud settings, go to **Secrets**.
   - Paste the contents of your `.env` file into the box.
   - Specifically, ensure `MONGO_URI` and `MONGO_DB_NAME` are set.

---

## 🏗️ Architecture Notes

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Streamlit | Role-based reactive UI |
| Backend | Python 3.10+ | Business logic, data processing |
| Database | MongoDB Atlas | Cloud-hosted NoSQL storage |
| Auth | Custom (bcrypt) | Secure password hashing & session management |
| PDF | fpdf2 | On-the-fly certificate generation |
| Charts | Plotly | Admin analytics visualisations |

---

## ⚙️ MongoDB Atlas Setup

1. Create a cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Create a Database User with read/write access.
3. Whitelist `0.0.0.0/0` in Network Access (or use Streamlit Cloud IPs).
4. Get your `mongodb+srv://` connection string and add it to `.env`.

---

## 👤 User Roles

- **Student**: Browse events, register, pay (simulated), join clubs, and download certificates.
- **Coordinator**: Create events/clubs, manage participants, and issue certificates.
- **Administrator**: Approve events/clubs, manage users, and view analytics.

---

*Built as an academic project demonstrating clean modular Python architecture with Streamlit and MongoDB Atlas.*
