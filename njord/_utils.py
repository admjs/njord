import os


def is_process_running(process_id):
    try:
        # os.kill(process_id, 0)
        os.system("sudo kill -0 " + str(process_id))
        return True
    except Exception:
        return False
