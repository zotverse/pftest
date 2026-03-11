import psycopg2; import os; from dotenv import load_dotenv; load_dotenv(); print("Connecting..."); conn = psycopg2.connect(os.environ["DATABASE_URL"]); print("Success!"); conn.close()
