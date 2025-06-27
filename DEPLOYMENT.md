# 🚀 Deployment Guide – PBPQMS (Protected Buffer-Based Patient Queue Management System)

This guide helps you install and run the PBPQMS system, a doctor registration and user management app built using Flask and Oracle DB, on your local machine or server.

---

## 🛠️ 1. Prerequisites

Ensure the following are installed:

| Tool                  | Purpose                            |
|-----------------------|-------------------------------------|
| Python 3.8+           | Backend environment                 |
| pip                   | Python package manager              |
| Oracle Database       | Main backend database               |
| Oracle Instant Client | Oracle connectivity via pyodbc      |
| pyodbc                | Python-to-Oracle DB connector       |
| Git                   | Version control                     |

---

## 📁 2. Clone the Repository

```bash
git clone https://github.com/Janani2405/pbpqms-doctor-reg-system.git
cd pbpqms-doctor-reg-system
````

---

## 🧪 3. (Optional) Create a Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # macOS/Linux
```

---

## 📦 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 5. Create Environment File

Create a `.env` file in the root directory with:

```env
DB_USER=your_oracle_username
DB_PASSWORD=your_oracle_password
DBQ=localhost/XE
```

> Replace with your actual Oracle DB credentials and service name.

---

## 🗃️ 6. Oracle Table Creation

All required SQL table definitions are included in the `tables.txt` file.
👉 Open the file and run its contents inside Oracle SQL Developer or SQL\*Plus.

This will create the following tables:

* **Users** – stores usernames, passwords, and roles
* **Buffer** – staging table for uncommitted doctor data
* **Doctors** – final committed doctor records

> Ensure your Oracle database service (e.g., `localhost/XE`) is running before running the script.

---

## ▶️ 7. Run the Flask App

```bash
python app.py
```

You’ll see:

```
 * Running on http://127.0.0.1:5000/
```

Open this URL in your browser to use the app.

---

## 📷 8. Screenshots

> Check the `README.md` file for visual screenshots of key pages like:

* Login
* Doctor Form
* Buffer Table
* User List

---

## ✅ 9. Optional Next Steps

* Add a `Procfile` and deploy to Heroku
* Dockerize for containerized deployment
* Deploy to Render for free hosting
* Use `Gunicorn` for production servers

---

## 👩‍💻 Maintainer

**Janani A**
🔗 [GitHub: @Janani2405](https://github.com/Janani2405)

---

