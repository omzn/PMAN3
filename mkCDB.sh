#!/bin/sh
rm -f db/cache.db
sqlite3 db/cache.db <<EOF
CREATE TABLE cache(
id integer primary key autoincrement,
url text not null,
page  text
);
EOF
chmod 666 db/cache.db
