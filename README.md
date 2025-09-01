# Natural Language to SQL Chatbot

A production-ready chatbot that translates plain English questions into safe, executable SQL queries for a PostgreSQL database using AWS Bedrock (Claude) and FastAPI. Enables non-technical users to access business data and insights through a simple web interface.

## Features
- **Natural Language to SQL:** Converts user questions into SQL queries using LLM prompt engineering and schema guidance.
- **SQL Safety:** Ensures only safe SELECT queries are executed, with regex-based validation and FROM clause enforcement.
- **Error Handling:** Automatically repairs SQL errors by re-prompting the LLM with error feedback.
- **API Reliability:** Implements exponential backoff and retry logic for Bedrock API calls.
- **User Experience:** Returns both the generated SQL and the query results (and optionally, a plain English answer).
- **Deployment:** Dockerized for easy deployment; uses environment variables for configuration.

## Tech Stack
- Python 3.11, FastAPI, Uvicorn
- PostgreSQL, psycopg2-binary
- AWS Bedrock (Claude), boto3
- Docker

## Setup Instructions
1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/nl-to-sql-chatbot.git
   cd nl-to-sql-chatbot
   ```
2. **Install dependencies:**
   ```sh
   python -m venv venv
   .\venv\Scripts\activate  # On Windows
   pip install -r requirements.txt
   ```
3. **Configure environment variables:**
   - Copy `.env.example` to `.env` and fill in your AWS and database credentials.
4. **Run the app:**
   ```sh
   uvicorn app:app --reload
   ```
5. **Access the frontend:**
   - Open `http://localhost:8000` in your browser.

## Docker Deployment
1. **Build and run the container:**
   ```sh
   docker build -t nl-to-sql-chatbot .
   docker run --env-file .env -p 8000:8000 nl-to-sql-chatbot
   ```

## Project Structure
- `app.py` – FastAPI backend and main logic
- `bedrock_client.py` – LLM prompt engineering and Bedrock API calls
- `db.py` – Database connection and SQL safety
- `index.html` – Simple web frontend
- `Dockerfile` – Containerization
- `requirements.txt` – Python dependencies

## License
MIT License

---
Feel free to open issues or contribute!
