import os
import random
import string

BUFFER_SIZE = 8000


def send_message(massage, sock):
    """
    A function for sending a given message with a given socket, and getting a verification the message was received.
    Args:
        massage (str): the message we want to send
        sock (): the socket we want to send the message with
    """
    sock.send(bytes(massage, "utf-8"))
    data = b''
    while data == b'':
        data = sock.recv(BUFFER_SIZE)


def rec_message(sock):
    """
    A function for receiving a message a sending a verification the message was received.
    Args:
        sock (): the socket we want to send the verification with
    """
    message = b''
    while message == b'':
        message = sock.recv(BUFFER_SIZE)
    sock.send(b"i got it")
    return message


def send_a_single_file(file_path, file_name, client_id, folder_name, socket):
    """
    A function for sending a single file and all its contents
    Args:
        file_path (str) : the path of the file
        file_name ( str): the name of the file
        client_id (str) : the ID of the client
        folder_name (str): all the folders in the path of the file
        socket (): the socket that is connected to the server
    """
    f = open(os.path.normpath(file_path), "rb")
    data_to_send = os.path.join(client_id + folder_name, file_name)
    send_message(data_to_send, socket)
    data = f.read(BUFFER_SIZE)
    if data == b'':
        send_message("empty", socket)
    else:
        while data != b'':
            socket.send(data)
            data = f.read(BUFFER_SIZE)
        socket.recv(BUFFER_SIZE)
    f.close()


def push_all_files(directory_path, client_id, socket):
    """
    Pushing all the files from a given directory path to the server.
    Args:
        directory_path (str) : the path of the directory we want to push from
        client_id (str) : the ID of the client
        socket (): the socket that is connected to the server
    """
    for root, dirs, files in os.walk(directory_path, topdown=False):
        for file in files:
            name_folder = (os.path.join(root, file).split(directory_path, 1)[1]).split(file, 1)[0]
            send_a_single_file(os.path.join(root, file), file, client_id, name_folder, socket)


def push_all_folders(directory_path, client_id, socket):
    """
    Pushing all the folders from a given directory path.
    Args:
        directory_path (str) : the path of the directory we want to push from
        client_id (str) : the ID of the client
        socket (): the socket that is connected to the server
    """
    if client_id != '':
        client_id = os.path.join(client_id, "")
    start_path = os.sep + client_id
    for root, dirs, files in os.walk(directory_path, topdown=False):
        for name in dirs:
            path = os.path.join(root, name).split(directory_path + os.sep, 1)[1]
            send_message(start_path + path, socket)


# pulling all folders to the path we gave him
def pull_all_folders(path, client_socket):
    """
    Pulling all the folders to a given directory path.
    Args:
        path (str) : the path of the directory we want to put there the folders
        client_socket (): the socket that is connected to the server
    """
    data = rec_message(client_socket)
    # As long As the server or client has not received a message that
    while data != b'done':
        # data is the name of folder
        new_client_path = path + data.decode("utf-8")
        if not os.path.exists(new_client_path):
            os.makedirs(new_client_path)
        data = rec_message(client_socket)


def get_a_single_file(path, client_socket, file_path_data):
    """
    A function for getting a single file and putting it in a given path.
    Args:
        path (str) : the path we want to put the file in
        file_path_data ( bytes): the file name we need to create
        client_socket (): the socket that is connected to the server
    """
    file_path = file_path_data.decode("utf-8")
    # send a notification that the files path has been send
    client_socket.send(b'got it')
    # create file
    file_new = path + file_path
    file = open(file_new, "wb")
    # The contents of the file
    data3 = client_socket.recv(BUFFER_SIZE)
    if data3 == b'empty':
        client_socket.send(b'got it')
    else:
        while len(data3) == BUFFER_SIZE:
            file.write(data3)
            data3 = client_socket.recv(BUFFER_SIZE)
        file.write(data3)
        client_socket.send(b'2-got it')
    file.close()


def pull_all_files(path, client_socket):
    """
    Pulling all the files to a given directory path.
    Args:
        path (str) : the path of the directory we want to put there the files.
        client_socket (): the socket that is connected to the server
    """
    # data = address of new folder
    data2 = client_socket.recv(BUFFER_SIZE)
    while data2 != b'it is last':
        get_a_single_file(path, client_socket, data2)
        data2 = client_socket.recv(BUFFER_SIZE)
    client_socket.send(b'ok')


def names(path_folder_client, file_path):
    """
    Separating a file path into its name and its inner folders - folders that are in the directory we are backing up.
    Args:
        path_folder_client (str) : the path of the client directory that is watched
        file_path (str): the path of the file
    """
    # we want only the inner folders and the file name in the path
    array = file_path.replace(path_folder_client + os.sep, '').split(os.sep)
    len_op_path = len(array)
    file_name = array[len_op_path - 1]
    folder_name = ''
    index = 0
    # building a path of only the inner folders (without the file name ot the beginning)
    while index < len_op_path - 1:
        folder_name = os.path.join(folder_name, array[index])
        index += 1
    if folder_name != '':
        folder_name = os.sep + folder_name
    return folder_name, file_name


def delete_a_single_file_or_folder(start_path, end_path):
    new_path = os.path.join(start_path, end_path)
    if os.path.isfile(new_path):
        os.remove(new_path)
    if os.path.isdir(new_path):
        for root, dirs, files in os.walk(new_path, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for folder in dirs:
                os.rmdir(os.path.join(root, folder))
        os.rmdir(new_path)


def create_id():
    """
    Creating a randomly client ID.
    Returns:
         str: the ID of the client
    """
    client_id = ""
    for i in range(0, 128):
        client_id = client_id + random.SystemRandom().choice(
            string.ascii_uppercase + string.digits + string.ascii_lowercase)
    return client_id


def make_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)
