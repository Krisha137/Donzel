# 🍨 Donzel - Artisanal Ice Cream & Desserts Parlour

A full-stack Django web application for an artisanal ice cream parlour, featuring interactive dessert customization, order management, digital customer wallet, and staff administration dashboard.

---

## ✨ Features

- **Storefront & Menu Showcase**: Browse handcrafted artisanal gelato, ice creams, sorbets, and sundaes with rich descriptions, pricing, and dietary categories.
- **Interactive Dessert Customizer**: Build personalized custom ice cream creations.
- **Cart & Order Checkout**:
  - Dine-In parlour table service
  - Takeaway express pickup
- **Payment Choices**:
  - **Donzel Digital Wallet**: Instant 1-click order checkout using digital wallet balance with top-up options.
  - **Online Payment / UPI**: Future scope option (GPay, PhonePe, Paytm, Cards).
- **Automated Email Receipts**: Real-time order confirmations sent directly via Gmail SMTP.
- **Manager / Staff Admin Dashboard**: Real-time order tracking, status workflow updates (Accepted, Preparing, Ready, Served), and analytics.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Clone the Repository
`ash
git clone https://github.com/Krisha137/Dozel.git
cd Dozel
`

### 3. Create & Activate Virtual Environment
`ash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
`

### 4. Install Dependencies
`ash
pip install -r requirements.txt
`

### 5. Setup Environment Variables
Copy .env.example to .env and configure your credentials:
`ash
cp .env.example .env
`

### 6. Run Migrations & Start Server
`ash
python manage.py migrate
python manage.py runserver
`

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

---

## 🔑 Default Staff Credentials
- **Manager Dashboard**: /admin-dashboard/
- **Username**: dmin
- **Password**: dmin@123
