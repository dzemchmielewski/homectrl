create database homectrl;
create user homectrl with encrypted password 'homectrl_dba';
grant all privileges on database homectrl to homectrl;
GRANT ALL ON SCHEMA public TO homectrl;
ALTER DATABASE homectrl OWNER TO homectrl;
