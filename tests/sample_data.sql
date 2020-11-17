-- Run this file to add sample values into the database.

insert into users values
    (1, 'admin', 'System Administrator',
     'pbkdf2:sha256:50000$713rFBmU$1e10a0e9b5fca0b4550b39dffd01931d8cdc64760d5995856e9c775e94e983dd'),
    (2, 'user2', 'Maria',
     'pbkdf2:sha256:50000$w4xHhhi8$75b2502e4680383c5fc89423e446b847021b52b086648897b8a6dcba60e771cb'),
    (3, 'user3', 'Debbie',
     'pbkdf2:sha256:50000$g2cIiryf$b0da4704216e5128544a831ba293adcc7aae3d730df9464cba5943fdf2b33c92');

-- abc -> pbkdf2:sha256:50000$713rFBmU$1e10a0e9b...
-- 123 -> pbkdf2:sha256:50000$w4xHhhi8$75b2502e4...
-- xyz -> pbkdf2:sha256:50000$g2cIiryf$b0da47042...


insert into trees values
    (1, 1, 'My First Tree', 'A simple test of a tree',
    '((B:2,(C:3,D:4)E:5)A:1)F;'),
    (2, 1, 'Tree of Life', 'Every species, more or less',
    '(ainur,wizards,balrogs:2[&&NHX:temp=hot:fun=no],dwarves,elves,humans,ents,hobbits,orcs,trolls,barrow-wights)?;'),
    (3, 2, 'Directories', 'From the filesystem',
    '(boot/,dev/,etc/,(user1/,user2/)home/,(bin/,lib/)usr/,var/,tmp/)/;');

insert into user_owned_trees values  -- id_user, id_tree
    (1, 1), (1, 2),
    (2, 3);

insert into user_reader_trees values  -- id_user, id_tree
    (1, 3), (1, 2),
    (3, 1), (3, 2);
