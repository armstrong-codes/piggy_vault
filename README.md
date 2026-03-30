# Piggy Vault System

A group savings management system built with Flask and MySQL.

## Requirements

- Python 3.x
- MySQL Server
- pip

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/piggy-vault.git
cd piggy-vault
```

### 2. Install dependencies
```bash
pip install flask flask_sqlalchemy mysql-connector-python werkzeug
```

### 3. Set up the database
- Open MySQL and create a database:
```sql
CREATE DATABASE piggy_vault_db;
```

### 4. Configure the database connection
- Open `app.py` and update this line with your MySQL credentials:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:YOUR_PASSWORD@localhost/piggy_vault_db'
```

### 5. Run the app
```bash
python app.py
```

### 6. Open in browser
```
http://127.0.0.1:5000
```

### 7. Default admin login
- Go to sign up page to create your group first
- Then log in with the username and password you created

## Features
- Admin and member login
- Member management (add, edit, delete)
- Attendance tracking
- Loan management with payment tracking
- System activity log
- Dashboard with totals
