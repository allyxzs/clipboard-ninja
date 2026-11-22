import hashlib
import sqlite3
from datetime import datetime


class History:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA secure_delete=ON")
        self.db.execute("""CREATE TABLE IF NOT EXISTS clips
            (id INTEGER PRIMARY KEY AUTOINCREMENT, digest TEXT UNIQUE, kind TEXT,
             body TEXT, image BLOB, stamp TEXT, state TEXT)""")
        with self.db:
            self.db.execute("UPDATE clips SET state='OCR interrompido' WHERE state='Lendo imagem'")

    def add(self, kind, body, image=None):
        digest = hashlib.sha256(kind.encode() + (image if image else body.encode())).hexdigest()
        with self.db:
            old = self.db.execute("SELECT body,state FROM clips WHERE digest=?", (digest,)).fetchone()
            state = 'Texto' if kind == 'texto' else 'Lendo imagem'
            if old:
                body, state = old
                self.db.execute("DELETE FROM clips WHERE digest=?", (digest,))
            cur = self.db.execute("INSERT INTO clips(digest,kind,body,image,stamp,state) VALUES(?,?,?,?,?,?)",
                                  (digest, kind, body, image, datetime.now().isoformat(timespec='seconds'), state))
            self.db.execute("DELETE FROM clips WHERE id NOT IN (SELECT id FROM clips ORDER BY id DESC LIMIT 200)")
            self.db.execute("""DELETE FROM clips WHERE id IN
                (SELECT id FROM (SELECT id,SUM(COALESCE(length(image),length(CAST(body AS BLOB)))) OVER
                (ORDER BY id DESC) AS total FROM clips) WHERE total>67108864)""")
        return digest, not old

    def results(self, query):
        rows = self.db.execute("SELECT id,kind,body,stamp,state FROM clips ORDER BY id DESC")
        return [row for row in rows if query.casefold() in (row[2]+' '+row[1]).casefold()]

    def finish(self, digest, body, state):
        with self.db:
            self.db.execute("UPDATE clips SET body=?,state=? WHERE digest=?", (body,state,digest))

    def remove(self, item=None):
        with self.db:
            if item is None:
                self.db.execute("DELETE FROM clips")
            else:
                self.db.execute("DELETE FROM clips WHERE id=?", (item,))

