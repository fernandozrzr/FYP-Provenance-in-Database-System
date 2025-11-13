# Interactive Provenance Exploration for Data Preparation Debugging

This project provides a unified browser-based interface for interacting with two provenance systems, **GProM** and **ProvSQL**, without requiring users to memorise complex syntax or work through command-line interfaces. The system offers table-based outputs, provenance graph visualisation, tuple occurrence summaries, and interactive provenance circuit exploration.

---

## 📁 Project Structure

```
project/
│
├── app.py                 # Flask backend (query builder, execution, parsing)
├── prov_graph.py          # ProvSQL CSV → PNG provenance graph generator
├── templates/
│   └── index.html         # Front-end interface
│
├── static/                # Graphs and exported files generated at runtime
│   ├── output.png
│   ├── prov_graph.png
│   ├── prov_output.csv
│   └── ...
└── README.md
```

---

## 🛠 Requirements

### Python

- Python ≥ 3.8
- Flask
- Graphviz installed locally

Install system dependencies:

```bash
sudo apt install graphviz
```

Create virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask
```

---

## 🔧 Provenance Engines (Prerequisites)

### 1. Install GProM (Ubuntu / WSL)

```bash
git clone https://github.com/IITDBGroup/gprom.git
cd gprom
mkdir build && cd build
cmake ..
make -j4
sudo make install
```

Make sure GProM CLI exists:

```
/home/user/gprom/src/command_line/gprom
```

---

### 2. Install ProvSQL (Docker)

```bash
docker pull pierresenellart/provsql
docker run -it --name provsql-demo -p 5432:5432 pierresenellart/provsql
```

Inside the container:

```bash
psql -U test -d test -c "CREATE EXTENSION provsql;"
```

---

## ▶ Running the System

Start Flask:

```bash
source venv/bin/activate
python3 app.py
```

Open the browser:

```
http://localhost:5000
```

---

## 🚀 Features

### ✔ Supports Both Engines

| Engine      | Capabilities                                                                                     |
| ----------- | ------------------------------------------------------------------------------------------------ |
| **GProM**   | Provenance-of, Temporal provenance, REENACT, HAS/USE PROVENANCE, Graphviz lineage graphs         |
| **ProvSQL** | Semiring provenance, WHERE-provenance, Probability evaluation, UUID-based circuits, VIEW_CIRCUIT |

---

## 👤 Author

**Leong Ling Min Fernando**  
Final Year Project: _Interactive provenance exploration for data preparation debugging_

---

## 📜 License

This project is for academic purposes and not intended for production deployment.
