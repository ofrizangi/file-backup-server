# File backup server

A simple backup server developed in python allowing you to back-up a specific directory in your computer.

# Featueres:
1. Backing up all the files and folders in a specific directory and its subfolders.
2. Whenever a change is made in the directory - deleting, modifying, creating, renaming or moving a file or a folder, it will automatically update in the server as well.
3. The same user can connect the server from different computers.
4. The program allows you to transfer the backed-up directory from one computer to another – whenever you connect an existing user from a new computer the server will automatically push this directory to the new computer.
5. Every change you did in the folder in one computer will automatically change in other computers that are connected to the same user.
6. Working both in linux and windows


# Tools:
1. sockets - for connecting between the server and all the clients, and transfering the necessary information. Working by TCP protocol.
2. watchdog library - for tracking the directory that is backed up.

