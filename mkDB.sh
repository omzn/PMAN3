#!/bin/sh
rm -f db/bibdat.db
sqlite3 db/bibdat.db <<EOF
CREATE TABLE bib(
id integer primary key autoincrement,
style text not null,
ptype integer not null,
author  text,
editor  text,
key     text,
title   text,
journal text,
booktitle text,
series  text,
volume  text,
number  text,
chapter text,
pages   text,
edition text,
school  text,
type    text,
institution    text,
organization   text,
publisher   text,
address   text,
month   integer,
year   integer,
howpublished   text,
note   text,
annote   text,
abstract   text,
title_e   text,
author_e   text,
editor_e   text,
journal_e   text,
booktitle_e   text,
publisher_e   text,
acceptance   text,
impactfactor   text,
url   text
);
CREATE TABLE ptypes(
pt_id    integer primary key autoincrement,
pt_type  integer not null,
pt_order integer not null,
pt_lang  text not null,
pt_desc  text not null
);
CREATE TABLE files(
id integer primary key autoincrement,
pid integer not null,
filename text not null,
mimetype text not null,
file blob not null,
access integer not null,
file_desc text
);
CREATE TABLE tags(
tag_id integer primary key autoincrement,
paper_id integer not null,
tag text not null
);
CREATE TABLE authors(
id integer primary key autoincrement,
paper_id integer not null,
author_order integer not null,
author_name text not null,
author_key text
);
EOF
rm -f db/sess.db
sqlite3 db/sess.db <<EOF
CREATE TABLE sessions (
id CHAR(32) NOT NULL PRIMARY KEY,
a_session TEXT NOT NULL);
EOF
chmod 666 db/*.db
chmod 777 db
