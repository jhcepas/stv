-- Run this file to (re)create all the tables needed for the backend.

drop table if exists users;
create table users (
    id integer primary key autoincrement,
    username text unique,
    name text not null,
    password text not null);

drop table if exists trees;
create table trees (
    id integer primary key autoincrement,
    owner integer not null,
    name text unique not null,
    description text,
    newick text);

drop table if exists user_owned_trees;
create table user_owned_trees (
    id_user integer,
    id_tree integer unique);

drop table if exists user_reader_trees;
create table user_reader_trees (
    id_user integer,
    id_tree integer);
