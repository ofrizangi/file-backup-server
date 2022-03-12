# File Backup Server

A simple backup server developed in python allowing you to back-up a specific directory in your computer.

## Featueres:
1. Backing up all the files and folders in a specific directory and its subfolders.
2. Whenever a change is made in the directory (delete/update/create/rename/move) the change will automatically be updated in the server as well.
3. The same user can connect to the server from different computers.
4. The program allows you to transfer the backed-up directory from one computer to another – whenever you connect an existing user from a new computer the server will automatically push this directory to the new computer.
5. Every change you did in the folder in one computer will automatically change in other computers that are connected to the same user.
6. Works both on Linux and Windows


## Tools:
1. Sockets - for connecting the server and the clients, and transfering the necessary information.
   Using TCP protocol.
3. Watchdog library - for tracking the directory that is backed up.

