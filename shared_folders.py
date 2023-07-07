shared_folders = []

def add_shared_folder(share_link):
    shared_folders.append(share_link)

def is_folder_shared(share_link):
    return share_link in shared_folders
