def check_transfer(transfer_id: str):
    return {'ID': transfer_id}


def confirm_transfer(intent_id: str):
    return {
        'input': {
            'id': intent_id
        }
    }


def get_moment(moment_id: str):
    return {'momentId': moment_id}


def get_profile(oauth_id: str):
    return {'id': oauth_id}


def get_user(username: str):
    return {'username': username}


def start_transfer(
        moment_id: str, flow_id: str, receiver_oauth_id: str,
        moment_name: str = '', moment_image: str = ''
):
    return {
        'momentID': moment_id,
        'momentFlowID': flow_id,
        'receiverDapperID': receiver_oauth_id,
        'momentTitle': moment_name,
        'momentImage': moment_image,
        'redirectURL': ''
    }
