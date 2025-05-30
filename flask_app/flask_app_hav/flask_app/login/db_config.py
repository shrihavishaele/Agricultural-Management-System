import psycopg2

def connect_db():
    return psycopg2.connect(
        dbname="project",
        user="postgres",
        password="1234",
        host="localhost",
        port="5432"
    )

