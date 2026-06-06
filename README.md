# LoChat

LoChat is a secure client-server chat application built in Python. The project was developed with a focus on secure communication, user-friendly graphical interfaces, and a modular architecture that separates client and server functionality.

The application uses SSL/TLS to encrypt communications between clients and the server and stores application data using SQLite.

---

## Features

* Secure SSL/TLS encrypted communication
* Dedicated client and server applications
* Modern graphical user interface
* Multi-client support
* SQLite database integration
* Administrative management panel
* Modular and maintainable code structure
* Cross-platform Python implementation

---

## Project Structure

```text
SecureChat/
│
├── client_app/
│   ├── main.py
│   ├── network.py
│   ├── ui.py
│   ├── theme.py
│   └── utils.py
│
├── server_app/
│   ├── main.py
│   ├── server.py
│   ├── database.py
│   ├── admin_ui.py
│   └── ssl_context.py
│
├── requirements.txt
└── README.md
```

---

## Requirements

* Python 3.10 or newer
* OpenSSL
* pip

---

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/LoChat.git
cd LoChat
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## SSL Certificate Setup

For security reasons, SSL certificates are **not included** in this repository.

Before running the server, create a directory named:

```text
server_app/certificate
```

The structure should look like:

```text
server_app/
│
├── certificate/
│   ├── server.crt
│   └── server.key
│
├── server.py
├── ssl_context.py
└── ...
```

### Generate a Self-Signed Certificate

Open a terminal inside the `server_app/certificate` directory and run:

```bash
openssl req -x509 -newkey rsa:4096 -nodes \
-keyout server.key \
-out server.crt \
-days 365
```

You will be asked to provide certificate information. For development purposes, default values are acceptable.

After completion, two files should be generated:

```text
server.crt
server.key
```

These files are required for the server to establish encrypted connections.

---

## Running the Server

Navigate to the server application directory:

```bash
cd server_app
```

Start the server:

```bash
python main.py
```

---

## Running the Client

Navigate to the client application directory:

```bash
cd client_app
```

Start the client:

```bash
python main.py
```

---

## Security Notes

* SSL certificate files are intentionally excluded from version control.
* Private keys should never be shared publicly.
* For production deployments, use certificates issued by a trusted Certificate Authority instead of self-signed certificates.

---

## Technologies Used

* Python
* Socket Programming
* SSL/TLS
* SQLite
* CustomTkinter
* Threading

---

## Educational Purpose

This project was developed as a practical exploration of networking concepts, secure communication, client-server architecture, and GUI application development using Python.

The goal was to combine networking fundamentals with real-world software engineering practices in a complete end-to-end application.
