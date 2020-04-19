import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Set up database
engine = create_engine("postgres://rpjilxlcgaghie:c8d1c15ea82e25fc78284036a2a972a27b393b9d7dfacd2bef3496bfe5cc0d6b@ec2-54-147-209-121.compute-1.amazonaws.com:5432/dfuf1untuc7v6m")
db = scoped_session(sessionmaker(bind=engine))

def main():
    line_count = 0
    f = open("books.csv")
    reader = csv.reader(f)
    for isbn, title, author, year in reader :
        if line_count == 0:
            line_count += 1
            continue
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
        {"isbn" : isbn, "title" : title, "author" : author, "year" : year})
    db.commit()
if __name__ == "__main__" :
    main()
