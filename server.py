import socket
import os
import sys
import utils

BUFFER_SIZE = 8000


def create_id_and_folder_client(my_path):
    """
    Creating an ID and a folder to backup all the client files.
    Args:
        my_path (str): the path of the directory we want to create their the clients backup the directory
    Returns:
           str : the clients ID
    """
    client_id2 = utils.create_id()
    new_client_path = os.path.join(my_path, client_id2)
    # crete new folder to client
    if not os.path.exists(new_client_path):
        os.makedirs(new_client_path)
    # send to client id
    client_socket.send(bytes(client_id2, "utf-8"))
    return client_id2


def search_folder_and_push_to_client(id_file_name, directory_path, socket2):
    """
    Pushing all files and folders from the directory related to the client ID into the clients' folder.
    Args:
        id_file_name (str): the clients ID, which is the name of the folder we are looking for
        directory_path (str): the path of the directory we want to look there for the specific client folder
        socket2 (): the socket connected to the client
    """
    for root, dir, files in os.walk(directory_path):
        for folder in dir:
            # finding the client folder by his id
            if folder == id_file_name:
                directory_path = os.path.join(directory_path, id_file_name)
                utils.push_all_folders(directory_path, '', socket2)
                utils.send_message("done", socket2)
                utils.push_all_files(directory_path, '', socket2)
                utils.send_message("it is last", socket2)
                break


def delete_client_id_in_the_path(path2):
    """
    Returning the path without the client id number in it.
    Args:
        path2 (): the path we want to delete from it the client ID
    Returns:
        str : the new path
    """
    parts_of_path = path2.decode("utf-8").split(os.sep)
    new_path2 = parts_of_path[1]
    for i in range(2, len(parts_of_path) - 1):
        new_path2 = os.path.join(new_path2, parts_of_path[i])
    return new_path2


# updating the dict that contains all the changes from the client
def update_data_dict(computer_id, all_computer_id, place, data_to_send, computer_id_dict):
    """
    Adding a change to the dict that contains all the changes we have to send to a specific computer.
     We add this change to all the clients with the same client ID, but different computer ID.
    Args:
        computer_id (str): the computer ID of the computer that did the change and we don't want to send it for him
        again.
        all_computer_id(dict): a list that contains all the different computer IDs of the same client ID.
        place (str): the name of the change we want to send the client
        data_to_send (): the change itself
        computer_id_dict(dict): the dict containing all the computer IDs mapped to different changes we need to send
        to that computer.
    """
    for client_computer_id in all_computer_id:
        # update the dictionary of all the different computers except for this one
        if client_computer_id != computer_id:
            computer_id_dict[client_computer_id][place].append(data_to_send)


def send_changes_to_client(changes_dict, sock, client_id):
    """
    Sending all the changes that has been done in the directory by other clients with same ID, for a specific computer.
    Args:
        changes_dict (dict): the dict containing all the changes that has to be send.
        sock(): the socket connected to the client
        client_id (str): the ID of the client we are sending him the changes
    """
    for change in changes_dict:
        # sending the data to clients with the same computer ID
        if change == 'create_directory' and changes_dict[change] != []:
            for data_to_send in changes_dict[change]:
                utils.send_message(change, sock)
                for renames in changes_dict["modify_directory"]:
                    if data_to_send in renames:
                        data_to_send = renames[1]
                        changes_dict["modify_directory"].remove(renames)
                        break
                str_data = data_to_send.decode("utf-8").replace(client_id + os.sep, '')
                utils.send_message(str_data, sock)

        if change == 'create' and changes_dict[change] != []:
            for data_to_send in changes_dict[change]:
                # if os.path.isfile(new_path + data_to_send.decode("utf-8")):
                utils.send_message(change, sock)
                for renames in changes_dict["rename_file"]:
                    if bytes(data_to_send.decode("utf-8").replace(os.sep, '', 1), "utf-8") in renames:
                        data_to_send = bytes(os.sep + renames[1].decode("utf-8"), "utf-8")
                        changes_dict["rename_file"].remove(renames)
                        break
                folder_name, file_name = utils.names(client_id, data_to_send.decode("utf-8"))
                utils.send_a_single_file(new_path + data_to_send.decode("utf-8"),
                                         file_name, '', folder_name, sock)

        if change == 'delete' and changes_dict[change] != []:
            for data_to_send in changes_dict[change]:
                utils.send_message(change, sock)
                str_data = data_to_send.decode("utf-8").replace(client_id + os.sep, '')
                utils.send_message(str_data, sock)

        if (change == 'rename_file' or change == 'modify_directory') and changes_dict[change] != []:
            for data_to_send in changes_dict[change]:
                utils.send_message(change, sock)
                str_src_data = data_to_send[0].decode("utf-8").replace(client_id + os.sep, '')
                utils.send_message(str_src_data, sock)
                str_dest_data = data_to_send[1].decode("utf-8").replace(client_id + os.sep, '')
                utils.send_message(str_dest_data, sock)

        if change == 'modify' and changes_dict[change] != []:
            for data_to_send in changes_dict[change]:
                utils.send_message(change, sock)
                str_data = data_to_send[0].decode("utf-8").replace(os.sep + client_id + os.sep, '')
                utils.send_message(str_data, sock)
                folder_name, file_name = utils.names(client_id, data_to_send[1].decode("utf-8"))
                utils.send_a_single_file(new_path + os.sep + data_to_send[1].decode("utf-8"),
                                         file_name, '', folder_name, sock)
                sock.recv(BUFFER_SIZE)


def update_changes_from_client(client_socket, new_path, computer_id_dict, id_dict, computer_id):
    """
    Adding a change to the dict that contains all the changes we have to send to a specific computer.
     We add this change to all the clients with the same client ID, but different computer ID.
    Args:
        client_socket (): the socket connected to the client
        new_path (str): the path of the server director
        computer_id_dict(dict): the dict containing all the computer IDs mapped to different changes we need to send
        to that computer.
        id_dict(dict): a dict mapping a client ID to all its computer IDs'.
        computer_id (str): the computer ID of the computer that did the change and we don't want to send it for him
        again.
    """
    data = client_socket.recv(BUFFER_SIZE)
    # updating changes in the server folder
    while data != b'no more changes':
        client_socket.send(b'got it')

        if data == b'create':
            my_client_id = utils.rec_message(client_socket).decode("utf-8")
            data2 = client_socket.recv(utils.BUFFER_SIZE)
            utils.get_a_single_file(new_path, client_socket, data2)
            update_data_dict(computer_id, id_dict[my_client_id], "create", data2, computer_id_dict)

        elif data == b'delete':
            my_client_id = utils.rec_message(client_socket).decode("utf-8")
            data2 = utils.rec_message(client_socket)
            utils.delete_a_single_file_or_folder(new_path, data2.decode("utf-8"))
            update_data_dict(computer_id, id_dict[my_client_id], "delete", data2, computer_id_dict)

        elif data == b'modify':
            my_client_id = utils.rec_message(client_socket).decode("utf-8")
            data_to_delete = utils.rec_message(client_socket)
            utils.delete_a_single_file_or_folder(new_path, data_to_delete.decode("utf-8"))
            data_to_create = client_socket.recv(utils.BUFFER_SIZE)
            utils.get_a_single_file(new_path, client_socket, data_to_create)
            update_data_dict(computer_id, id_dict[my_client_id], "modify", [data_to_delete, data_to_create],
                             computer_id_dict)

        elif data == b'create_directory':
            my_client_id = utils.rec_message(client_socket).decode("utf-8")
            data2 = utils.rec_message(client_socket)
            path = os.path.join(new_path, data2.decode("utf-8"))
            utils.make_folder(path)
            update_data_dict(computer_id, id_dict[my_client_id], "create_directory", data2, computer_id_dict)

        elif data == b'rename_file' or data == b'modify_directory':
            my_client_id = utils.rec_message(client_socket).decode("utf-8")
            data1 = utils.rec_message(client_socket)
            src_path = os.path.join(new_path, data1.decode("utf-8"))
            data2 = utils.rec_message(client_socket)
            dest_path = os.path.join(new_path, data2.decode("utf-8"))
            os.rename(src_path, dest_path)
            update_data_dict(computer_id, id_dict[my_client_id], data.decode("utf-8"), [data1, data2],
                             computer_id_dict)

        data = client_socket.recv(BUFFER_SIZE)


if __name__ == '__main__':
    new_path = os.path.join(os.getcwd(), "Server")
    # create new folder to the server
    utils.make_folder(new_path)
    # in the ID dict - a key of a client ID will be mapped to a list of all the computer IDs'
    id_dict = {}
    """"
    in the computer ID dict - a key of a computer ID will be mapped for a dict that contains all the changes 
    we have to send to this computer.
    """
    computer_id_dict = {}
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', int(sys.argv[1])))
    server.listen(5)

    while True:

        # accepting the next client
        client_socket, client_address = server.accept()
        computer_id = utils.rec_message(client_socket).decode("utf-8")
        first_data = client_socket.recv(BUFFER_SIZE)

        # if it is the first meeting with this client
        if first_data == b'hello':
            # new client without id, server create id and open folder to save client's files"
            id_client = create_id_and_folder_client(new_path)
            print(id_client)
            # sever pull all folder from client
            utils.pull_all_folders(new_path, client_socket)
            utils.pull_all_files(new_path + os.sep, client_socket)
            id_dict.update({id_client: [computer_id]})
            save_data_dict = {"create_directory": [], "create": [], "rename_file": [],
                              "modify_directory": [], "modify": [], "delete": []}
            computer_id_dict.update({computer_id: save_data_dict})

        # if there is already a client with this ID
        elif first_data == b'already know you':
            client_socket.send(b'got it')
            client_id = client_socket.recv(BUFFER_SIZE).decode("utf-8")
            search_folder_and_push_to_client(client_id, new_path, client_socket)
            # adding the client computer ID to the list of all the computers connected to the same user
            id_dict[client_id].append(computer_id)
            save_data_dict = {"create_directory": [], "create": [], "rename_file": [],
                              "modify_directory": [], "modify": [], "delete": []}
            computer_id_dict.update({computer_id: save_data_dict})

        # updating and getting updates from the client
        else:
            client_id = first_data.decode("utf-8")
            changes_dict = computer_id_dict[computer_id]

            send_changes_to_client(changes_dict, client_socket, client_id)

            client_socket.send(b'do nothing')
            # erase all the changes we did
            for key in computer_id_dict[computer_id]:
                computer_id_dict[computer_id][key] = []

            update_changes_from_client(client_socket, new_path, computer_id_dict, id_dict, computer_id)

        client_socket.close()
