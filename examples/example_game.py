from spot.dialog.dialog_manager import DialogManager

if __name__ == '__main__':
    dialog_manager = DialogManager(1,2)

    dialog_manager.set_replier(lambda reply: print(reply))
    dialog_manager.submit()
    dialog_manager.utterance()