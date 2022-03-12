import sys
import utils
import socket
import os
import time
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

BUFFER_SIZE = 8000


def connect_with_server(socket):
    """
    A function for connecting a new client to the backup server.
    Args:
        socket (): The socket used for connecting to the server
    Returns:
        str: the ID the server gave to the client
    """
    socket.send(b'hello')
    client_id = socket.recv(BUFFER_SIZE).decode("utf-8")
    return client_id


def no_id(client_id, directory_path, socket):
    """
    When a new client got connected to the server we push to the server, the folder the client wants to backup.
    Args:
        client_id (str): The ID of the client
        directory_path (str): The directory the client wants to backup
        socket (): the socket connected to the server
    """
    utils.push_all_folders(directory_path, client_id, socket)
    # The client notifies the server that has finished sending the folder names to it
    utils.send_message("done", socket)
    utils.push_all_files(directory_path, client_id, socket)
    utils.send_message("it is last", socket)


def with_id(client_id, directory_path, socket):
    """
    When a client with an existing ID connect to the server, we want to pull  from the server the files that are
    relevant to him into a given directory.
    Args:
        client_id (str): The ID of the client
        directory_path (str): The directory the client wants to backup
        socket (): the socket connected to the server
    """
    socket.send(bytes(client_id, "utf-8"))
    utils.pull_all_folders(directory_path, socket)
    utils.pull_all_files(directory_path, socket)


def send_new_folder_path(src_path, dest_path, directory, socket, client_id):
    """
    Sending the server the old and new name of the folder we renamed.
    Args:
        src_path (str): the path of the file before renaming it
        dest_path (str): the path of the file after renaming it
        directory (str): the directory the watchdog is tracking
        socket (): the socket connected to the server
        client_id (str): the ID of the client
    """
    str_src_path = src_path.replace(directory, "")
    str_dest_path = dest_path.replace(directory, "")
    path_dest_arr = str_dest_path.split(os.sep)
    path_src_arr = str_src_path.split(os.sep)
    folder_new_name = path_dest_arr[0]
    folder_old_name = path_src_arr[0]
    if folder_new_name == folder_old_name:
        for i in range(1, len(path_dest_arr)):
            if path_dest_arr[i] == path_src_arr[i]:
                folder_old_name = os.path.join(folder_old_name, path_src_arr[i])
                folder_new_name = os.path.join(folder_new_name, path_dest_arr[i])
            if path_dest_arr[i] != path_src_arr[i]:
                folder_old_name = os.path.join(folder_old_name, path_src_arr[i])
                folder_new_name = os.path.join(folder_new_name, path_dest_arr[i])
                break
    utils.send_message(os.path.join(client_id, folder_old_name), socket)
    utils.send_message(os.path.join(client_id, folder_new_name), socket)


def check_if_need_to_update(sock, directory, changes_from_server_dict, client_id):
    """
    When other clients with the same ID make changes in their directory the server needs to update us.
    Here we get all the updates from the server.
    Args:
        sock (): the socket connected to the server
        changes_from_server_dict (dict): A dict containing all the changes we made here. We save all the changes
        we made so we will know not to send them again to the server.
        directory (str): the directory the watchdog is tracking
        client_id (str): the ID of the client
    Returns:
          int: 1 if we made a change in the directory, 0 otherwise.
    """
    sock.send(bytes(client_id, "utf-8"))
    data = sock.recv(BUFFER_SIZE)
    flag_entered_to_dict = 0
    # while we get new changes from the server
    while data != b'do nothing':
        sock.send(b'got it')
        flag_entered_to_dict = 1
        if data == b'create_directory':
            data2 = utils.rec_message(sock).decode("utf-8")
            path = os.path.join(directory, data2)
            utils.make_folder(path)
            changes_from_server_dict["create_directory"].append(path)

        elif data == b'create':
            data2 = sock.recv(utils.BUFFER_SIZE)
            data3 = data2.decode("utf-8")
            if data3 != '':
                if data3[0] == os.sep:
                    data3 = data3.replace(os.sep, '', 1)
            changes_from_server_dict["create"].append(directory + os.sep + data3)
            utils.get_a_single_file(directory + os.sep, sock, data2)

        elif data == b'rename_file' or data == b'modify_directory':
            data1 = utils.rec_message(sock)
            src_path = os.path.join(directory, data1.decode("utf-8"))
            data2 = utils.rec_message(sock)
            dest_path = os.path.join(directory, data2.decode("utf-8"))
            changes_from_server_dict[data.decode("utf-8")].append([src_path, dest_path])
            os.rename(os.path.normpath(src_path), os.path.normpath(dest_path))

        elif data == b'modify':
            data_to_delete = utils.rec_message(sock).decode("utf-8")
            data_to_create = utils.rec_message(sock).decode("utf-8")
            if data_to_create[0] == os.sep:
                data_to_create = data_to_create.replace(os.sep, '', 1)
            changes_from_server_dict["delete"].append(client_id + data_to_delete)
            changes_from_server_dict["create"].append(directory + os.sep + data_to_create)
            changes_from_server_dict["modify"].append(directory + os.sep + data_to_create)
            if data_to_delete[0] == os.sep:
                data_to_delete = data_to_delete.replace(os.sep, '', 1)
            utils.delete_a_single_file_or_folder(directory, data_to_delete)
            utils.get_a_single_file(directory + os.sep, sock, bytes(data_to_create, "utf-8"))

        elif data == b'delete':
            data2 = utils.rec_message(sock)
            for root, dirs, files in os.walk(directory + os.sep + data2.decode("utf-8"), topdown=False):
                for file in files:
                    changes_from_server_dict["delete"].append(client_id + root.replace(directory, '') + os.sep + file)
                for folder in dirs:
                    changes_from_server_dict["delete"].append(client_id + root.replace(directory, '') + os.sep + folder)
            changes_from_server_dict["delete"].append(client_id + os.sep + data2.decode("utf-8"))
            utils.delete_a_single_file_or_folder(directory, data2.decode("utf-8"))

        data = sock.recv(BUFFER_SIZE)

    return flag_entered_to_dict


def sending_items_in_dict(my_dict, changes_from_server_dict, client_id, new_sock, directory):
    """
    Sending the server all the last changes we did in our directory, except for the changes we got from him.
    Args:
        new_sock (): the socket connected to the server
        changes_from_server_dict (dict): A dict containing all the changes we got from the server, if a certain change
        is in this dict we won't send it back to the server.
        directory (str): the directory the watchdog is tracking.
        client_id (str): the ID of the client
        my_dict (dict): the dict that contains all the changes we made in the directory.
    """
    for item in my_dict["create_directory"]:
        if item not in changes_from_server_dict["create_directory"]:
            utils.send_message("create_directory", new_sock)
            utils.send_message(client_id, new_sock)
            str = item.replace(directory, "")
            utils.send_message(client_id + str, socket)

    for item in my_dict["create"]:
        if item not in changes_from_server_dict["create"]:
            utils.send_message("create", new_sock)
            utils.send_message(client_id, new_sock)
            folder_name, file_name = utils.names(directory, item)
            for files in my_dict["rename_file"]:
                if item in files:
                    item = files[1]
                    break
            utils.send_a_single_file(item, file_name, os.sep + client_id, folder_name, new_sock)

    for item in my_dict["rename_file"]:
        if item not in changes_from_server_dict["rename_file"]:
            utils.send_message("rename_file", new_sock)
            utils.send_message(client_id, new_sock)
            folder_name1, file_name1 = utils.names(directory, item[0])
            utils.send_message(client_id + folder_name1 + os.sep + file_name1, new_sock)
            folder_name2, file_name2 = utils.names(directory, item[1])
            utils.send_message(client_id + folder_name2 + os.sep + file_name2, new_sock)

    for item in my_dict["modify_directory"]:
        do_change = 1
        for change in changes_from_server_dict["modify_directory"]:
            if change[0] in item[0]:
                do_change = 0
        if do_change == 1:
            utils.send_message("modify_directory", new_sock)
            utils.send_message(client_id, new_sock)
            send_new_folder_path(item[0], item[1], directory, new_sock, client_id)

    for item in my_dict["modify"]:
        if item not in changes_from_server_dict["modify"]:
            if os.path.isfile(item):
                utils.send_message("modify", new_sock)
                utils.send_message(client_id, new_sock)
                delete_path = item.replace(directory, "")
                utils.send_message(os.path.join(client_id, delete_path), new_sock)
                folder_name, file_name = utils.names(directory, item)
                utils.send_a_single_file(item, file_name, os.sep + client_id, folder_name, new_sock)

    for item in my_dict["delete"]:
        if item not in changes_from_server_dict["delete"]:
            utils.send_message("delete", new_sock)
            utils.send_message(client_id, new_sock)
            utils.send_message(item, new_sock)


class Watcher:
    """
    A class for creating and running the observer (of the watchdog library) that will track the changes in the
    directory we gave him.
    """

    def __init__(self, directory, times, ip, port, client_id, computer_id, handler):
        self.observer = Observer()
        self.directory = directory
        self.time_for_connect = times
        self.ip = ip
        self.port = port
        self.client_id = client_id
        self.computer_id = computer_id
        self.handler = handler
        self.changes_from_server_dict = {"delete": [], "create": [], "create_directory": [], "rename_file": [],
                                         "modify_directory": [], "modify": []}

    def run(self):
        """
        Running the observer on the clients directory with an infinity loop.
        At each iteration we connect to the server that sends us the changes we need to make in the directory,
        and send the server the new changes we made.
        """
        self.observer.schedule(self.handler, self.directory, recursive=True)
        self.observer.start()

        try:
            while True:
                self.handler.close_socket()
                # waiting for x time
                time.sleep(self.time_for_connect)
                sock_new = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.handler.set_socket(sock_new)
                # connecting the server
                sock_new.connect((self.ip, self.port))
                utils.send_message(self.computer_id, sock_new)
                # getting updates from the server
                flag_erase_dict = check_if_need_to_update(sock_new, self.directory, self.changes_from_server_dict,
                                                          self.client_id)
                # the dict that contains all the changes we made
                dict = self.handler.get_dict()
                # remove duplicates from list
                for key in dict:
                    if key != "rename_file" and key != "modify_directory":
                        dict[key] = list(dict.fromkeys(dict[key]))
                # sending all the updates we made
                sending_items_in_dict(dict, self.changes_from_server_dict, client_id, sock_new, self.directory)

                self.handler.set_list_empty()

                if flag_erase_dict != 1:
                    for key in self.changes_from_server_dict:
                        self.changes_from_server_dict[key] = []
                sock_new.send(b"no more changes")
        except:
            self.observer.stop()
            self.observer.join()


class MyHandler(FileSystemEventHandler):
    """
    A handler class from dealing with the different events that occurs in the directory.
    Whenever an event occurs the observer notifies this handler to execute the actions.
    """

    def __init__(self, ip, port, sock, client_id, path_folder_client):
        FileSystemEventHandler.__init__(self)
        self.dict_change = {"delete": [], "create": [], "create_directory": [], "rename_file": [],
                            "modify_directory": [], "modify": []}
        self.socket = sock
        self.ip = ip
        self.port = port
        self.client_id = client_id
        self.path_folder_client = path_folder_client
        self.flag_create_file = 0
        self.flag_create_folder = 0
        self.flag_rename_folder = 0
        self.flag_rename_file = 0

    def set_list_empty(self):
        for key in self.dict_change:
            self.dict_change[key] = []

    def get_dict(self):
        return self.dict_change

    def close_socket(self):
        self.socket.close()

    def set_socket(self, sock):
        self.socket = sock

    # when a file or folder is created this method get called
    def on_created(self, event):
        if event.is_directory:
            self.dict_change["create_directory"].append(event.src_path)
        else:
            self.flag_create_file = 1
            self.dict_change["create"].append(event.src_path)

    # when a file or folder is deleted this method get called
    def on_deleted(self, event):
        if os.path.isdir(event.src_path):
            new_string = event.src_path.replace(self.path_folder_client, "")
            self.dict_change["delete"].append(self.client_id + new_string)
        else:
            new_string = event.src_path.replace(self.path_folder_client, "")
            self.dict_change["delete"].append(self.client_id + new_string)

    # when a file is modified this method get called
    def on_modified(self, event):
        self.flag_rename_folder = 0
        if not event.is_directory:
            if self.flag_create_file == 0 and self.flag_rename_file == 0:
                self.dict_change["modify"].append(event.src_path)
            self.flag_rename_file = 0
            self.flag_create_file = 0

    # when a file or folder is moved this method get called
    def on_moved(self, event):
        if event.is_directory:
            if self.flag_rename_folder == 0:
                self.flag_rename_folder = 1
                self.dict_change["modify_directory"].append([event.src_path, event.dest_path])
        else:
            # if the name of the file was changed, and the file didn't only move
            dest_path_arr = event.dest_path.split(os.sep)
            src_path_arr = event.src_path.split(os.sep)
            len_src_path_arr = len(src_path_arr)
            if src_path_arr[len_src_path_arr - 1] != dest_path_arr[len_src_path_arr - 1]:
                self.dict_change["rename_file"].append([event.src_path, event.dest_path])
                self.flag_rename_file = 1


if __name__ == "__main__":
    ip = sys.argv[1]
    port = int(sys.argv[2])
    directory_path = sys.argv[3]
    time_for_connect = float(sys.argv[4])
    client_id = ''
    computer_id = utils.create_id()

    socket_first = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_first.connect((ip, port))
    utils.send_message(computer_id, socket_first)

    # if there are only four arguments (no ID) - that means it is a new client
    if len(sys.argv) == 5:
        client_id = connect_with_server(socket_first)
        no_id(client_id, directory_path, socket_first)
    # otherwise it is an existing clients
    else:
        client_id = sys.argv[5]
        utils.make_folder(directory_path)
        utils.send_message("already know you", socket_first)
        with_id(client_id, directory_path, socket_first)

    w = Watcher(directory_path, time_for_connect, ip, port, client_id, computer_id,
                MyHandler(ip, port, socket_first, client_id, directory_path))
    w.run()
